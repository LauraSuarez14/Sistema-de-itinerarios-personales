"""Puertos (interfaces) del dominio de Airport Context. El caso de uso solo
conoce estas abstracciones — nunca sabe si detrás hay una API externa, un
caché Redis, o cualquier otra cosa. Esta es la mitad "Puerto" del patrón
Puerto/Adapter."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import Airport, Page


class AirportRepositoryPort(ABC):
    """Contrato para obtener aeropuertos colombianos, independiente de la
    fuente de datos real."""

    @abstractmethod
    async def get_by_id(self, airport_id: int) -> Airport | None:
        ...

    @abstractmethod
    async def list_all(self, page: int, page_size: int) -> Page:
        ...
