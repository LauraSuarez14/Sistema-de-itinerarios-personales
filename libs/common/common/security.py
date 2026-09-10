"""Emisión/verificación de JWT compartida por el API Gateway (emisor) y los
servicios internos (verificadores) para propagar la identidad del usuario, y
también usada para los tokens de servicio (OAuth2 Client Credentials) entre
Itinerary Service y Airport Service."""
from __future__ import annotations

import os
import time
from typing import Any

from jose import JWTError as _JoseJWTError
from jose import jwt

JWTError = _JoseJWTError

ALGORITHM = "HS256"
DEFAULT_TTL_SECONDS = 3600


def _secret_key() -> str:
    return os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")


def create_access_token(subject: str, claims: dict[str, Any] | None = None,
                         ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
