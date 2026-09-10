"""Fakes en memoria del puerto `AirportRepositoryPort`, usados para testear
la capa de aplicación sin ninguna dependencia externa (ni httpx, ni Redis)."""
from __future__ import annotations

from app.domain.entities import Airport, Page
from app.domain.exceptions import ExternalSourceUnavailableError
from app.domain.ports import AirportRepositoryPort

SAMPLE_AIRPORTS = [
    Airport(id=1, name="El Dorado", iata_code="BOG", city="Bogotá", latitude=4.70159, longitude=-74.1469),
    Airport(id=2, name="José María Córdova", iata_code="MDE", city="Rionegro", latitude=6.1645, longitude=-75.4231),
    Airport(id=3, name="Ernesto Cortissoz", iata_code="BAQ", city="Barranquilla", latitude=10.8895, longitude=-74.7807),
]


class FakeAirportRepository(AirportRepositoryPort):
    def __init__(self, airports: list[Airport] | None = None, fail: bool = False) -> None:
        self._airports = airports if airports is not None else list(SAMPLE_AIRPORTS)
        self._fail = fail

    async def get_by_id(self, airport_id: int) -> Airport | None:
        if self._fail:
            raise ExternalSourceUnavailableError("simulated outage")
        return next((a for a in self._airports if a.id == airport_id), None)

    async def list_all(self, page: int, page_size: int) -> Page:
        if self._fail:
            raise ExternalSourceUnavailableError("simulated outage")
        start = (page - 1) * page_size
        end = start + page_size
        return Page(items=self._airports[start:end], page=page, page_size=page_size, total=len(self._airports))
