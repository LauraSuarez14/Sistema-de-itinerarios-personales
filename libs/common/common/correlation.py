"""Propagación de correlation id a través de servicios (trazabilidad de negocio,
independiente del trace_id/span_id de OpenTelemetry, para poder correlacionar
logs incluso si la instrumentación OTel está deshabilitada)."""
from __future__ import annotations

import contextvars
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

HEADER_NAME = "X-Correlation-Id"

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def get_correlation_id() -> str:
    return _correlation_id.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Lee X-Correlation-Id entrante (propagado por el API Gateway) o genera
    uno nuevo si el servicio es el punto de entrada, y lo agrega también a la
    respuesta para que el cliente pueda correlacionar."""

    def __init__(self, app: ASGIApp, header_name: str = HEADER_NAME) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        token = _correlation_id.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            _correlation_id.reset(token)
        response.headers[self.header_name] = correlation_id
        return response
