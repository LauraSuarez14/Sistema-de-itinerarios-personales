"""Errores de dominio del contexto Itinerary.

Estas excepciones no dependen de FastAPI ni de ningun detalle de transporte;
la capa `api/` es responsable de traducirlas a respuestas HTTP RFC7807
(application/problem+json).
"""
from __future__ import annotations

from uuid import UUID


class DomainError(Exception):
    """Clase base de todos los errores de dominio de Itinerary Service."""


class AirportNotFoundError(DomainError):
    """El Airport Service respondio explicitamente que el aeropuerto no existe
    (found=false via gRPC, o 404 via REST)."""

    def __init__(self, airport_id: int) -> None:
        self.airport_id = airport_id
        super().__init__(f"Airport with id={airport_id} was not found")


class AirportServiceUnavailableError(DomainError):
    """Ni gRPC ni el fallback REST hacia Airport Service pudieron completarse
    tras agotar los reintentos configurados (problema de red/timeout, no de
    negocio)."""

    def __init__(self, message: str = "Airport service is unavailable") -> None:
        super().__init__(message)


class ItineraryNotFoundError(DomainError):
    def __init__(self, itinerary_id: UUID) -> None:
        self.itinerary_id = itinerary_id
        super().__init__(f"Itinerary with id={itinerary_id} was not found")


class InvalidItineraryDataError(DomainError):
    """Violacion de una regla de negocio simple (duracion <= 0, fecha pasada,
    etc.), independiente de la validacion de forma que ya hace Pydantic en la
    capa API."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
