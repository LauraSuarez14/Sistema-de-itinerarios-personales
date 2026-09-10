"""Cliente OAuth2 Client Credentials hacia Airport Service, con cacheo del
token en memoria (thread-safe) hasta que expira."""
from __future__ import annotations

import threading
import time

import httpx


class OAuth2TokenCache:
    def __init__(self, token_url: str, client_id: str, client_secret: str, http_client: httpx.Client | None = None) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._http_client = http_client or httpx.Client(timeout=5.0)
        self._lock = threading.Lock()
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        with self._lock:
            # Renueva 30s antes de expirar para evitar condiciones de carrera
            # con requests concurrentes que usan un token a punto de expirar.
            if self._access_token and time.monotonic() < self._expires_at - 30:
                return self._access_token

            response = self._http_client.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            response.raise_for_status()
            body = response.json()
            self._access_token = body["access_token"]
            expires_in = body.get("expires_in", 3600)
            self._expires_at = time.monotonic() + expires_in
            return self._access_token

    def invalidate(self) -> None:
        with self._lock:
            self._access_token = None
            self._expires_at = 0.0
