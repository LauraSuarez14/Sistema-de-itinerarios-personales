from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.domain.entities import AirportSnapshot, Itinerary
from app.domain.errors import InvalidItineraryDataError
from app.domain.events import (
    EVENT_TYPE_ITINERARY_CREATED,
    EVENT_VERSION_ITINERARY_CREATED,
    build_itinerary_created_payload,
)


def test_ensure_valid_business_rules_accepts_future_date_and_positive_duration():
    Itinerary.ensure_valid_business_rules(
        travel_date=date(2026, 12, 1), duration_minutes=90, today=date(2026, 9, 9)
    )  # no exception


def test_ensure_valid_business_rules_rejects_zero_or_negative_duration():
    with pytest.raises(InvalidItineraryDataError):
        Itinerary.ensure_valid_business_rules(
            travel_date=date(2026, 12, 1), duration_minutes=0, today=date(2026, 9, 9)
        )


def test_ensure_valid_business_rules_rejects_past_travel_date():
    with pytest.raises(InvalidItineraryDataError):
        Itinerary.ensure_valid_business_rules(
            travel_date=date(2020, 1, 1), duration_minutes=60, today=date(2026, 9, 9)
        )


def test_build_itinerary_created_payload_matches_integration_contract():
    itinerary = Itinerary(
        id=uuid4(),
        user_name="Sebastian",
        origin_airport=AirportSnapshot(id=1, iata_code="BOG", name="El Dorado"),
        destination_airport=AirportSnapshot(id=2, iata_code="MDE", name="Jose Maria Cordova"),
        travel_date=date(2026, 10, 1),
        duration_minutes=65,
        created_at=datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc),
    )
    event_id = uuid4()
    occurred_at = datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc)

    payload = build_itinerary_created_payload(itinerary, event_id=event_id, occurred_at=occurred_at)

    assert payload == {
        "event_id": str(event_id),
        "event_type": EVENT_TYPE_ITINERARY_CREATED,
        "event_version": EVENT_VERSION_ITINERARY_CREATED,
        "occurred_at": "2026-09-09T12:00:00Z",
        "data": {
            "itinerary_id": str(itinerary.id),
            "user_name": "Sebastian",
            "origin_airport": {"id": 1, "iata_code": "BOG", "name": "El Dorado"},
            "destination_airport": {"id": 2, "iata_code": "MDE", "name": "Jose Maria Cordova"},
            "travel_date": "2026-10-01",
            "duration_minutes": 65,
        },
    }
    assert EVENT_TYPE_ITINERARY_CREATED == "ItineraryCreatedEvent"
    assert EVENT_VERSION_ITINERARY_CREATED == 1
