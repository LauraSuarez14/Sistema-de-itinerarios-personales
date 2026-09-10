"""Inyección de dependencias de FastAPI: construye la cadena de Adapters
(API Colombia -> caché Redis) una sola vez por proceso y expone los casos de
uso y la verificación de JWT a los routers."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.use_cases import (
    GetAirportByIdUseCase,
    GetAirportsForPlotlyUseCase,
    ListAirportsUseCase,
)
from app.config import Settings
from app.infrastructure.api_colombia_adapter import ApiColombiaAdapter
from app.infrastructure.api_colombia_client import ApiColombiaClient
from app.infrastructure.caching_adapter import CachingAirportAdapter
from app.infrastructure.oauth2 import OAuth2ClientCredentialsProvider
from common.security import JWTError, decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


def build_repository(settings: Settings) -> CachingAirportAdapter:
    base_url = (
        settings.toxiproxy_proxy_url if settings.toxiproxy_enabled else settings.api_colombia_base_url
    )
    client = ApiColombiaClient(base_url=base_url)
    real_adapter = ApiColombiaAdapter(client=client)
    return CachingAirportAdapter(
        inner=real_adapter, redis_url=settings.redis_url, ttl_seconds=settings.cache_ttl_seconds
    )


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_repository(request: Request) -> CachingAirportAdapter:
    return request.app.state.repository


def get_oauth2_provider(request: Request) -> OAuth2ClientCredentialsProvider:
    return request.app.state.oauth2_provider


def get_airport_by_id_use_case(repo=Depends(get_repository)) -> GetAirportByIdUseCase:
    return GetAirportByIdUseCase(repository=repo)


def get_list_airports_use_case(repo=Depends(get_repository)) -> ListAirportsUseCase:
    return ListAirportsUseCase(repository=repo)


def get_plotly_use_case(repo=Depends(get_repository)) -> GetAirportsForPlotlyUseCase:
    return GetAirportsForPlotlyUseCase(repository=repo)


def require_valid_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """Exige un JWT válido (emitido por el API Gateway para usuarios, o por
    este mismo servicio vía /oauth/token para llamadas S2S). Se usa en los
    endpoints administrativos del Airport Service (p. ej. invalidar caché)."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        return decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}") from exc
