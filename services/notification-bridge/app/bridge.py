"""RabbitMQBridge: adapter `pika` (API bloqueante) que declara la topologia
de colas/exchanges y consume mensajes, delegando la decision de ack/nack a
`MessageProcessor` (logica pura, ver `processor.py`).

Reconexion con backoff exponencial ante caidas de la conexion, siguiendo el
mismo patron que `RabbitMQPublisher` de Itinerary Service
(`services/itinerary-service/app/infrastructure/messaging/rabbitmq_publisher.py`)
para mantener consistencia de estilo entre los dos lados del mismo flujo
asincrono (uno publica, el otro consume).

NOTA DE ARQUITECTURA (ver README.md seccion 5 y ADR asociados): este proceso
NO es serverless. Es la pieza minima de infraestructura siempre encendida
que hace falta porque RabbitMQ no es un origen de eventos nativo de AWS
Lambda (a diferencia de SQS/Kinesis/DynamoDB Streams). Su unico trabajo es
traducir "hay un mensaje en la cola" en "invocar la funcion Lambda
correspondiente" -- toda la logica de negocio de la notificacion vive en la
propia Lambda (`SendNotificationFunction`), nunca aqui.
"""
from __future__ import annotations

import logging
import time

import pika
from pika.exceptions import AMQPError

from .processor import Decision, MessageProcessor

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "itinerary.events"
EXCHANGE_TYPE = "topic"
ROUTING_KEY = "itinerary.created.v1"

DEAD_LETTER_EXCHANGE_NAME = "itinerary.notifications.dlx"
DEAD_LETTER_QUEUE_NAME = "itinerary.notifications.dead"


class RabbitMQBridge:
    def __init__(
        self,
        amqp_url: str,
        processor: MessageProcessor,
        queue_name: str = "itinerary.notifications",
        prefetch_count: int = 1,
        initial_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 30.0,
    ) -> None:
        self._amqp_url = amqp_url
        self._processor = processor
        self._queue_name = queue_name
        self._prefetch_count = prefetch_count
        self._initial_backoff_seconds = initial_backoff_seconds
        self._max_backoff_seconds = max_backoff_seconds
        self._stopped = False

    def declare_topology(self, channel) -> None:
        """Idempotente: `exchange_declare`/`queue_declare` son declaraciones
        activas pero seguras de repetir (mismos argumentos => no-op si ya
        existen), por lo que el bridge puede reiniciarse sin coordinacion
        externa."""
        # Dead-letter primero: la cola principal la referencia por nombre.
        channel.exchange_declare(
            exchange=DEAD_LETTER_EXCHANGE_NAME, exchange_type="fanout", durable=True
        )
        channel.queue_declare(queue=DEAD_LETTER_QUEUE_NAME, durable=True)
        channel.queue_bind(queue=DEAD_LETTER_QUEUE_NAME, exchange=DEAD_LETTER_EXCHANGE_NAME)

        channel.exchange_declare(
            exchange=EXCHANGE_NAME, exchange_type=EXCHANGE_TYPE, durable=True
        )
        channel.queue_declare(
            queue=self._queue_name,
            durable=True,
            arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE_NAME},
        )
        channel.queue_bind(
            queue=self._queue_name, exchange=EXCHANGE_NAME, routing_key=ROUTING_KEY
        )

    def _on_message(self, channel, method, properties, body) -> None:
        correlation_id = None
        if properties is not None and properties.headers:
            correlation_id = properties.headers.get("x-correlation-id")

        try:
            decision = self._processor.process(body)
        except Exception:  # noqa: BLE001 - un fallo inesperado nunca debe tumbar el consumer
            logger.exception(
                "Unexpected error processing message (correlation_id=%s); dead-lettering",
                correlation_id,
            )
            decision = Decision.DEAD_LETTER

        if decision is Decision.ACK:
            channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def stop(self) -> None:
        self._stopped = True

    def run_forever(self) -> None:
        """Bucle principal: conecta, consume, y si la conexion se cae
        reintenta con backoff exponencial (nunca se rinde -- este proceso
        esta pensado para correr siempre encendido dentro del contenedor)."""
        backoff = self._initial_backoff_seconds
        while not self._stopped:
            try:
                connection = pika.BlockingConnection(pika.URLParameters(self._amqp_url))
                try:
                    channel = connection.channel()
                    self.declare_topology(channel)
                    channel.basic_qos(prefetch_count=self._prefetch_count)
                    channel.basic_consume(
                        queue=self._queue_name, on_message_callback=self._on_message
                    )
                    logger.info(
                        "notification-bridge connected to RabbitMQ, consuming queue=%s",
                        self._queue_name,
                    )
                    backoff = self._initial_backoff_seconds  # reset tras conexion exitosa
                    channel.start_consuming()
                finally:
                    if connection.is_open:
                        connection.close()
            except KeyboardInterrupt:
                logger.info("notification-bridge shutting down (KeyboardInterrupt)")
                self._stopped = True
            except AMQPError as exc:
                logger.warning(
                    "RabbitMQ connection lost or failed: %s. Reconnecting in %ss",
                    exc,
                    backoff,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, self._max_backoff_seconds)
