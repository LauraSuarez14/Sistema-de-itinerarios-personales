# Airport Service

Microservicio del Airport Context. Ver `README.md` en la raíz del proyecto
para la arquitectura completa.

## Ejecutar tests localmente (sin Docker)

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt -r requirements-dev.txt
pip install -e ../../libs/common
PYTHONPATH=. pytest tests/ -v
```

Los tests de `tests/test_use_cases.py` no requieren ninguna dependencia
externa real (usan `tests/fakes.py`, un `AirportRepositoryPort` en memoria).
`tests/test_api_colombia_adapter.py` valida específicamente la traducción de
la respuesta cruda de API Colombia al modelo de dominio, incluyendo el
intercambio de `latitude`/`longitude` que tiene la API externa (confirmado
contra `https://api-colombia.com/api/v1/Airport/2`).

## Variables de entorno

Ver `.env.example` en la raíz del proyecto (`API_COLOMBIA_BASE_URL`,
`REDIS_URL`, `AIRPORT_CACHE_TTL_SECONDS`, `AIRPORT_HTTP_PORT`,
`AIRPORT_GRPC_PORT`, `OAUTH2_CLIENT_ID`/`OAUTH2_CLIENT_SECRET`,
`TOXIPROXY_ENABLED`/`TOXIPROXY_PROXY_URL`, `JWT_SECRET_KEY`,
`OTEL_EXPORTER_OTLP_ENDPOINT`, `VAULT_ADDR`/`VAULT_TOKEN`).

## Superficies expuestas

- REST + Swagger: `http://localhost:8001/docs` (`/api/v1/airports*`, `/oauth/token`, `/health`, `/metrics`).
- gRPC: `airport.v1.AirportService` en el puerto `50051` (contrato en `proto/airport.proto`), protegido con JWT (Bearer) vía interceptor — usado por Itinerary Service.
