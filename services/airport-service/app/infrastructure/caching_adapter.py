"""Adapter que decora otro `AirportRepositoryPort` (típicamente el
`ApiColombiaAdapter`) aplicando cache-aside sobre Redis. Sigue siendo un
Adapter válido del mismo puerto de dominio — el caso de uso no sabe ni le
importa si hay caché de por medio."""
from __future__ import annotations

import json
from dataclasses import asdict

import redis.asyncio as redis
from prometheus_client import Counter

from app.domain.entities import Airport, Page
from app.domain.ports import AirportRepositoryPort
from common.logging import get_logger

logger = get_logger(__name__)

cache_hits_total = Counter("airport_cache_hits_total", "Aciertos de caché Redis", ["operation"])
cache_misses_total = Counter("airport_cache_misses_total", "Fallos de caché Redis", ["operation"])


def _airport_key(airport_id: int) -> str:
    return f"airport:v1:by_id:{airport_id}"


def _list_key(page: int, page_size: int) -> str:
    return f"airport:v1:list:{page}:{page_size}"


class CachingAirportAdapter(AirportRepositoryPort):
    def __init__(self, inner: AirportRepositoryPort, redis_url: str, ttl_seconds: int) -> None:
        self._inner = inner
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds

    async def get_by_id(self, airport_id: int) -> Airport | None:
        key = _airport_key(airport_id)
        cached = await self._redis.get(key)
        if cached is not None:
            cache_hits_total.labels(operation="get_by_id").inc()
            payload = json.loads(cached)
            return Airport(**payload) if payload else None

        cache_misses_total.labels(operation="get_by_id").inc()
        airport = await self._inner.get_by_id(airport_id)
        await self._redis.set(
            key,
            json.dumps(asdict(airport)) if airport else json.dumps(None),
            ex=self._ttl_seconds,
        )
        return airport

    async def list_all(self, page: int, page_size: int) -> Page:
        key = _list_key(page, page_size)
        cached = await self._redis.get(key)
        if cached is not None:
            cache_hits_total.labels(operation="list_all").inc()
            payload = json.loads(cached)
            return Page(
                items=[Airport(**item) for item in payload["items"]],
                page=payload["page"],
                page_size=payload["page_size"],
                total=payload["total"],
            )

        cache_misses_total.labels(operation="list_all").inc()
        result = await self._inner.list_all(page, page_size)
        serializable = {
            "items": [asdict(a) for a in result.items],
            "page": result.page,
            "page_size": result.page_size,
            "total": result.total,
        }
        await self._redis.set(key, json.dumps(serializable), ex=self._ttl_seconds)
        return result

    async def aclose(self) -> None:
        await self._redis.aclose()
        inner_aclose = getattr(self._inner, "aclose", None)
        if inner_aclose is not None:
            await inner_aclose()

    async def invalidate_all(self) -> int:
        """Invalidación explícita del caché (requisito: 'cache Redis con
        invalidación'). Borra todas las claves del namespace `airport:v1:*`."""
        keys = [key async for key in self._redis.scan_iter(match="airport:v1:*")]
        if not keys:
            return 0
        return await self._redis.delete(*keys)
