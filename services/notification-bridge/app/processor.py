"""Logica pura de decision del bridge: validar -> invocar Lambda (con
reintentos) -> decidir ack o dead-letter. Vive separada de `bridge.py`
(que solo conoce pika) para poder testear la decision completa con un
`LambdaInvoker` fake, sin RabbitMQ real -- mismo espiritu que `OutboxRelay`
en Itinerary Service, que separa la logica de negocio de los adapters
concretos (pika, prometheus_client) inyectandolos via constructor.
"""
from __future__ import annotations

import json
import logging
import time
from enum import Enum
from typing import Any, Callable, Protocol

from .metrics import MetricsPort, NoOpMetrics
from .schema import SchemaValidationError, validate_itinerary_created_event

logger = logging.getLogger(__name__)


class Decision(str, Enum):
    """Resultado de procesar un mensaje: que debe hacer el bridge con el
    delivery tag de AMQP."""

    ACK = "ack"
    # Tanto "schema invalido" como "reintentos de Lambda agotados" terminan
    # en la misma accion de broker: nack sin requeue, para que RabbitMQ lo
    # enrute a la dead-letter exchange (`x-dead-letter-exchange`).
    DEAD_LETTER = "dead_letter"


class LambdaInvokerPort(Protocol):
    def invoke(self, payload: dict) -> dict: ...  # pragma: no cover - protocolo


class MessageProcessor:
    def __init__(
        self,
        lambda_invoker: LambdaInvokerPort,
        max_attempts: int = 3,
        initial_backoff_seconds: float = 0.5,
        metrics: MetricsPort | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._lambda_invoker = lambda_invoker
        self._max_attempts = max_attempts
        self._initial_backoff_seconds = initial_backoff_seconds
        self._metrics = metrics or NoOpMetrics()
        self._sleep_fn = sleep_fn

    def process(self, body: bytes) -> Decision:
        payload = self._parse_and_validate(body)
        if payload is None:
            self._metrics.inc_dead_lettered()
            return Decision.DEAD_LETTER

        event_id = payload.get("event_id")
        backoff = self._initial_backoff_seconds
        last_error: Exception | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                result = self._lambda_invoker.invoke(payload)
                logger.info(
                    "Lambda invocation succeeded (event_id=%s, attempt=%s/%s): %s",
                    event_id,
                    attempt,
                    self._max_attempts,
                    result,
                )
                self._metrics.inc_processed()
                return Decision.ACK
            except Exception as exc:  # noqa: BLE001 - cualquier fallo de invocacion se reintenta igual
                last_error = exc
                self._metrics.inc_failed()
                logger.warning(
                    "Lambda invocation failed (event_id=%s, attempt=%s/%s): %s",
                    event_id,
                    attempt,
                    self._max_attempts,
                    exc,
                )
                if attempt < self._max_attempts:
                    self._sleep_fn(backoff)
                    backoff *= 2

        logger.error(
            "Exhausted %s attempts invoking Lambda (event_id=%s), dead-lettering: %s",
            self._max_attempts,
            event_id,
            last_error,
        )
        self._metrics.inc_dead_lettered()
        return Decision.DEAD_LETTER

    def _parse_and_validate(self, body: bytes) -> dict[str, Any] | None:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("Malformed message body, dead-lettering without retry: %s", exc)
            return None

        try:
            validate_itinerary_created_event(payload)
        except SchemaValidationError as exc:
            logger.error(
                "Message does not match ItineraryCreatedEvent v1 schema, "
                "dead-lettering without retry: %s",
                exc,
            )
            return None

        return payload
