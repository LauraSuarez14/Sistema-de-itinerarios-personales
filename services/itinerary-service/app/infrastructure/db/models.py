"""Modelos ORM de SQLAlchemy 2.0 (sincrono, driver psycopg2-binary). Solo se
usan dentro de `infrastructure/`; el dominio nunca importa este modulo."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ItineraryModel(Base):
    __tablename__ = "itineraries"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_name: Mapped[str] = mapped_column(String(255), nullable=False)

    origin_airport_id: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_airport_code: Mapped[str] = mapped_column(String(10), nullable=False)
    origin_airport_name: Mapped[str] = mapped_column(String(255), nullable=False)

    destination_airport_id: Mapped[int] = mapped_column(Integer, nullable=False)
    destination_airport_code: Mapped[str] = mapped_column(String(10), nullable=False)
    destination_airport_name: Mapped[str] = mapped_column(String(255), nullable=False)

    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
