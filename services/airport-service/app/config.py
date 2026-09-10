"""Configuración del Airport Service, cargada de variables de entorno (con
fallback dinámico a Vault vía `common.vault_client`)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from common.vault_client import load_secrets


@dataclass(frozen=True)
class Settings:
    api_colombia_base_url: str
    toxiproxy_enabled: bool
    toxiproxy_proxy_url: str
    redis_url: str
    cache_ttl_seconds: int
    http_port: int
    grpc_port: int
    oauth2_client_id: str
    oauth2_client_secret: str
    jwt_secret_key: str


def load_settings() -> Settings:
    secrets = load_secrets(
        mount_path="airport-service",
        env_fallback_keys=["OAUTH2_CLIENT_SECRET", "JWT_SECRET_KEY"],
    )

    return Settings(
        api_colombia_base_url=os.getenv(
            "API_COLOMBIA_BASE_URL", "https://api-colombia.com/api/v1"
        ),
        toxiproxy_enabled=os.getenv("TOXIPROXY_ENABLED", "false").lower() == "true",
        toxiproxy_proxy_url=os.getenv("TOXIPROXY_PROXY_URL", "http://toxiproxy:8666"),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        cache_ttl_seconds=int(os.getenv("AIRPORT_CACHE_TTL_SECONDS", "3600")),
        http_port=int(os.getenv("AIRPORT_HTTP_PORT", "8001")),
        grpc_port=int(os.getenv("AIRPORT_GRPC_PORT", "50051")),
        oauth2_client_id=os.getenv("OAUTH2_CLIENT_ID", "itinerary-service"),
        oauth2_client_secret=secrets.get(
            "OAUTH2_CLIENT_SECRET", os.getenv("OAUTH2_CLIENT_SECRET", "dev-client-secret-change-me")
        ),
        jwt_secret_key=secrets.get(
            "JWT_SECRET_KEY", os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
        ),
    )
