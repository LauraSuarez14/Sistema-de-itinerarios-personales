# Contract Testing (Pact) — Itinerary Service ↔ Airport Service

Verifica el contrato REST `GET /api/v1/airports/{id}` que Itinerary Service
usa como **fallback HTTP** de la validación de aeropuertos (el canal
principal es gRPC; ver ADR y `services/itinerary-service/app/infrastructure/`).

> **No ejecutado en el entorno donde se generó este proyecto**: `pact-python`
> descarga binarios standalone (Ruby) la primera vez y la verificación del
> proveedor requiere Airport Service corriendo de verdad (Docker), ninguno
> disponible aquí. El código queda completo y listo para ejecutar.

## Cómo correrlo

```bash
pip install -r tests/contract/requirements.txt

# 1. Lado consumidor: genera tests/contract/pacts/itinerary-service-airport-service.json
pytest tests/contract/test_consumer_itinerary.py -v

# 2. Lado proveedor: requiere Airport Service real escuchando en :8001
docker compose up -d airport-service redis
pytest tests/contract/test_provider_airport.py -v
```

Si el contrato cambia (p. ej. se agrega un campo obligatorio a `AirportOut`
en `services/airport-service/app/api/schemas.py`), el test del proveedor
debe fallar hasta que Itinerary Service actualice su lado del contrato —
ese es justamente el valor del contract testing frente a testear cada
servicio de forma aislada.
