"""Esquemas Pydantic de la API REST del Airport Service. Son la única forma
que el mundo exterior (frontend, gateway, otros servicios) ve del dominio
-- nunca se serializa directamente la entidad `Airport` del dominio."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AirportOut(BaseModel):
    id: int
    name: str
    iata_code: str
    city: str
    latitude: float
    longitude: float


class PageOut(BaseModel):
    items: list[AirportOut]
    page: int
    page_size: int
    total: int


class PlotlyPointOut(BaseModel):
    id: int
    lat: float
    lon: float
    label: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ProblemDetail(BaseModel):
    """RFC 7807 — formato consistente de error usado en todo el sistema."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None


class CacheInvalidationResult(BaseModel):
    deleted_keys: int = Field(description="Cantidad de claves de caché eliminadas")
