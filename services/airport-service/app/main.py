"""Punto de entrada del Airport Service: arma la app FastAPI (REST +
Swagger) y el servidor gRPC, y los corre concurrentemente en el mismo
proceso (dos superficies del mismo dominio, ver sección 3-4 del README)."""
from __future__ import annotations

import asyncio
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.dependencies import build_repository
from app.api.routes import oauth_router, router as airports_router
from app.config import load_settings
from app.grpc_server.server import create_grpc_server
from app.infrastructure.oauth2 import OAuth2ClientCredentialsProvider
from common.correlation import CorrelationIdMiddleware
from common.logging import configure_json_logging, get_logger
from common.telemetry import setup_telemetry

settings = load_settings()
configure_json_logging("airport-service", level=logging.INFO)
logger = get_logger(__name__)

app = FastAPI(
    title="Airport Service API",
    description=(
        "Consulta de aeropuertos colombianos, adaptados desde API Colombia "
        "(patrón Adapter) con caché Redis y resiliencia (circuit breaker, "
        "retry, bulkhead). Ver también el servicio gRPC airport.v1.AirportService."
    ),
    version="1.0.0",
)

app.add_middleware(CorrelationIdMiddleware)
setup_telemetry(app, "airport-service")
Instrumentator().instrument(app).expose(app)

app.include_router(airports_router)
app.include_router(oauth_router)


def _problem_response(status_code: int, title: str, detail: str, instance: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _problem_response(exc.status_code, exc.detail or "HTTP error", str(exc.detail), str(request.url))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _problem_response(422, "Validation error", str(exc.errors()), str(request.url))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception")
    return _problem_response(500, "Internal server error", str(exc), str(request.url))


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "service": "airport-service"}


@app.on_event("startup")
async def on_startup() -> None:
    app.state.settings = settings
    app.state.repository = build_repository(settings)
    app.state.oauth2_provider = OAuth2ClientCredentialsProvider(
        client_id=settings.oauth2_client_id, client_secret=settings.oauth2_client_secret
    )
    app.state.grpc_server = await create_grpc_server(app.state.repository, settings.grpc_port)
    logger.info("airport-service started", extra={"grpc_port": settings.grpc_port, "http_port": settings.http_port})


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await app.state.repository.aclose()
    await app.state.grpc_server.stop(grace=5)


async def _run() -> None:
    config = uvicorn.Config(app, host="0.0.0.0", port=settings.http_port, log_config=None)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(_run())
