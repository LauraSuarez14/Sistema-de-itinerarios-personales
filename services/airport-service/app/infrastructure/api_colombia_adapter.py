"""El Adapter del patrón Puerto/Adapter: implementa `AirportRepositoryPort`
traduciendo la forma cruda de la API Colombia al modelo de dominio `Airport`.

Nota de traducción importante: se verificó contra la API real
(`GET https://api-colombia.com/api/v1/Airport/2`) que sus campos `latitude`
y `longitude` están intercambiados (p. ej. para el aeropuerto de Barranquilla
devuelve `latitude=-74.78` y `longitude=10.88`, cuando Barranquilla está en
~10.88°N, -74.78°O). Este es exactamente el tipo de detalle de la fuente
externa que el Adapter debe absorber para que el dominio y el resto del
sistema trabajen siempre con coordenadas correctas."""
from __future__ import annotations

from app.domain.entities import Airport, Page
from app.domain.ports import AirportRepositoryPort
from app.infrastructure.api_colombia_client import ApiColombiaClient


def _to_domain(raw: dict) -> Airport:
    city = raw.get("city") or {}
    return Airport(
        id=raw["id"],
        name=raw.get("name") or "",
        iata_code=raw.get("iataCode") or "N/A",
        city=city.get("name") or "",
        # Campos intercambiados en la API externa: ver nota del módulo.
        latitude=raw.get("longitude") or 0.0,
        longitude=raw.get("latitude") or 0.0,
    )


class ApiColombiaAdapter(AirportRepositoryPort):
    def __init__(self, client: ApiColombiaClient) -> None:
        self._client = client

    async def get_by_id(self, airport_id: int) -> Airport | None:
        raw = await self._client.get_airport(airport_id)
        if raw is None:
            return None
        return _to_domain(raw)

    async def list_all(self, page: int, page_size: int) -> Page:
        all_raw = await self._client.list_airports()
        total = len(all_raw)
        start = (page - 1) * page_size
        end = start + page_size
        items = [_to_domain(raw) for raw in all_raw[start:end]]
        return Page(items=items, page=page, page_size=page_size, total=total)

    async def aclose(self) -> None:
        await self._client.aclose()
