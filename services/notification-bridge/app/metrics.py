"""Puerto de metricas + adapter Prometheus.

Se define un puerto minimo (`MetricsPort`) y una implementacion nula
(`NoOpMetrics`, usada por defecto en tests) siguiendo el mismo espiritu que
`MetricsPort`/`NoOpMetrics` de `OutboxRelay` en Itinerary Service: la logica
de decision (`app/processor.py`) nunca importa `prometheus_client`
directamente, solo el puerto.
"""
from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

MESSAGES_PROCESSED = Counter(
    "notification_bridge_messages_processed_total",
    "Mensajes de itinerary.events procesados (aceptados o dead-letter) por notification-bridge",
)
MESSAGES_FAILED = Counter(
    "notification_bridge_messages_failed_total",
    "Intentos de invocacion a la Lambda SendNotificationFunction que fallaron",
)
MESSAGES_DEAD_LETTERED = Counter(
    "notification_bridge_dead_lettered_total",
    "Mensajes enrutados a la dead-letter exchange (schema invalido o reintentos agotados)",
)


class MetricsPort:
    def inc_processed(self) -> None:  # pragma: no cover - interfaz
        raise NotImplementedError

    def inc_failed(self) -> None:  # pragma: no cover - interfaz
        raise NotImplementedError

    def inc_dead_lettered(self) -> None:  # pragma: no cover - interfaz
        raise NotImplementedError


class NoOpMetrics(MetricsPort):
    def inc_processed(self) -> None:  # pragma: no cover - trivial
        pass

    def inc_failed(self) -> None:  # pragma: no cover - trivial
        pass

    def inc_dead_lettered(self) -> None:  # pragma: no cover - trivial
        pass


class PrometheusMetrics(MetricsPort):
    def inc_processed(self) -> None:
        MESSAGES_PROCESSED.inc()

    def inc_failed(self) -> None:
        MESSAGES_FAILED.inc()

    def inc_dead_lettered(self) -> None:
        MESSAGES_DEAD_LETTERED.inc()


def render_latest() -> tuple[bytes, str]:
    """Devuelve (body, content_type) para el endpoint `/metrics`."""
    return generate_latest(), CONTENT_TYPE_LATEST
