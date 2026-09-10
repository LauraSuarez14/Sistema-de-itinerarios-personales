"""Traduccion del evento de dominio (`ItineraryCreated`, implicito en el
propio caso de uso) al evento de integracion `ItineraryCreatedEvent v1`,
segun el contrato exacto documentado en `docs/asyncapi.yaml` (ADR 0003).

Esta funcion es pura (sin I/O) y por eso vive en `domain/`: es la unica
fuente de verdad sobre la FORMA del evento de integracion, para que tanto el
caso de uso (al construir la fila de outbox) como los tests puedan verificar
que el contrato no se rompe accidentalmente.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from .entities import Itinerary

EVENT_TYPE_ITINERARY_CREATED = "ItineraryCreatedEvent"
EVENT_VERSION_ITINERARY_CREATED = 1
ROUTING_KEY_ITINERARY_CREATED = "itinerary.created.v1"


def _format_occurred_at(occurred_at: datetime) -> str:
    occurred_at = occurred_at.astimezone(timezone.utc)
    return occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_itinerary_created_payload(
    itinerary: Itinerary, event_id: UUID, occurred_at: datetime
) -> dict[str, Any]:
    """Construye el payload EXACTO (ver contrato en la tarea / asyncapi.yaml)
    que se guarda en `outbox_events.payload` y que se publica tal cual en
    RabbitMQ, sin envoltorios adicionales."""
    return {
        "event_id": str(event_id),
        "event_type": EVENT_TYPE_ITINERARY_CREATED,
        "event_version": EVENT_VERSION_ITINERARY_CREATED,
        "occurred_at": _format_occurred_at(occurred_at),
        "data": {
            "itinerary_id": str(itinerary.id),
            "user_name": itinerary.user_name,
            "origin_airport": {
                "id": itinerary.origin_airport.id,
                "iata_code": itinerary.origin_airport.iata_code,
                "name": itinerary.origin_airport.name,
            },
            "destination_airport": {
                "id": itinerary.destination_airport.id,
                "iata_code": itinerary.destination_airport.iata_code,
                "name": itinerary.destination_airport.name,
            },
            "travel_date": itinerary.travel_date.isoformat(),
            "duration_minutes": itinerary.duration_minutes,
        },
    }
