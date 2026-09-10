"""Routers REST del Airport Service, bajo el prefijo versionado /api/v1."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request

from app.api.dependencies import (
    get_airport_by_id_use_case,
    get_oauth2_provider,
    get_plotly_use_case,
    get_repository,
    get_list_airports_use_case,
    require_valid_token,
)
from app.api.schemas import (
    AirportOut,
    CacheInvalidationResult,
    PageOut,
    PlotlyPointOut,
    TokenResponse,
)
from app.application.use_cases import (
    GetAirportByIdUseCase,
    GetAirportsForPlotlyUseCase,
    ListAirportsUseCase,
)
from app.domain.exceptions import ExternalSourceUnavailableError
from app.infrastructure.oauth2 import InvalidClientError, OAuth2ClientCredentialsProvider

router = APIRouter(prefix="/api/v1/airports", tags=["airports"])
oauth_router = APIRouter(tags=["auth"])


@router.get("", response_model=PageOut, summary="Lista aeropuertos colombianos (paginado)")
async def list_airports(
    page: int = 1,
    page_size: int = 20,
    use_case: ListAirportsUseCase = Depends(get_list_airports_use_case),
) -> PageOut:
    try:
        result = await use_case.execute(page, page_size)
    except ExternalSourceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PageOut(
        items=[AirportOut(**vars(a)) for a in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.get("/plotly/points", response_model=list[PlotlyPointOut],
            summary="Aeropuertos en el formato requerido por Plotly")
async def plotly_points(
    limit: int = 200,
    use_case: GetAirportsForPlotlyUseCase = Depends(get_plotly_use_case),
) -> list[PlotlyPointOut]:
    try:
        points = await use_case.execute(limit=limit)
    except ExternalSourceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return [PlotlyPointOut(**p) for p in points]


@router.post("/cache/invalidate", response_model=CacheInvalidationResult,
             summary="Invalida el caché Redis de aeropuertos (requiere JWT)")
async def invalidate_cache(
    repo=Depends(get_repository),
    _claims: dict = Depends(require_valid_token),
) -> CacheInvalidationResult:
    deleted = await repo.invalidate_all()
    return CacheInvalidationResult(deleted_keys=deleted)


@router.get("/{airport_id}", response_model=AirportOut,
            summary="Obtiene un aeropuerto por id (usado también por Itinerary Service como fallback HTTP)")
async def get_airport(
    airport_id: int,
    use_case: GetAirportByIdUseCase = Depends(get_airport_by_id_use_case),
) -> AirportOut:
    try:
        airport = await use_case.execute(airport_id)
    except ExternalSourceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if airport is None:
        raise HTTPException(status_code=404, detail=f"airport {airport_id} not found")
    return AirportOut(**vars(airport))


@oauth_router.post("/oauth/token", response_model=TokenResponse,
                    summary="Emite un token OAuth2 Client Credentials para llamadas S2S")
async def issue_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    provider: OAuth2ClientCredentialsProvider = Depends(get_oauth2_provider),
) -> TokenResponse:
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    try:
        token = provider.issue_token(client_id, client_secret)
    except InvalidClientError as exc:
        raise HTTPException(status_code=401, detail="invalid_client") from exc
    return TokenResponse(**token)
