# Itinerary Service

CRUD de itinerarios de viaje (arquitectura hexagonal), con validacion de
aeropuertos contra Airport Service (gRPC con fallback REST) y publicacion de
`ItineraryCreatedEvent v1` en RabbitMQ via Transactional Outbox (ver
`docs/adr/0002-double-write-problem.md`).

## Correr los tests localmente (sin Docker)

Los tests de `tests/` solo cubren `app/domain/` y `app/application/`, que no
importan SQLAlchemy, grpc ni pika, por lo que solo necesitan `pytest` (y
`pydantic`, usado por algunos esquemas relacionados):

```bash
cd services/itinerary-service
python -m venv .venv
. .venv/Scripts/activate   # en Windows; en Linux/Mac: source .venv/bin/activate
pip install pytest pydantic
pytest tests/ -v
```

No hace falta Postgres, RabbitMQ ni el Airport Service real: los puertos del
dominio (`ItineraryRepositoryPort`, `AirportValidationPort`,
`EventPublisherPort`, `OutboxRepositoryPort`) se sustituyen por fakes en
memoria (`tests/fakes.py`).

Para correr el servicio completo (API + Postgres + RabbitMQ + migraciones)
usa `docker compose up --build` desde la raiz del repo.

## Variables de entorno principales

| Variable | Uso |
|---|---|
| `ITINERARY_DB_HOST/PORT/NAME/USER/PASSWORD` | Conexion a Postgres (SQLAlchemy sincrono + psycopg2-binary) |
| `AIRPORT_SERVICE_GRPC_URL` | Host:puerto del Airport Service (gRPC, primer intento) |
| `AIRPORT_SERVICE_HTTP_URL` | Base URL del Airport Service (REST, fallback + endpoint OAuth2) |
| `OAUTH2_CLIENT_ID` / `OAUTH2_CLIENT_SECRET` | Credenciales S2S para el token Client Credentials |
| `RABBITMQ_URL` / `RABBITMQ_EXCHANGE` | Broker donde el `OutboxRelay` publica el evento de integracion |
| `OUTBOX_RELAY_INTERVAL_SECONDS` | Intervalo de polling del `OutboxRelay` |
| `ITINERARY_HTTP_PORT` | Puerto donde escucha uvicorn (default 8002) |
| `JWT_SECRET_KEY` | Secreto para verificar los JWT emitidos por el API Gateway |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint OTLP/gRPC de Jaeger |

Ver `.env.example` en la raiz del repo para la lista completa y los valores
por defecto usados por `docker-compose.yml`.

## Endpoints

- `GET /health` -- sin auth, `SELECT 1` contra la DB.
- `GET /metrics` -- metricas Prometheus (incluye `outbox_pending_events` y
  `outbox_events_published_total`).
- `POST|GET|PUT|DELETE /api/v1/itineraries*` -- requieren `Authorization: Bearer <jwt>`.
- Swagger UI: `/docs` (titulo "Itinerary Service API", version "1.0.0").

Todas las respuestas de error usan `application/problem+json` (RFC 7807).
