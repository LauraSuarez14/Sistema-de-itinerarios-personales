"""Inyeccion de dependencias de FastAPI: sesion de DB, autenticacion JWT y
construccion de casos de uso. Es la unica capa que conecta `api/` con
`infrastructure/`, respetando la regla de dependencia hexagonal (domain y
application no conocen FastAPI ni SQLAlchemy)."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from common.security import JWTError, decode_access_token

from ..application.use_cases import (
    CreateItineraryUseCase,
    DeleteItineraryUseCase,
    GetItineraryUseCase,
    ListItinerariesUseCase,
    UpdateItineraryUseCase,
)
from ..config import settings
from ..domain.ports import AirportValidationPort
from ..infrastructure.airport_client.adapter import AirportValidationAdapter
from ..infrastructure.airport_client.token_cache import OAuth2TokenCache
from ..infrastructure.db.repository import SqlAlchemyItineraryRepository
from ..infrastructure.db.session import get_session

_bearer_scheme = HTTPBearer(auto_error=False)

# Singletons de proceso: el token OAuth2 se cachea en memoria y se comparte
# entre requests (evita pedir un token nuevo en cada validacion de
# aeropuerto), y el canal gRPC/cliente HTTP tambien se reutiliza.
_token_cache = OAuth2TokenCache(
    token_url=f"{settings.airport_http_url}/oauth/token",
    client_id=settings.oauth2_client_id,
    client_secret=settings.oauth2_client_secret,
)
_airport_validator: Optional[AirportValidationPort] = None


def get_airport_validator() -> AirportValidationPort:
    global _airport_validator
    if _airport_validator is None:
        _airport_validator = AirportValidationAdapter(
            grpc_target=settings.airport_grpc_url,
            http_base_url=settings.airport_http_url,
            token_cache=_token_cache,
        )
    return _airport_validator


def get_current_subject(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer_scheme)]
) -> str:
    """Dependencia de autenticacion: exige un JWT valido (`sub` presente),
    sin validar roles (fuera del alcance pedido). Falta o invalidez ->
    HTTPException 401, que `problem_json.py` traduce a application/problem+json."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        claims = decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    subject = claims.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing 'sub' claim")
    return subject


def get_itinerary_repository(
    session: Annotated[Session, Depends(get_session)]
) -> SqlAlchemyItineraryRepository:
    return SqlAlchemyItineraryRepository(session)


def get_create_use_case(
    repository: Annotated[SqlAlchemyItineraryRepository, Depends(get_itinerary_repository)],
    validator: Annotated[AirportValidationPort, Depends(get_airport_validator)],
) -> CreateItineraryUseCase:
    return CreateItineraryUseCase(repository, validator)


def get_get_use_case(
    repository: Annotated[SqlAlchemyItineraryRepository, Depends(get_itinerary_repository)]
) -> GetItineraryUseCase:
    return GetItineraryUseCase(repository)


def get_list_use_case(
    repository: Annotated[SqlAlchemyItineraryRepository, Depends(get_itinerary_repository)]
) -> ListItinerariesUseCase:
    return ListItinerariesUseCase(repository)


def get_update_use_case(
    repository: Annotated[SqlAlchemyItineraryRepository, Depends(get_itinerary_repository)],
    validator: Annotated[AirportValidationPort, Depends(get_airport_validator)],
) -> UpdateItineraryUseCase:
    return UpdateItineraryUseCase(repository, validator)


def get_delete_use_case(
    repository: Annotated[SqlAlchemyItineraryRepository, Depends(get_itinerary_repository)]
) -> DeleteItineraryUseCase:
    return DeleteItineraryUseCase(repository)
