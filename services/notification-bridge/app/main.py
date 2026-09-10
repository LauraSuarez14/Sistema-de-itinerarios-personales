"""Punto de entrada del proceso `notification-bridge`.

NOTA DE ARQUITECTURA (ver README.md raiz, seccion 5, y
`docs/adr/0003-eventos-dominio-vs-integracion.md`): este proceso NO es
serverless -- es un worker Python simple, siempre encendido dentro de su
propio contenedor. Existe porque RabbitMQ no es un origen de eventos nativo
de AWS Lambda (no hay un "event source mapping" como el que si existe para
SQS/Kinesis/DynamoDB Streams); por eso hace falta esta pieza minima de
infraestructura que traduzca "llego un mensaje a la cola" en "invocar
`lambda:Invoke`". No contiene logica de negocio de notificaciones -- eso
vive exclusivamente en la Lambda `SendNotificationFunction`.
"""
from __future__ import annotations

import logging
import os

from common.logging import configure_json_logging

from .bridge import RabbitMQBridge
from .health import start_health_server
from .lambda_invoker import LambdaInvoker
from .metrics import PrometheusMetrics
from .processor import MessageProcessor

logger = logging.getLogger(__name__)


def main() -> None:
    configure_json_logging("notification-bridge", level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO"), logging.INFO))

    amqp_url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    queue_name = os.environ.get("NOTIFICATION_QUEUE", "itinerary.notifications")
    function_name = os.environ.get("SEND_NOTIFICATION_FUNCTION_NAME", "SendNotificationFunction")
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL", "http://localstack:4566")
    region_name = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "test")
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")
    health_port = int(os.environ.get("NOTIFICATION_BRIDGE_HTTP_PORT", "8090"))
    max_attempts = int(os.environ.get("NOTIFICATION_BRIDGE_MAX_ATTEMPTS", "3"))

    metrics = PrometheusMetrics()
    start_health_server(health_port)

    invoker = LambdaInvoker(
        function_name=function_name,
        endpoint_url=endpoint_url,
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    processor = MessageProcessor(invoker, max_attempts=max_attempts, metrics=metrics)
    bridge = RabbitMQBridge(amqp_url=amqp_url, processor=processor, queue_name=queue_name)

    logger.info(
        "notification-bridge starting (queue=%s, function=%s, endpoint=%s)",
        queue_name,
        function_name,
        endpoint_url,
    )
    bridge.run_forever()


if __name__ == "__main__":
    main()
