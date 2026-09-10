"""Endpoint de salud sin autenticacion, para probes de k8s / healthcheck de
docker-compose. Verifica la DB con un `SELECT 1` real."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ...infrastructure.db.session import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    if not check_database_connection():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not reachable")
    return {"status": "ok"}
