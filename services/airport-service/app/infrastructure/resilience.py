"""Primitivas de resiliencia usadas por el adapter de la API externa:
Circuit Breaker (implementación propia, async-first, sin dependencias
exóticas) y Bulkhead (aislamiento de concurrencia). El retry con backoff
exponencial + jitter se hace con `tenacity` directamente en el adapter.

Se implementa a mano en vez de usar `pybreaker` (que es síncrono) para poder
integrarse limpiamente con `httpx.AsyncClient` y con las métricas de
Prometheus que expone este servicio (requisito de observabilidad)."""
from __future__ import annotations

import asyncio
import enum
import time
from typing import Awaitable, Callable, TypeVar

from prometheus_client import Counter, Gauge

T = TypeVar("T")

circuit_breaker_state = Gauge(
    "airport_circuit_breaker_state",
    "Estado del circuit breaker hacia la API externa (0=closed, 1=open, 2=half_open)",
    ["target"],
)
circuit_breaker_trips_total = Counter(
    "airport_circuit_breaker_trips_total",
    "Cantidad de veces que el circuit breaker se abrió",
    ["target"],
)
bulkhead_rejections_total = Counter(
    "airport_bulkhead_rejections_total",
    "Cantidad de llamadas rechazadas por el bulkhead por saturación",
    ["target"],
)


class CircuitState(enum.Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


class CircuitBreakerOpenError(Exception):
    """El disyuntor está abierto: no se intenta ni siquiera llamar a la
    fuente externa, se falla rápido (fail-fast)."""


class AsyncCircuitBreaker:
    """Disyuntor clásico de 3 estados.

    - CLOSED: las llamadas pasan normalmente. Si se acumulan
      `failure_threshold` fallos consecutivos, pasa a OPEN.
    - OPEN: todas las llamadas fallan inmediatamente con
      `CircuitBreakerOpenError` (fail-fast) durante `recovery_timeout`
      segundos, para no seguir golpeando una fuente externa caída.
    - HALF_OPEN: pasado el timeout, se permite UNA llamada de prueba; si
      tiene éxito vuelve a CLOSED, si falla vuelve a OPEN.
    """

    def __init__(self, name: str, failure_threshold: int = 5,
                 recovery_timeout: float = 30.0) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()
        circuit_breaker_state.labels(target=name).set(self._state.value)

    @property
    def state(self) -> CircuitState:
        return self._state

    def _set_state(self, state: CircuitState) -> None:
        self._state = state
        circuit_breaker_state.labels(target=self.name).set(state.value)

    async def call(self, func: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self._state is CircuitState.OPEN:
                assert self._opened_at is not None
                if time.monotonic() - self._opened_at >= self.recovery_timeout:
                    self._set_state(CircuitState.HALF_OPEN)
                else:
                    raise CircuitBreakerOpenError(
                        f"circuit breaker '{self.name}' is open"
                    )

        try:
            result = await func()
        except Exception:
            await self._on_failure()
            raise
        else:
            await self._on_success()
            return result

    async def _on_success(self) -> None:
        async with self._lock:
            self._failure_count = 0
            if self._state is not CircuitState.CLOSED:
                self._set_state(CircuitState.CLOSED)

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            if self._state is CircuitState.HALF_OPEN or (
                self._failure_count >= self.failure_threshold
            ):
                self._set_state(CircuitState.OPEN)
                self._opened_at = time.monotonic()
                circuit_breaker_trips_total.labels(target=self.name).inc()


class Bulkhead:
    """Aísla la concurrencia hacia un recurso (p. ej. la API externa) de la
    concurrencia hacia otro (p. ej. Redis/DB local), para que una fuente
    lenta no agote todos los workers disponibles del servicio."""

    def __init__(self, name: str, max_concurrent_calls: int, queue_timeout: float = 2.0) -> None:
        self.name = name
        self._semaphore = asyncio.Semaphore(max_concurrent_calls)
        self._queue_timeout = queue_timeout

    async def run(self, func: Callable[[], Awaitable[T]]) -> T:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self._queue_timeout)
        except asyncio.TimeoutError:
            bulkhead_rejections_total.labels(target=self.name).inc()
            raise
        try:
            return await func()
        finally:
            self._semaphore.release()
