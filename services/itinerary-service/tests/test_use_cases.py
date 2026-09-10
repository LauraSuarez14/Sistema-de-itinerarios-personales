from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.dto import CreateItineraryCommand, UpdateItineraryCommand
from app.application.use_cases import (
    CreateItineraryUseCase,
    DeleteItineraryUseCase,
    GetItineraryUseCase,
    ListItinerariesUseCase,
    UpdateItineraryUseCase,
)
from app.domain.entities import AirportSnapshot
from app.domain.errors import AirportNotFoundError, AirportServiceUnavailableError, ItineraryNotFoundError
from tests.fakes import FakeAirportValidator, FakeItineraryRepository

FIXED_NOW = datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc)
FIXED_ID = UUID("11111111-1111-1111-1111-111111111111")


def fixed_clock() -> datetime:
    return FIXED_NOW


def make_id_factory():
    ids = iter([UUID(int=i) for i in range(1, 1000)])
    return lambda: next(ids)


BOG = AirportSnapshot(id=1, iata_code="BOG", name="El Dorado")
MDE = AirportSnapshot(id=2, iata_code="MDE", name="Jose Maria Cordova")


def make_create_command(**overrides) -> CreateItineraryCommand:
    defaults = dict(
        user_name="Sebastian",
        origin_airport_id=1,
        destination_airport_id=2,
        travel_date=date(2026, 10, 1),
        duration_minutes=65,
    )
    defaults.update(overrides)
    return CreateItineraryCommand(**defaults)


def test_create_itinerary_success_stores_itinerary_and_outbox_event():
    repo = FakeItineraryRepository()
    validator = FakeAirportValidator(airports={1: BOG, 2: MDE})
    use_case = CreateItineraryUseCase(repo, validator, clock=fixed_clock, id_factory=make_id_factory())

    itinerary = use_case.execute(make_create_command())

    assert repo.get(itinerary.id) is itinerary
    assert itinerary.origin_airport == BOG
    assert itinerary.destination_airport == MDE
    assert len(repo.outbox_events) == 1
    outbox_event = next(iter(repo.outbox_events.values()))
    assert outbox_event.aggregate_id == itinerary.id
    assert outbox_event.payload["data"]["itinerary_id"] == str(itinerary.id)
    assert outbox_event.published_at is None


def test_create_itinerary_fails_when_origin_airport_not_found():
    repo = FakeItineraryRepository()
    validator = FakeAirportValidator(airports={2: MDE})  # origin 1 missing
    use_case = CreateItineraryUseCase(repo, validator, clock=fixed_clock)

    with pytest.raises(AirportNotFoundError) as exc_info:
        use_case.execute(make_create_command())

    assert exc_info.value.airport_id == 1
    assert len(repo.outbox_events) == 0


def test_create_itinerary_fails_when_destination_airport_not_found():
    repo = FakeItineraryRepository()
    validator = FakeAirportValidator(airports={1: BOG})  # destination 2 missing
    use_case = CreateItineraryUseCase(repo, validator, clock=fixed_clock)

    with pytest.raises(AirportNotFoundError) as exc_info:
        use_case.execute(make_create_command())

    assert exc_info.value.airport_id == 2


def test_create_itinerary_fails_when_airport_service_unavailable():
    repo = FakeItineraryRepository()
    validator = FakeAirportValidator(unavailable=True)
    use_case = CreateItineraryUseCase(repo, validator, clock=fixed_clock)

    with pytest.raises(AirportServiceUnavailableError):
        use_case.execute(make_create_command())

    assert len(repo.outbox_events) == 0


def test_create_itinerary_rejects_non_positive_duration_without_calling_airport_service():
    repo = FakeItineraryRepository()
    validator = FakeAirportValidator(airports={1: BOG, 2: MDE})
    use_case = CreateItineraryUseCase(repo, validator, clock=fixed_clock)

    with pytest.raises(Exception):
        use_case.execute(make_create_command(duration_minutes=0))

    # La regla de negocio se valida antes de llamar al airport service.
    assert validator.calls == []


def test_get_itinerary_not_found_raises():
    repo = FakeItineraryRepository()
    use_case = GetItineraryUseCase(repo)

    with pytest.raises(ItineraryNotFoundError):
        use_case.execute(uuid4())


def test_update_itinerary_revalidates_only_changed_airports():
    repo = FakeItineraryRepository()
    validator = FakeAirportValidator(airports={1: BOG, 2: MDE})
    create_uc = CreateItineraryUseCase(repo, validator, clock=fixed_clock, id_factory=make_id_factory())
    itinerary = create_uc.execute(make_create_command())
    validator.calls.clear()

    CDG = AirportSnapshot(id=3, iata_code="CDG", name="Charles de Gaulle")
    validator.airports[3] = CDG
    update_uc = UpdateItineraryUseCase(repo, validator, clock=fixed_clock)

    updated = update_uc.execute(
        itinerary.id,
        UpdateItineraryCommand(
            user_name="Sebastian E.",
            origin_airport_id=1,  # unchanged -> should NOT re-call validator
            destination_airport_id=3,  # changed -> should call validator
            travel_date=date(2026, 11, 1),
            duration_minutes=120,
        ),
    )

    assert updated.destination_airport == CDG
    assert updated.origin_airport == BOG
    assert validator.calls == [3]
    assert repo.get(itinerary.id).user_name == "Sebastian E."


def test_update_itinerary_not_found_raises():
    repo = FakeItineraryRepository()
    validator = FakeAirportValidator(airports={1: BOG, 2: MDE})
    use_case = UpdateItineraryUseCase(repo, validator, clock=fixed_clock)

    with pytest.raises(ItineraryNotFoundError):
        use_case.execute(
            uuid4(),
            UpdateItineraryCommand(
                user_name="x",
                origin_airport_id=1,
                destination_airport_id=2,
                travel_date=date(2026, 11, 1),
                duration_minutes=30,
            ),
        )


def test_delete_itinerary_removes_it():
    repo = FakeItineraryRepository()
    validator = FakeAirportValidator(airports={1: BOG, 2: MDE})
    itinerary = CreateItineraryUseCase(repo, validator, clock=fixed_clock).execute(make_create_command())

    DeleteItineraryUseCase(repo).execute(itinerary.id)

    assert repo.get(itinerary.id) is None


def test_delete_itinerary_not_found_raises():
    repo = FakeItineraryRepository()
    with pytest.raises(ItineraryNotFoundError):
        DeleteItineraryUseCase(repo).execute(uuid4())


def test_list_itineraries_paginates():
    repo = FakeItineraryRepository()
    validator = FakeAirportValidator(airports={1: BOG, 2: MDE})
    create_uc = CreateItineraryUseCase(repo, validator, clock=fixed_clock, id_factory=make_id_factory())
    for _ in range(5):
        create_uc.execute(make_create_command())

    list_uc = ListItinerariesUseCase(repo)
    items_page1, total = list_uc.execute(page=1, page_size=2)
    items_page2, _ = list_uc.execute(page=2, page_size=2)
    items_page3, _ = list_uc.execute(page=3, page_size=2)

    assert total == 5
    assert len(items_page1) == 2
    assert len(items_page2) == 2
    assert len(items_page3) == 1
