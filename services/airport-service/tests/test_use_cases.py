import pytest

from app.application.use_cases import (
    GetAirportByIdUseCase,
    GetAirportsForPlotlyUseCase,
    ListAirportsUseCase,
)
from app.domain.exceptions import ExternalSourceUnavailableError
from tests.fakes import SAMPLE_AIRPORTS, FakeAirportRepository


async def test_get_airport_by_id_found():
    use_case = GetAirportByIdUseCase(repository=FakeAirportRepository())
    airport = await use_case.execute(1)
    assert airport is not None
    assert airport.iata_code == "BOG"


async def test_get_airport_by_id_not_found():
    use_case = GetAirportByIdUseCase(repository=FakeAirportRepository())
    airport = await use_case.execute(999)
    assert airport is None


async def test_get_airport_by_id_propagates_external_failure():
    use_case = GetAirportByIdUseCase(repository=FakeAirportRepository(fail=True))
    with pytest.raises(ExternalSourceUnavailableError):
        await use_case.execute(1)


async def test_list_airports_paginates():
    use_case = ListAirportsUseCase(repository=FakeAirportRepository())
    page = await use_case.execute(page=1, page_size=2)
    assert page.total == len(SAMPLE_AIRPORTS)
    assert len(page.items) == 2
    assert page.items[0].id == 1


async def test_list_airports_clamps_page_size():
    use_case = ListAirportsUseCase(repository=FakeAirportRepository())
    page = await use_case.execute(page=0, page_size=10_000)
    assert page.page == 1
    assert page.page_size == 200


async def test_plotly_points_have_expected_shape():
    use_case = GetAirportsForPlotlyUseCase(repository=FakeAirportRepository())
    points = await use_case.execute()
    assert len(points) == len(SAMPLE_AIRPORTS)
    assert {"id", "lat", "lon", "label"} <= points[0].keys()
    assert points[0]["lat"] == SAMPLE_AIRPORTS[0].latitude
