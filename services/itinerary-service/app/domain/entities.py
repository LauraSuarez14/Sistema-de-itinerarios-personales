"""Entidades y value objects del contexto Itinerary. Sin dependencias
externas (ni SQLAlchemy, ni Pydantic, ni grpc): solo `dataclasses` de la
libreria estandar, tal como exige la regla de dependencia de la arquitectura
hexagonal (domain no depende de nada hacia afuera)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from .errors import InvalidItineraryDataError


@dataclass(frozen=True)
class AirportSnapshot:
    """Snapshot minimo e inmutable de un aeropuerto, tomado del Airport
    Service en el momento de validar (ver ADR 0001). No es un agregado
    replicado: solo lo necesario para mostrar el itinerario sin volver a
    llamar al Airport Service en cada lectura."""

    id: int
    iata_code: str
    name: str


@dataclass
class Itinerary:
    """Agregado raiz del contexto Itinerary."""

    id: UUID
    user_name: str
    origin_airport: AirportSnapshot
    destination_airport: AirportSnapshot
    travel_date: date
    duration_minutes: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def ensure_valid_business_rules(travel_date: date, duration_minutes: int, today: date) -> None:
        """Reglas de negocio simples que no requieren I/O (a diferencia de la
        validacion de existencia de aeropuertos, que si lo requiere y por eso
        vive en el caso de uso, orquestada via `AirportValidationPort`)."""
        if duration_minutes <= 0:
            raise InvalidItineraryDataError("duration_minutes must be greater than zero")
        if travel_date < today:
            raise InvalidItineraryDataError("travel_date cannot be in the past")
