"""Rutas REST de `/api/v1/itineraries`. Endpoints sincronos (`def`, no
`async def`) porque tocan la DB via SQLAlchemy sincrono -- FastAPI los
ejecuta automaticamente en un threadpool, sin bloquear el event loop."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ...application.dto import CreateItineraryCommand, UpdateItineraryCommand
from ...application.use_cases import (
    CreateItineraryUseCase,
    DeleteItineraryUseCase,
    GetItineraryUseCase,
    ListItinerariesUseCase,
    UpdateItineraryUseCase,
)
from ..deps import (
    get_create_use_case,
    get_current_subject,
    get_delete_use_case,
    get_get_use_case,
    get_list_use_case,
    get_update_use_case,
)
from ..schemas import (
    ItineraryCreateRequest,
    ItineraryListResponse,
    ItineraryResponse,
    ItineraryUpdateRequest,
)

router = APIRouter(
    prefix="/api/v1/itineraries",
    tags=["itineraries"],
    dependencies=[Depends(get_current_subject)],
)


@router.post("", response_model=ItineraryResponse, status_code=status.HTTP_201_CREATED)
def create_itinerary(
    body: ItineraryCreateRequest,
    use_case: Annotated[CreateItineraryUseCase, Depends(get_create_use_case)],
) -> ItineraryResponse:
    command = CreateItineraryCommand(
        user_name=body.user_name,
        origin_airport_id=body.origin_airport_id,
        destination_airport_id=body.destination_airport_id,
        travel_date=body.travel_date,
        duration_minutes=body.duration_minutes,
    )
    itinerary = use_case.execute(command)
    return ItineraryResponse.from_domain(itinerary)


@router.get("", response_model=ItineraryListResponse)
def list_itineraries(
    use_case: Annotated[ListItinerariesUseCase, Depends(get_list_use_case)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ItineraryListResponse:
    items, total = use_case.execute(page=page, page_size=page_size)
    return ItineraryListResponse(
        items=[ItineraryResponse.from_domain(it) for it in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
def get_itinerary(
    itinerary_id: UUID,
    use_case: Annotated[GetItineraryUseCase, Depends(get_get_use_case)],
) -> ItineraryResponse:
    itinerary = use_case.execute(itinerary_id)
    return ItineraryResponse.from_domain(itinerary)


@router.put("/{itinerary_id}", response_model=ItineraryResponse)
def update_itinerary(
    itinerary_id: UUID,
    body: ItineraryUpdateRequest,
    use_case: Annotated[UpdateItineraryUseCase, Depends(get_update_use_case)],
) -> ItineraryResponse:
    command = UpdateItineraryCommand(
        user_name=body.user_name,
        origin_airport_id=body.origin_airport_id,
        destination_airport_id=body.destination_airport_id,
        travel_date=body.travel_date,
        duration_minutes=body.duration_minutes,
    )
    itinerary = use_case.execute(itinerary_id, command)
    return ItineraryResponse.from_domain(itinerary)


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_itinerary(
    itinerary_id: UUID,
    use_case: Annotated[DeleteItineraryUseCase, Depends(get_delete_use_case)],
) -> None:
    use_case.execute(itinerary_id)
