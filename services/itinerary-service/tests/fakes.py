"""Fakes en memoria de los puertos del dominio, usados por los tests de
`application/` para no requerir Postgres, RabbitMQ ni grpc reales."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.entities import AirportSnapshot, Itinerary
from app.domain.errors import AirportServiceUnavailableError
from app.domain.outbox import OutboxEvent
from app.domain.ports import (
    AirportValidationPort,
    EventPublisherPort,
    ItineraryRepositoryPort,
    OutboxRepositoryPort,
)


class FakeAirportValidator(AirportValidationPort):
    """Airport validator configurable: `airports` mapea id -> AirportSnapshot
    (ausencia de la key = "no existe"). Si `unavailable` es True, simula que
    el Airport Service no responde en absoluto."""

    def __init__(self, airports: Optional[dict[int, AirportSnapshot]] = None, unavailable: bool = False) -> None:
        self.airports = airports or {}
        self.unavailable = unavailable
        self.calls: list[int] = []

    def get_airport(self, airport_id: int) -> Optional[AirportSnapshot]:
        self.calls.append(airport_id)
        if self.unavailable:
            raise AirportServiceUnavailableError("airport service down (fake)")
        return self.airports.get(airport_id)


class FakeItineraryRepository(ItineraryRepositoryPort):
    def __init__(self) -> None:
        self._itineraries: dict[UUID, Itinerary] = {}
        self.outbox_events: dict[UUID, OutboxEvent] = {}

    def add_with_outbox(self, itinerary: Itinerary, outbox_event: OutboxEvent) -> None:
        # Simula la atomicidad de la transaccion real: ambas escrituras
        # ocurren "juntas" en el dict en memoria.
        self._itineraries[itinerary.id] = itinerary
        self.outbox_events[outbox_event.id] = outbox_event

    def get(self, itinerary_id: UUID) -> Optional[Itinerary]:
        return self._itineraries.get(itinerary_id)

    def list(self, page: int, page_size: int) -> tuple[list[Itinerary], int]:
        items = sorted(self._itineraries.values(), key=lambda it: it.created_at)
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    def update(self, itinerary: Itinerary) -> None:
        self._itineraries[itinerary.id] = itinerary

    def delete(self, itinerary_id: UUID) -> bool:
        return self._itineraries.pop(itinerary_id, None) is not None


class FakeOutboxRepository(OutboxRepositoryPort):
    def __init__(self, events: Optional[list[OutboxEvent]] = None) -> None:
        self._events: dict[UUID, OutboxEvent] = {e.id: e for e in (events or [])}

    def add(self, event: OutboxEvent) -> None:
        self._events[event.id] = event

    def fetch_pending(self, limit: int = 50) -> list[OutboxEvent]:
        pending = [e for e in self._events.values() if e.published_at is None]
        pending.sort(key=lambda e: e.created_at)
        return pending[:limit]

    def mark_published(self, event_id: UUID, published_at: datetime) -> None:
        event = self._events[event_id]
        event.published_at = published_at


class FakeEventPublisher(EventPublisherPort):
    """Publisher configurable: `should_succeed` simula si el broker confirma
    (publisher confirms) o no. Registra cada intento en `published`."""

    def __init__(self, should_succeed: bool = True) -> None:
        self.should_succeed = should_succeed
        self.published: list[tuple[str, dict]] = []

    def publish(self, routing_key: str, payload: dict) -> bool:
        self.published.append((routing_key, payload))
        return self.should_succeed
