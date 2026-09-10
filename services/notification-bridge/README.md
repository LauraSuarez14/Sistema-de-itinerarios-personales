# notification-bridge

Puente entre RabbitMQ y las funciones Lambda de LocalStack. **No es
serverless** -- es un proceso Python simple, siempre encendido, que existe
porque RabbitMQ no es un origen de eventos nativo de AWS Lambda (a
diferencia de SQS/Kinesis/DynamoDB Streams, que si tienen "event source
mapping" nativo). Es la pieza minima de infraestructura necesaria para que
el broker "active" la funcion `SendNotificationFunction` (ver README.md
raiz, seccion 5, y `docs/adr/0003-eventos-dominio-vs-integracion.md`).

## Que hace

1. Declara la topologia AMQP (idempotente):
   - Exchange `itinerary.events` (topic, durable) -- ya declarado tambien
     por el `OutboxRelay` de Itinerary Service; declararlo aqui de nuevo es
     seguro porque `exchange_declare` con los mismos argumentos es un no-op.
   - Cola `itinerary.notifications` (durable, `NOTIFICATION_QUEUE`), bindeada
     con routing key `itinerary.created.v1`, con
     `x-dead-letter-exchange=itinerary.notifications.dlx`.
   - Exchange `itinerary.notifications.dlx` (fanout, durable) y cola
     `itinerary.notifications.dead` (durable) -- para poder detectar e
     inspeccionar dead-letters desde RabbitMQ management/Prometheus
     (criterio de "Alerting" del proyecto).
2. Por cada mensaje: valida el JSON contra el contrato exacto de
   `ItineraryCreatedEvent v1` (`app/schema.py`). Si no matchea, va directo a
   dead-letter (no tiene sentido reintentar basura).
3. Si matchea, invoca `SendNotificationFunction` via `boto3` (`lambda:Invoke`,
   `RequestResponse`, para poder loguear el resultado real). Reintenta hasta
   `NOTIFICATION_BRIDGE_MAX_ATTEMPTS` veces (default 3) con backoff
   exponencial. Si se agotan los reintentos, `basic_nack(requeue=False)` ->
   RabbitMQ enruta a la dead-letter exchange.
4. Expone `/health` y `/metrics` (Prometheus) en `NOTIFICATION_BRIDGE_HTTP_PORT`
   (default 8090): `notification_bridge_messages_processed_total`,
   `notification_bridge_messages_failed_total`,
   `notification_bridge_dead_lettered_total`.

## Correr los tests localmente (sin Docker, sin RabbitMQ/LocalStack reales)

`app/processor.py` y `app/bridge.py` reciben sus colaboradores (cliente
Lambda, canal AMQP) por parametro/duck typing, por lo que los tests usan
fakes en memoria (`tests/fakes.py`, `tests/test_bridge.py`):

```bash
cd services/notification-bridge
python -m venv .venv
. .venv/Scripts/activate   # en Windows; en Linux/Mac: source .venv/bin/activate
pip install pytest pika jsonschema prometheus-client
python -m pytest tests/ -v
```

`boto3` no hace falta para los tests: `app/lambda_invoker.py` (el unico
modulo que lo importa) no se ejercita directamente, solo a traves del fake
`FakeLambdaInvoker` (que implementa el mismo metodo `invoke(payload)`).

## Variables de entorno

Ver `.env.example` en la raiz para la lista completa. Las relevantes para
este servicio: `RABBITMQ_URL`, `NOTIFICATION_QUEUE`,
`SEND_NOTIFICATION_FUNCTION_NAME`, `AWS_ENDPOINT_URL`,
`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_DEFAULT_REGION`,
`NOTIFICATION_BRIDGE_HTTP_PORT`, `NOTIFICATION_BRIDGE_MAX_ATTEMPTS`.
