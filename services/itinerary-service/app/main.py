"""Punto de entrada de Itinerary Service. Ensambla la app FastAPI
(observabilidad, autenticacion, routers) y arranca/detiene el `OutboxRelay`
en los eventos `startup`/`shutdown`, tal como pide el ADR 0002."""
from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from common.correlation import CorrelationIdMiddleware
from common.logging import configure_json_logging
from common.telemetry import setup_telemetry

from .api.problem_json import register_exception_handlers
from .api.routers.health import router as health_router
from .api.routers.itineraries import router as itineraries_router
from .application.outbox_relay import OutboxRelay
from .config import settings
from .infrastructure.db.session import SessionLocal
from .infrastructure.messaging.rabbitmq_publisher import RabbitMQPublisher
from .infrastructure.db.repository import SqlAlchemyOutboxRepository
from .infrastructure.metrics import PrometheusMetrics

configure_json_logging("itinerary-service", level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Itinerary Service API",
        version="1.0.0",
        description="CRUD de itinerarios de viaje, con validacion de aeropuertos "
        "(gRPC/REST) y publicacion de eventos via Transactional Outbox.",
    )

    app.add_middleware(CorrelationIdMiddleware)
    setup_telemetry(app, "itinerary-service")

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(itineraries_router)

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    @app.on_event("startup")
    def start_outbox_relay() -> None:
        publisher = RabbitMQPublisher(
            amqp_url=settings.rabbitmq_url,
            exchange=settings.rabbitmq_exchange,
        )
        outbox_repository = SqlAlchemyOutboxRepository(session_factory=SessionLocal)
        relay = OutboxRelay(
            outbox_repository=outbox_repository,
            event_publisher=publisher,
            interval_seconds=settings.outbox_relay_interval_seconds,
            metrics=PrometheusMetrics(),
        )
        relay.start()
        app.state.outbox_relay = relay
        app.state.event_publisher = publisher
        logger.info("Itinerary Service started on port %s", settings.http_port)

    @app.on_event("shutdown")
    def stop_outbox_relay() -> None:
        relay = getattr(app.state, "outbox_relay", None)
        if relay is not None:
            relay.stop()
        publisher = getattr(app.state, "event_publisher", None)
        if publisher is not None:
            publisher.close()
        logger.info("Itinerary Service stopped")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.http_port)
