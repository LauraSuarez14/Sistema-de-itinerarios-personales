"""Configuración del API Gateway, cargada de variables de entorno. Mismo
estilo que los demás servicios (dataclass congelado + os.getenv). El único
secreto propio del gateway es JWT_SECRET_KEY, que además comparte con el
resto del sistema vía `common.security` (que lo lee directamente de
`os.environ`) — por eso, en vez de guardarlo en `Settings`, `load_settings`
lo resuelve desde Vault (con el mismo fallback a variables de entorno que
usan los demás servicios, ver `common.vault_client.load_secrets`) y lo
reinyecta en `os.environ` para que `common.security` lo use sin cambios."""
from __future__ import annotations

import os
from dataclasses import dataclass

from common.vault_client import load_secrets


@dataclass(frozen=True)
class Settings:
    http_port: int
    airport_service_url: str
    itinerary_service_url: str
    rate_limit_per_minute: int
    demo_user: str
    demo_password: str


def load_settings() -> Settings:
    secrets = load_secrets(mount_path="api-gateway", env_fallback_keys=["JWT_SECRET_KEY"])
    os.environ["JWT_SECRET_KEY"] = secrets["JWT_SECRET_KEY"]

    return Settings(
        http_port=int(os.getenv("GATEWAY_HTTP_PORT", "8000")),
        airport_service_url=os.getenv("AIRPORT_SERVICE_URL", "http://airport-service:8001"),
        itinerary_service_url=os.getenv("ITINERARY_SERVICE_URL", "http://itinerary-service:8002"),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        demo_user=os.getenv("DEMO_USER", "viajero"),
        demo_password=os.getenv("DEMO_PASSWORD", "viajero123"),
    )
