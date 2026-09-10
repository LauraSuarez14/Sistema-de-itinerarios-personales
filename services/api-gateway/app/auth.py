"""Endpoint de autenticación del gateway.

NOTA (mock de autenticación, alcance académico): no existe una base de datos
de usuarios ni un flujo de registro. `/auth/login` compara las credenciales
recibidas contra un único usuario "demo" configurado por variables de entorno
(`DEMO_USER` / `DEMO_PASSWORD`, ya definidas en `.env.example`). Si coinciden,
se emite un JWT real (HS256, mismo secreto `JWT_SECRET_KEY` que verifican los
demás servicios) usando `common.security.create_access_token`, para poder
demostrar el flujo completo de propagación de identidad (frontend -> gateway
emisor -> servicios internos verificadores) sin necesitar un sistema de
usuarios completo, que está fuera del alcance de este reto.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.problem_json import problem_response
from common.security import create_access_token

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Autenticación demo: emite un JWT si las credenciales coinciden con DEMO_USER/DEMO_PASSWORD",
    responses={401: {"description": "Credenciales inválidas (application/problem+json)"}},
)
async def login(payload: LoginRequest, request: Request):
    settings = request.app.state.settings
    if payload.username != settings.demo_user or payload.password != settings.demo_password:
        return problem_response(
            401,
            "Unauthorized",
            "invalid username or password",
            str(request.url),
        )
    token = create_access_token(subject=payload.username)
    return LoginResponse(access_token=token)
