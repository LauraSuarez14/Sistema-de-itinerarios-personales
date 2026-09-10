"""Adapter concreto de `EventPublisherPort` usando `pika` (API bloqueante).

Implementa publisher confirms (`confirm_delivery`) y `mandatory=True` para
detectar si el mensaje no pudo enrutarse a ninguna cola, y reconexion con
backoff exponencial si la conexion con RabbitMQ se cae entre publicaciones
(el `OutboxRelay` sigue funcionando: simplemente los ciclos fallaran y
reintentaran en el siguiente polling, sin perder eventos porque
`published_at` solo se marca si `publish()` devuelve True)."""
from __future__ import annotations

import json
import logging
import time

import pika
from pika.exceptions import AMQPError, UnroutableError

from ...domain.ports import EventPublisherPort

logger = logging.getLogger(__name__)


class RabbitMQPublisher(EventPublisherPort):
    def __init__(
        self,
        amqp_url: str,
        exchange: str,
        exchange_type: str = "topic",
        max_reconnect_attempts: int = 5,
        initial_backoff_seconds: float = 0.5,
    ) -> None:
        self._amqp_url = amqp_url
        self._exchange = exchange
        self._exchange_type = exchange_type
        self._max_reconnect_attempts = max_reconnect_attempts
        self._initial_backoff_seconds = initial_backoff_seconds
        self._connection: pika.BlockingConnection | None = None
        self._channel = None

    def _ensure_channel(self):
        if self._connection is not None and self._connection.is_open and self._channel is not None and self._channel.is_open:
            return self._channel

        backoff = self._initial_backoff_seconds
        last_error: Exception | None = None
        for attempt in range(1, self._max_reconnect_attempts + 1):
            try:
                self._connection = pika.BlockingConnection(pika.URLParameters(self._amqp_url))
                self._channel = self._connection.channel()
                self._channel.exchange_declare(
                    exchange=self._exchange, exchange_type=self._exchange_type, durable=True
                )
                self._channel.confirm_delivery()
                return self._channel
            except AMQPError as exc:  # noqa: PERF203 - retry loop, clarity over micro-perf
                last_error = exc
                logger.warning(
                    "RabbitMQ connection attempt %s/%s failed: %s",
                    attempt,
                    self._max_reconnect_attempts,
                    exc,
                )
                time.sleep(backoff)
                backoff *= 2
        raise ConnectionError(f"Could not connect to RabbitMQ after {self._max_reconnect_attempts} attempts") from last_error

    def publish(self, routing_key: str, payload: dict) -> bool:
        try:
            channel = self._ensure_channel()
            return channel.basic_publish(
                exchange=self._exchange,
                routing_key=routing_key,
                body=json.dumps(payload).encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,  # persistente
                ),
                mandatory=True,
            )
        except UnroutableError:
            # El mensaje no pudo enrutarse a ninguna cola (nadie escuchando
            # el exchange todavia); la conexion sigue sana, solo el mensaje
            # se considera no confirmado y se reintentara en el proximo ciclo.
            logger.warning("Message unroutable on exchange (routing_key=%s)", routing_key)
            return False
        except Exception:  # noqa: BLE001 - cualquier otro fallo se traduce a "no confirmado"
            logger.exception("Failed to publish message to RabbitMQ (routing_key=%s)", routing_key)
            self._channel = None
            self._connection = None
            return False

    def close(self) -> None:
        if self._connection is not None and self._connection.is_open:
            self._connection.close()
