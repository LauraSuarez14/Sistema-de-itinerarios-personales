"""Esquemas Pydantic (forma HTTP) del contexto Itinerary. Traducen entre
`domain.entities.Itinerary` y JSON. Solo la capa `api/` conoce Pydantic."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ..domain.entities import Itinerary


class AirportSnapshotResponse(BaseModel):
    id: int
    iata_code: str
    name: str


class ItineraryCreateRequest(BaseModel):
    user_name: str = Field(min_length=1, max_length=255)
    origin_airport_id: int = Field(gt=0)
    destination_airport_id: int = Field(gt=0)
    travel_date: date
    duration_minutes: int


class ItineraryUpdateRequest(BaseModel):
    user_name: str = Field(min_length=1, max_length=255)
    origin_airport_id: int = Field(gt=0)
    destination_airport_id: int = Field(gt=0)
    travel_date: date
    duration_minutes: int


class ItineraryResponse(BaseModel):
    id: UUID
    user_name: str
    origin_airport: AirportSnapshotResponse
    destination_airport: AirportSnapshotResponse
    travel_date: date
    duration_minutes: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, itinerary: Itinerary) -> "ItineraryResponse":
        return cls(
            id=itinerary.id,
            user_name=itinerary.user_name,
            origin_airport=AirportSnapshotResponse(
                id=itinerary.origin_airport.id,
                iata_code=itinerary.origin_airport.iata_code,
                name=itinerary.origin_airport.name,
            ),
            destination_airport=AirportSnapshotResponse(
                id=itinerary.destination_airport.id,
                iata_code=itinerary.destination_airport.iata_code,
                name=itinerary.destination_airport.name,
            ),
            travel_date=itinerary.travel_date,
            duration_minutes=itinerary.duration_minutes,
            created_at=itinerary.created_at,
            updated_at=itinerary.updated_at,
        )


class ItineraryListResponse(BaseModel):
    items: list[ItineraryResponse]
    page: int
    page_size: int
    total: int


class ProblemDetail(BaseModel):
    """RFC 7807 (application/problem+json)."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
    extra: dict[str, Any] | None = None
