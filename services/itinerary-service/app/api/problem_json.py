"""Exception handlers globales de FastAPI que traducen errores de dominio (y
errores genericos de HTTP/validacion) a respuestas RFC 7807
(application/problem+json), como exige el requisito de "manejo adecuado de
errores HTTP" del proyecto."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..domain.errors import (
    AirportNotFoundError,
    AirportServiceUnavailableError,
    InvalidItineraryDataError,
    ItineraryNotFoundError,
)

logger = logging.getLogger(__name__)

PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"


def _problem_response(request: Request, status_code: int, title: str, detail: str, type_: str = "about:blank", **extra) -> JSONResponse:
    body = {
        "type": type_,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": str(request.url.path),
    }
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body, media_type=PROBLEM_JSON_MEDIA_TYPE)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AirportNotFoundError)
    async def airport_not_found_handler(request: Request, exc: AirportNotFoundError) -> JSONResponse:
        return _problem_response(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Airport not found",
            detail=f"Airport with id={exc.airport_id} does not exist",
            type_="https://itinerarios-app/problems/airport-not-found",
            airport_id=exc.airport_id,
        )

    @app.exception_handler(AirportServiceUnavailableError)
    async def airport_unavailable_handler(request: Request, exc: AirportServiceUnavailableError) -> JSONResponse:
        return _problem_response(
            request,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            title="Airport service unavailable",
            detail=str(exc) or "Airport service could not be reached",
            type_="https://itinerarios-app/problems/airport-service-unavailable",
        )

    @app.exception_handler(ItineraryNotFoundError)
    async def itinerary_not_found_handler(request: Request, exc: ItineraryNotFoundError) -> JSONResponse:
        return _problem_response(
            request,
            status.HTTP_404_NOT_FOUND,
            title="Itinerary not found",
            detail=f"Itinerary with id={exc.itinerary_id} does not exist",
            type_="https://itinerarios-app/problems/itinerary-not-found",
        )

    @app.exception_handler(InvalidItineraryDataError)
    async def invalid_itinerary_data_handler(request: Request, exc: InvalidItineraryDataError) -> JSONResponse:
        return _problem_response(
            request,
            status.HTTP_400_BAD_REQUEST,
            title="Invalid itinerary data",
            detail=str(exc),
            type_="https://itinerarios-app/problems/invalid-itinerary-data",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem_response(
            request,
            status.HTTP_400_BAD_REQUEST,
            title="Request validation failed",
            detail=str(exc.errors()),
            type_="https://itinerarios-app/problems/validation-error",
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return _problem_response(
            request,
            exc.status_code,
            title=exc.detail if isinstance(exc.detail, str) else "HTTP error",
            detail=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            type_="about:blank",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
        return _problem_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal server error",
            detail="An unexpected error occurred",
            type_="https://itinerarios-app/problems/internal-error",
        )
