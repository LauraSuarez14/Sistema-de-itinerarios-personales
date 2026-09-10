"""Adapters concretos de persistencia (Postgres via SQLAlchemy 2.0
sincrono) para `ItineraryRepositoryPort` y `OutboxRepositoryPort`."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...domain.entities import AirportSnapshot, Itinerary
from ...domain.outbox import OutboxEvent
from ...domain.ports import ItineraryRepositoryPort, OutboxRepositoryPort
from .models import ItineraryModel, OutboxEventModel


def _to_domain(model: ItineraryModel) -> Itinerary:
    return Itinerary(
        id=model.id,
        user_name=model.user_name,
        origin_airport=AirportSnapshot(
            id=model.origin_airport_id,
            iata_code=model.origin_airport_code,
            name=model.origin_airport_name,
        ),
        destination_airport=AirportSnapshot(
            id=model.destination_airport_id,
            iata_code=model.destination_airport_code,
            name=model.destination_airport_name,
        ),
        travel_date=model.travel_date,
        duration_minutes=model.duration_minutes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_domain_to_model(itinerary: Itinerary, model: ItineraryModel) -> None:
    model.id = itinerary.id
    model.user_name = itinerary.user_name
    model.origin_airport_id = itinerary.origin_airport.id
    model.origin_airport_code = itinerary.origin_airport.iata_code
    model.origin_airport_name = itinerary.origin_airport.name
    model.destination_airport_id = itinerary.destination_airport.id
    model.destination_airport_code = itinerary.destination_airport.iata_code
    model.destination_airport_name = itinerary.destination_airport.name
    model.travel_date = itinerary.travel_date
    model.duration_minutes = itinerary.duration_minutes


class SqlAlchemyItineraryRepository(ItineraryRepositoryPort):
    """Recibe una `Session` por request (inyectada por FastAPI via
    `Depends(get_session)`), consistente con el patron "unit of work por
    request" habitual en SQLAlchemy sincrono."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_with_outbox(self, itinerary: Itinerary, outbox_event: OutboxEvent) -> None:
        itinerary_model = ItineraryModel()
        _apply_domain_to_model(itinerary, itinerary_model)
        itinerary_model.created_at = itinerary.created_at
        itinerary_model.updated_at = itinerary.updated_at

        outbox_model = OutboxEventModel(
            id=outbox_event.id,
            aggregate_id=outbox_event.aggregate_id,
            event_type=outbox_event.event_type,
            payload=outbox_event.payload,
            created_at=outbox_event.created_at,
            published_at=outbox_event.published_at,
        )

        # Transactional Outbox (ADR 0002): ambas filas se agregan a la MISMA
        # sesion/transaccion y se confirman con un unico commit atomico.
        self._session.add(itinerary_model)
        self._session.add(outbox_model)
        self._session.commit()

    def get(self, itinerary_id: UUID) -> Optional[Itinerary]:
        model = self._session.get(ItineraryModel, itinerary_id)
        return _to_domain(model) if model else None

    def list(self, page: int, page_size: int) -> tuple[list[Itinerary], int]:
        total = self._session.scalar(select(func.count()).select_from(ItineraryModel)) or 0
        stmt = (
            select(ItineraryModel)
            .order_by(ItineraryModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        models = self._session.scalars(stmt).all()
        return [_to_domain(m) for m in models], total

    def update(self, itinerary: Itinerary) -> None:
        model = self._session.get(ItineraryModel, itinerary.id)
        if model is None:
            return
        _apply_domain_to_model(itinerary, model)
        self._session.commit()

    def delete(self, itinerary_id: UUID) -> bool:
        model = self._session.get(ItineraryModel, itinerary_id)
        if model is None:
            return False
        self._session.delete(model)
        self._session.commit()
        return True


class SqlAlchemyOutboxRepository(OutboxRepositoryPort):
    """Usado exclusivamente por el `OutboxRelay` (capa application), con su
    propia sesion independiente de las de los requests HTTP porque corre en
    un hilo de background con su propio ciclo de vida."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def fetch_pending(self, limit: int = 50) -> list[OutboxEvent]:
        with self._session_factory() as session:
            stmt = (
                select(OutboxEventModel)
                .where(OutboxEventModel.published_at.is_(None))
                .order_by(OutboxEventModel.created_at.asc())
                .limit(limit)
                # skip_locked evita bloquear si en el futuro corrieran varias
                # replicas del relay en paralelo (no es el caso por defecto,
                # pero es una salvaguarda barata).
                .with_for_update(skip_locked=True)
            )
            models = session.scalars(stmt).all()
            return [
                OutboxEvent(
                    id=m.id,
                    aggregate_id=m.aggregate_id,
                    event_type=m.event_type,
                    payload=m.payload,
                    created_at=m.created_at,
                    published_at=m.published_at,
                )
                for m in models
            ]

    def mark_published(self, event_id: UUID, published_at: datetime) -> None:
        with self._session_factory() as session:
            model = session.get(OutboxEventModel, event_id)
            if model is not None:
                model.published_at = published_at
                session.commit()
