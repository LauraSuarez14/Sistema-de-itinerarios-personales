"""Casos de uso del contexto Itinerary. Dependen unicamente de los puertos
definidos en `domain/ports.py` -- nunca de SQLAlchemy, grpc, pika ni
FastAPI -- por lo que se pueden testear con fakes en memoria."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import UUID, uuid4

from ..domain.entities import Itinerary
from ..domain.errors import AirportNotFoundError, ItineraryNotFoundError
from ..domain.events import ROUTING_KEY_ITINERARY_CREATED, build_itinerary_created_payload
from ..domain.outbox import OutboxEvent
from ..domain.ports import AirportValidationPort, ItineraryRepositoryPort

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CreateItineraryUseCase:
    def __init__(
        self,
        repository: ItineraryRepositoryPort,
        airport_validator: AirportValidationPort,
        clock: Clock = _utcnow,
        id_factory: IdFactory = uuid4,
    ) -> None:
        self._repository = repository
        self._airport_validator = airport_validator
        self._clock = clock
        self._id_factory = id_factory

    def execute(self, command) -> Itinerary:
        now = self._clock()
        Itinerary.ensure_valid_business_rules(
            travel_date=command.travel_date,
            duration_minutes=command.duration_minutes,
            today=now.date(),
        )

        origin_snapshot = self._airport_validator.get_airport(command.origin_airport_id)
        if origin_snapshot is None:
            raise AirportNotFoundError(command.origin_airport_id)

        destination_snapshot = self._airport_validator.get_airport(command.destination_airport_id)
        if destination_snapshot is None:
            raise AirportNotFoundError(command.destination_airport_id)

        itinerary = Itinerary(
            id=self._id_factory(),
            user_name=command.user_name,
            origin_airport=origin_snapshot,
            destination_airport=destination_snapshot,
            travel_date=command.travel_date,
            duration_minutes=command.duration_minutes,
            created_at=now,
            updated_at=now,
        )

        event_id = self._id_factory()
        payload = build_itinerary_created_payload(itinerary, event_id=event_id, occurred_at=now)
        outbox_event = OutboxEvent(
            id=event_id,
            aggregate_id=itinerary.id,
            event_type=ROUTING_KEY_ITINERARY_CREATED,
            payload=payload,
            created_at=now,
            published_at=None,
        )

        self._repository.add_with_outbox(itinerary, outbox_event)
        return itinerary


class GetItineraryUseCase:
    def __init__(self, repository: ItineraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self, itinerary_id: UUID) -> Itinerary:
        itinerary = self._repository.get(itinerary_id)
        if itinerary is None:
            raise ItineraryNotFoundError(itinerary_id)
        return itinerary


class ListItinerariesUseCase:
    def __init__(self, repository: ItineraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self, page: int, page_size: int) -> tuple[list[Itinerary], int]:
        return self._repository.list(page=page, page_size=page_size)


class UpdateItineraryUseCase:
    def __init__(
        self,
        repository: ItineraryRepositoryPort,
        airport_validator: AirportValidationPort,
        clock: Clock = _utcnow,
    ) -> None:
        self._repository = repository
        self._airport_validator = airport_validator
        self._clock = clock

    def execute(self, itinerary_id: UUID, command) -> Itinerary:
        existing = self._repository.get(itinerary_id)
        if existing is None:
            raise ItineraryNotFoundError(itinerary_id)

        now = self._clock()
        Itinerary.ensure_valid_business_rules(
            travel_date=command.travel_date,
            duration_minutes=command.duration_minutes,
            today=now.date(),
        )

        if command.origin_airport_id == existing.origin_airport.id:
            origin_snapshot = existing.origin_airport
        else:
            origin_snapshot = self._airport_validator.get_airport(command.origin_airport_id)
            if origin_snapshot is None:
                raise AirportNotFoundError(command.origin_airport_id)

        if command.destination_airport_id == existing.destination_airport.id:
            destination_snapshot = existing.destination_airport
        else:
            destination_snapshot = self._airport_validator.get_airport(command.destination_airport_id)
            if destination_snapshot is None:
                raise AirportNotFoundError(command.destination_airport_id)

        updated = Itinerary(
            id=existing.id,
            user_name=command.user_name,
            origin_airport=origin_snapshot,
            destination_airport=destination_snapshot,
            travel_date=command.travel_date,
            duration_minutes=command.duration_minutes,
            created_at=existing.created_at,
            updated_at=now,
        )
        self._repository.update(updated)
        return updated


class DeleteItineraryUseCase:
    def __init__(self, repository: ItineraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self, itinerary_id: UUID) -> None:
        deleted = self._repository.delete(itinerary_id)
        if not deleted:
            raise ItineraryNotFoundError(itinerary_id)
