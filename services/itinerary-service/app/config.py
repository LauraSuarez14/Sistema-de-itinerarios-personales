"""Configuracion centralizada, leida de variables de entorno (ver
`.env.example` en la raiz del repo -- docker-compose.yml las inyecta)."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    # --- Itinerary DB ---
    db_host: str = os.getenv("ITINERARY_DB_HOST", "itinerary-db")
    db_port: int = _get_int("ITINERARY_DB_PORT", 5432)
    db_name: str = os.getenv("ITINERARY_DB_NAME", "itinerary")
    db_user: str = os.getenv("ITINERARY_DB_USER", "itinerary")
    db_password: str = os.getenv("ITINERARY_DB_PASSWORD", "itinerary-db-pass")

    # --- Airport Service ---
    airport_grpc_url: str = os.getenv("AIRPORT_SERVICE_GRPC_URL", "airport-service:50051")
    airport_http_url: str = os.getenv("AIRPORT_SERVICE_HTTP_URL", "http://airport-service:8001")
    oauth2_client_id: str = os.getenv("OAUTH2_CLIENT_ID", "itinerary-service")
    oauth2_client_secret: str = os.getenv("OAUTH2_CLIENT_SECRET", "dev-client-secret-change-me")

    # --- Outbox / RabbitMQ ---
    outbox_relay_interval_seconds: float = _get_float("OUTBOX_RELAY_INTERVAL_SECONDS", 2.0)
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    rabbitmq_exchange: str = os.getenv("RABBITMQ_EXCHANGE", "itinerary.events")

    # --- HTTP ---
    http_port: int = _get_int("ITINERARY_HTTP_PORT", 8002)

    # --- Auth ---
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")

    # --- Observability ---
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    otel_exporter_otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
