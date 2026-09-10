"""Esquema JSON EXACTO del evento de integracion `ItineraryCreatedEvent v1`
(contrato publicado por Itinerary Service via Transactional Outbox, ver
`docs/asyncapi.yaml` y `docs/adr/0003-eventos-dominio-vs-integracion.md`).

Se valida aqui, ANTES de invocar la Lambda, para no gastar una invocacion en
un mensaje corrupto: si el body no matchea el contrato, se manda directo a
dead-letter sin reintentos (reintentar basura nunca la convierte en un
mensaje valido).
"""
from __future__ import annotations

from typing import Any

import jsonschema

EVENT_TYPE_ITINERARY_CREATED = "ItineraryCreatedEvent"
EVENT_VERSION_ITINERARY_CREATED = 1

_AIRPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["id", "iata_code", "name"],
    "properties": {
        "id": {"type": "integer"},
        "iata_code": {"type": "string", "minLength": 3, "maxLength": 3},
        "name": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}

ITINERARY_CREATED_EVENT_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ItineraryCreatedEvent",
    "type": "object",
    "required": ["event_id", "event_type", "event_version", "occurred_at", "data"],
    "properties": {
        "event_id": {"type": "string", "minLength": 1},
        "event_type": {"type": "string", "const": EVENT_TYPE_ITINERARY_CREATED},
        "event_version": {"type": "integer", "const": EVENT_VERSION_ITINERARY_CREATED},
        "occurred_at": {"type": "string", "minLength": 1},
        "data": {
            "type": "object",
            "required": [
                "itinerary_id",
                "user_name",
                "origin_airport",
                "destination_airport",
                "travel_date",
                "duration_minutes",
            ],
            "properties": {
                "itinerary_id": {"type": "string", "minLength": 1},
                "user_name": {"type": "string", "minLength": 1},
                "origin_airport": _AIRPORT_SCHEMA,
                "destination_airport": _AIRPORT_SCHEMA,
                "travel_date": {"type": "string", "minLength": 1},
                "duration_minutes": {"type": "integer"},
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}


class SchemaValidationError(ValueError):
    """El body del mensaje no matchea el contrato de ItineraryCreatedEvent."""


def validate_itinerary_created_event(payload: Any) -> None:
    """Lanza `SchemaValidationError` si `payload` no matchea el contrato
    exacto de `ItineraryCreatedEvent v1`. No devuelve nada si es valido."""
    try:
        jsonschema.validate(instance=payload, schema=ITINERARY_CREATED_EVENT_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise SchemaValidationError(str(exc)) from exc
