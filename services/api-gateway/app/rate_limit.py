"""Rate limiting básico por IP, implementado a mano (ventana deslizante en
memoria de proceso) en vez de agregar la dependencia `slowapi`.

Decisión de diseño: para un gateway académico de un solo proceso (sin
múltiples réplicas detrás de un balanceador) un contador en memoria es
suficiente y evita traer una dependencia extra + su almacenamiento (slowapi
normalmente recomienda Redis para producción multi-proceso, lo cual sería
sobre-ingeniería aquí). Si el gateway se escalara horizontalmente, este
limitador tendría que moverse a Redis (mismo Redis que ya usa Airport
Service) — se deja anotado como limitación conocida.

El algoritmo es "sliding window log": por cada IP se guarda la lista de
timestamps (monotonic) de sus requests en los últimos 60 segundos; si al
llegar una nueva petición ya hay `rate_limit_per_minute` marcas dentro de esa
ventana, se rechaza con 429.
"""
from __future__ import annotations

import asyncio
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.problem_json import problem_response

WINDOW_SECONDS = 60.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        limit_per_minute: int,
        protected_prefixes: tuple[str, ...],
    ) -> None:
        super().__init__(app)
        self.limit_per_minute = limit_per_minute
        self.protected_prefixes = protected_prefixes
        self._buckets: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    def _is_protected(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.protected_prefixes)

    async def dispatch(self, request: Request, call_next):
        if not self._is_protected(request.url.path):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - WINDOW_SECONDS

        async with self._lock:
            bucket = self._buckets.setdefault(client_ip, [])
            while bucket and bucket[0] < window_start:
                bucket.pop(0)
            if len(bucket) >= self.limit_per_minute:
                return problem_response(
                    429,
                    "Too Many Requests",
                    f"rate limit exceeded: max {self.limit_per_minute} requests per minute",
                    str(request.url),
                )
            bucket.append(now)

        return await call_next(request)

    def reset(self) -> None:
        """Utilidad para tests: limpia los contadores entre casos de prueba."""
        self._buckets.clear()
