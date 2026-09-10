from __future__ import annotations

import copy

import pytest

from app.schema import SchemaValidationError, validate_itinerary_created_event

VALID_EVENT = {
    "event_id": "5c9c6f2a-1111-4b2a-9c3d-abcdef123456",
    "event_type": "ItineraryCreatedEvent",
    "event_version": 1,
    "occurred_at": "2026-09-09T12:00:00Z",
    "data": {
        "itinerary_id": "e2b1c0d0-2222-4b2a-9c3d-abcdef654321",
        "user_name": "Sebastian",
        "origin_airport": {"id": 1, "iata_code": "BOG", "name": "El Dorado"},
        "destination_airport": {"id": 2, "iata_code": "MDE", "name": "Jose Maria Cordova"},
        "travel_date": "2026-10-01",
        "duration_minutes": 65,
    },
}


def test_valid_event_passes():
    validate_itinerary_created_event(VALID_EVENT)  # no debe lanzar


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.pop("event_id"),
        lambda e: e.__setitem__("event_type", "SomethingElse"),
        lambda e: e.__setitem__("event_version", 2),
        lambda e: e["data"].pop("itinerary_id"),
        lambda e: e["data"].pop("origin_airport"),
        lambda e: e["data"]["origin_airport"].pop("iata_code"),
        lambda e: e["data"].__setitem__("duration_minutes", "sixty-five"),
        lambda e: e.pop("data"),
    ],
)
def test_invalid_events_are_rejected(mutate):
    event = copy.deepcopy(VALID_EVENT)
    mutate(event)
    with pytest.raises(SchemaValidationError):
        validate_itinerary_created_event(event)


def test_non_object_payload_is_rejected():
    with pytest.raises(SchemaValidationError):
        validate_itinerary_created_event(["not", "an", "object"])
