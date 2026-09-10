"""Cliente HTTP crudo hacia la API pública API Colombia, con tolerancia a
fallos: timeout explícito, reintentos con backoff exponencial + jitter
(tenacity), circuit breaker y bulkhead (resilience.py). Este módulo NO sabe
nada del modelo de dominio — solo devuelve el JSON crudo de la API externa.
La traducción a dominio ocurre en `api_colombia_adapter.py` (el Adapter)."""
from __future__ import annotations

import asyncio

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.domain.exceptions import ExternalSourceUnavailableError
from app.infrastructure.resilience import AsyncCircuitBreaker, Bulkhead, CircuitBreakerOpenError
from common.logging import get_logger

logger = get_logger(__name__)

RETRYABLE_EXCEPTIONS = (httpx.TransportError, httpx.TimeoutException)


class ApiColombiaClient:
    """Encapsula TODO el acceso HTTP a api-colombia.com. Bulkhead separa esta
    concurrencia externa de la concurrencia local (Redis), y el circuit
    breaker protege contra fallas sostenidas de la fuente externa."""

    def __init__(self, base_url: str, timeout_seconds: float = 5.0,
                 max_concurrent_calls: int = 10) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_seconds),
            limits=httpx.Limits(max_connections=max_concurrent_calls, max_keepalive_connections=5),
        )
        self._breaker = AsyncCircuitBreaker(
            name="api-colombia", failure_threshold=5, recovery_timeout=30.0
        )
        self._bulkhead = Bulkhead(name="api-colombia", max_concurrent_calls=max_concurrent_calls)

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.2, max=2.0),
        reraise=True,
    )
    async def _get(self, path: str) -> httpx.Response:
        response = await self._client.get(path)
        if response.status_code >= 500:
            raise httpx.TransportError(f"upstream {response.status_code} on {path}")
        return response

    async def _resilient_get(self, path: str) -> httpx.Response:
        async def call() -> httpx.Response:
            return await self._bulkhead.run(lambda: self._get(path))

        try:
            return await self._breaker.call(call)
        except CircuitBreakerOpenError as exc:
            logger.warning("circuit breaker open, failing fast", extra={"path": path})
            raise ExternalSourceUnavailableError("circuit breaker open") from exc
        except (httpx.TransportError, httpx.TimeoutException, asyncio.TimeoutError) as exc:
            logger.warning("api colombia unreachable after retries", extra={"path": path, "error": str(exc)})
            raise ExternalSourceUnavailableError(str(exc)) from exc

    async def get_airport(self, airport_id: int) -> dict | None:
        response = await self._resilient_get(f"/Airport/{airport_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def list_airports(self) -> list[dict]:
        response = await self._resilient_get("/Airport")
        response.raise_for_status()
        data = response.json()
        return [item for item in data if item is not None]
