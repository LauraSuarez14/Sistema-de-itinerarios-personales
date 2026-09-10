"""Proveedor OAuth2 Client Credentials para autenticación servicio-a-servicio
(S2S) entre Itinerary Service y Airport Service — la alternativa a mTLS con
Service Mesh que permite el enunciado para el bonus de seguridad S2S de
Nivel 3, mucho más simple de operar sin un cluster de Kubernetes real.

Es un registro de clientes en memoria (suficiente para el alcance
académico); en un entorno productivo esto viviría en una tabla o en un
proveedor de identidad dedicado (Keycloak, Auth0, etc.)."""
from __future__ import annotations

from common.security import create_access_token


class InvalidClientError(Exception):
    pass


class OAuth2ClientCredentialsProvider:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def issue_token(self, client_id: str, client_secret: str) -> dict:
        if client_id != self._client_id or client_secret != self._client_secret:
            raise InvalidClientError("invalid client_id or client_secret")

        ttl_seconds = 3600
        token = create_access_token(
            subject=client_id,
            claims={"scope": "s2s", "token_type_hint": "service"},
            ttl_seconds=ttl_seconds,
        )
        return {"access_token": token, "token_type": "bearer", "expires_in": ttl_seconds}
