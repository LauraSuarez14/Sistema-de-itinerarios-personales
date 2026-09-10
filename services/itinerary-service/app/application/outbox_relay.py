"""OutboxRelay: orquestador del patron Transactional Outbox (ADR 0002).

Vive en `application/` (y no en `infrastructure/`) a proposito: su logica de
negocio (poll -> publicar -> marcar publicado si y solo si el broker
confirmo) depende UNICAMENTE de los puertos `OutboxRepositoryPort`,
`EventPublisherPort` y `MetricsPort`, nunca de `pika`, `psycopg2` ni
`prometheus_client` directamente. Eso permite testear el ciclo completo del
relay con fakes en memoria, sin RabbitMQ ni Postgres reales. Los adapters
concretos (pika, prometheus_client) viven en `infrastructure/messaging/` e
`infrastructure/metrics.py` y se inyectan aqui via constructor.

`threading.Thread` es libreria estandar, por eso su uso aqui no rompe la
regla de "sin dependencias externas" de la arquitectura hexagonal.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from ..domain.events import ROUTING_KEY_ITINERARY_CREATED
from ..domain.ports import EventPublisherPort, MetricsPort, OutboxRepositoryPort

logger = logging.getLogger(__name__)


class NoOpMetrics(MetricsPort):
    """Implementacion nula usada por defecto y en tests, para no forzar una
    dependencia de metricas real cuando no se necesita observar nada."""

    def set_outbox_pending(self, count: int) -> None:  # pragma: no cover - trivial
        pass

    def inc_outbox_published(self, amount: int = 1) -> None:  # pragma: no cover - trivial
        pass


class OutboxRelay:
    def __init__(
        self,
        outbox_repository: OutboxRepositoryPort,
        event_publisher: EventPublisherPort,
        routing_key: str = ROUTING_KEY_ITINERARY_CREATED,
        interval_seconds: float = 2.0,
        batch_size: int = 50,
        metrics: MetricsPort | None = None,
    ) -> None:
        self._repository = outbox_repository
        self._publisher = event_publisher
        self._routing_key = routing_key
        self._interval_seconds = interval_seconds
        self._batch_size = batch_size
        self._metrics = metrics or NoOpMetrics()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def run_once(self) -> int:
        """Ejecuta un ciclo de polling y devuelve cuantos eventos se
        publicaron con exito. Metodo publico deliberadamente, para poder
        testear el ciclo de forma sincrona sin arrancar el hilo."""
        pending = self._repository.fetch_pending(limit=self._batch_size)
        self._metrics.set_outbox_pending(len(pending))

        published_count = 0
        for event in pending:
            try:
                confirmed = self._publisher.publish(self._routing_key, event.payload)
            except Exception:  # noqa: BLE001 - un fallo de publicacion nunca debe tumbar el relay
                logger.exception("Failed to publish outbox event %s", event.id)
                confirmed = False

            if confirmed:
                self._repository.mark_published(event.id, datetime.now(timezone.utc))
                self._metrics.inc_outbox_published()
                published_count += 1
            else:
                logger.warning(
                    "Outbox event %s was not confirmed by the broker; will retry next cycle",
                    event.id,
                )
        return published_count

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="outbox-relay", daemon=True
        )
        self._thread.start()
        logger.info("OutboxRelay started (interval=%ss)", self._interval_seconds)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        logger.info("OutboxRelay stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:  # noqa: BLE001 - un ciclo fallido no debe matar el hilo
                logger.exception("OutboxRelay polling cycle failed")
            self._stop_event.wait(self._interval_seconds)
