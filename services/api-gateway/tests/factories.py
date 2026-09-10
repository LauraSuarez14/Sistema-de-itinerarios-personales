"""Helpers de tests: construye objetos Settings de prueba sin depender de
variables de entorno ni de docker-compose, y sin tocar la app global del
módulo (cada test crea su propia instancia con `app.main.create_app`)."""
from __future__ import annotations

from app.config import Settings

DEFAULTS = dict(
    http_port=8000,
    airport_service_url="http://airport-service:8001",
    itinerary_service_url="http://itinerary-service:8002",
    rate_limit_per_minute=1000,
    demo_user="viajero",
    demo_password="viajero123",
)


def make_settings(**overrides) -> Settings:
    values = dict(DEFAULTS)
    values.update(overrides)
    return Settings(**values)
