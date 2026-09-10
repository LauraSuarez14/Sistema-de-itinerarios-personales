"""Punto de entrada del API Gateway / BFF.

Es infraestructura pura (routing, auth demo, rate limiting, propagación de
headers/correlation id) — a propósito NO contiene lógica de negocio: nunca
valida aeropuertos, fechas de viaje, ni reglas de itinerarios; eso vive en
los servicios correspondientes. El gateway solo decide "a dónde reenviar" y
"quién puede pasar" (rate limit) y "quién es" (JWT demo).

Se usa un patrón de "app factory" (`create_app`) en vez de construir un único
`app` global con efectos secundarios de import (leer settings, configurar
logging) para que los tests puedan crear instancias aisladas con su propia
configuración (p. ej. un rate limit bajo) sin interferir entre sí. El punto
de entrada real (`python -m app.main` / Dockerfile CMD) simplemente llama a
`create_app()` con la configuración real de variables de entorno.
"""
from __future__ import annotations

import logging

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import router as auth_router
from app.config import Settings, load_settings
from app.problem_json import problem_response
from app.proxy import build_proxy_router
from app.rate_limit import RateLimitMiddleware
from common.correlation import CorrelationIdMiddleware
from common.logging import configure_json_logging, get_logger
from common.telemetry import setup_telemetry

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    app = FastAPI(
        title="API Gateway / BFF",
        description=(
            "Punto de entrada único del sistema de itinerarios. Emite el JWT "
            "demo de autenticación, aplica rate limiting básico, y hace proxy "
            "transparente (sin lógica de negocio) hacia Airport Service e "
            "Itinerary Service, propagando el token JWT del usuario y el "
            "X-Correlation-Id. Las rutas de proxy (/api/v1/airports*, "
            "/api/v1/itineraries*, /oauth/token) exponen exactamente el "
            "contrato de los servicios destino — ver sus propios /docs."
        ),
        version="1.0.0",
    )

    app.state.settings = settings

    # CORS abierto: el frontend estático (nginx, puerto 8080) y el gateway
    # (puerto 8000) son orígenes distintos desde el navegador. Para un reto
    # académico sin dominio real ni usuarios de producción, se permite
    # cualquier origen; en un despliegue real se restringiría a la URL
    # pública del frontend.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # El gateway es el punto de entrada del sistema: genera el
    # X-Correlation-Id si el cliente no lo trae, y lo agrega en la respuesta.
    # La propagación hacia los servicios internos ocurre explícitamente en
    # app/proxy.py.
    app.add_middleware(CorrelationIdMiddleware)

    app.add_middleware(
        RateLimitMiddleware,
        limit_per_minute=settings.rate_limit_per_minute,
        protected_prefixes=("/api/v1/airports", "/api/v1/itineraries", "/oauth/token"),
    )

    setup_telemetry(app, "api-gateway")
    Instrumentator().instrument(app).expose(app)

    app.include_router(auth_router)
    app.include_router(
        build_proxy_router("/api/v1/airports", lambda req: req.app.state.settings.airport_service_url)
    )
    app.include_router(
        build_proxy_router("/api/v1/itineraries", lambda req: req.app.state.settings.itinerary_service_url)
    )
    app.include_router(
        build_proxy_router("/oauth/token", lambda req: req.app.state.settings.airport_service_url)
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem_response(exc.status_code, exc.detail or "HTTP error", str(exc.detail), str(request.url))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem_response(422, "Validation error", str(exc.errors()), str(request.url))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception in api-gateway")
        return problem_response(500, "Internal server error", str(exc), str(request.url))

    @app.get("/health", tags=["health"], summary="Liveness/readiness probe (sin auth, sin rate limit)")
    async def health() -> dict:
        # Deliberadamente no verifica los servicios río abajo: un probe de
        # k8s debe reflejar la salud del propio proceso del gateway, no la de
        # otros servicios (eso ya lo exponen sus propios /health individuales).
        return {"status": "ok", "service": "api-gateway"}

    @app.on_event("startup")
    async def on_startup() -> None:
        app.state.http_client = httpx.AsyncClient()
        logger.info("api-gateway started", extra={"http_port": settings.http_port})

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await app.state.http_client.aclose()

    return app


configure_json_logging("api-gateway", level=logging.INFO)
app = create_app()


def _run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=app.state.settings.http_port, log_config=None)


if __name__ == "__main__":
    _run()
