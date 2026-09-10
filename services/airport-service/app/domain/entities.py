"""Modelo de dominio del Airport Context. Estas clases no dependen de nada
externo (ni FastAPI, ni httpx, ni Redis): son el lenguaje ubicuo del
contexto, tal como lo consume el resto del sistema a través del Adapter."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Airport:
    """Entidad Aeropuerto del dominio interno, ya traducida desde la forma
    cruda de la API externa (API Colombia) por el Adapter correspondiente."""

    id: int
    name: str
    iata_code: str
    city: str
    latitude: float
    longitude: float

    def to_plotly_point(self) -> dict:
        """Formato mínimo requerido para pintar el aeropuerto en un mapa
        Plotly (lat/lon + texto de hover), sin exponer más forma de dominio
        de la necesaria al frontend."""
        return {
            "id": self.id,
            "lat": self.latitude,
            "lon": self.longitude,
            "label": f"{self.iata_code} — {self.name} ({self.city})",
        }


@dataclass(frozen=True, slots=True)
class Page:
    items: list[Airport]
    page: int
    page_size: int
    total: int
