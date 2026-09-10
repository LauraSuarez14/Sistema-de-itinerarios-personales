"""Casos de uso del Airport Context. Dependen únicamente del puerto
`AirportRepositoryPort` (inyectado), nunca de un adapter concreto."""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities import Airport, Page
from app.domain.ports import AirportRepositoryPort


@dataclass
class GetAirportByIdUseCase:
    repository: AirportRepositoryPort

    async def execute(self, airport_id: int) -> Airport | None:
        return await self.repository.get_by_id(airport_id)


@dataclass
class ListAirportsUseCase:
    repository: AirportRepositoryPort

    async def execute(self, page: int, page_size: int) -> Page:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 200)
        return await self.repository.list_all(page, page_size)


@dataclass
class GetAirportsForPlotlyUseCase:
    """Caso de uso dedicado a transformar los datos al formato requerido por
    Plotly, tal como lo pide explícitamente el enunciado del proyecto."""

    repository: AirportRepositoryPort

    async def execute(self, limit: int = 200) -> list[dict]:
        result = await self.repository.list_all(page=1, page_size=limit)
        return [airport.to_plotly_point() for airport in result.items]
