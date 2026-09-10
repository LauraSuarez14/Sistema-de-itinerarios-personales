"""Adapter concreto de `AirportValidationPort`: intenta gRPC primero, y si el
canal falla (excepcion `grpc.RpcError` o timeout) hace fallback a REST. Ambos
transportes se envuelven con `tenacity` (max 3 intentos, backoff exponencial
con jitter, solo en errores de red/timeout -- nunca en "no encontrado", que
es una respuesta valida de negocio, no un fallo transitorio).

Autenticacion S2S: obtiene un token OAuth2 Client Credentials cacheado
(`OAuth2TokenCache`) y lo propaga como metadata gRPC o header HTTP segun el
transporte usado.
"""
from __future__ import annotations

import logging
from typing import Optional

import grpc
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from ...domain.entities import AirportSnapshot
from ...domain.errors import AirportServiceUnavailableError
from ...domain.ports import AirportValidationPort
from .token_cache import OAuth2TokenCache

logger = logging.getLogger(__name__)

_RETRYABLE_HTTP_EXCEPTIONS = (httpx.TransportError, httpx.TimeoutException)


def _is_retryable_grpc_error(exc: BaseException) -> bool:
    if not isinstance(exc, grpc.RpcError):
        return False
    code = exc.code() if hasattr(exc, "code") else None
    # NOT_FOUND es una respuesta de negocio valida, nunca se reintenta.
    return code != grpc.StatusCode.NOT_FOUND


class AirportValidationAdapter(AirportValidationPort):
    def __init__(
        self,
        grpc_target: str,
        http_base_url: str,
        token_cache: OAuth2TokenCache,
        grpc_timeout_seconds: float = 3.0,
        http_timeout_seconds: float = 3.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._grpc_target = grpc_target
        self._http_base_url = http_base_url.rstrip("/")
        self._token_cache = token_cache
        self._grpc_timeout_seconds = grpc_timeout_seconds
        self._http_client = http_client or httpx.Client(timeout=http_timeout_seconds)
        self._grpc_channel: grpc.Channel | None = None
        self._grpc_stub = None

    # -- gRPC -----------------------------------------------------------
    def _get_stub(self):
        if self._grpc_stub is None:
            # Import perezoso: los stubs (`airport_pb2*.py`) se generan en
            # tiempo de build de Docker (ver Dockerfile) y no existen en el
            # repositorio ni en el entorno usado para correr los tests
            # unitarios de domain/application.
            from ..grpc_client import airport_pb2, airport_pb2_grpc

            self._grpc_channel = grpc.insecure_channel(self._grpc_target)
            self._grpc_stub = airport_pb2_grpc.AirportServiceStub(self._grpc_channel)
            self._airport_pb2 = airport_pb2
        return self._grpc_stub

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=0.2, max=2.0),
        retry=retry_if_exception_type(grpc.RpcError),
    )
    def _get_airport_via_grpc(self, airport_id: int) -> Optional[AirportSnapshot]:
        stub = self._get_stub()
        token = self._token_cache.get_token()
        metadata = (("authorization", f"Bearer {token}"),)
        try:
            reply = stub.GetAirportById(
                self._airport_pb2.GetAirportByIdRequest(airport_id=airport_id),
                timeout=self._grpc_timeout_seconds,
                metadata=metadata,
            )
        except grpc.RpcError as exc:
            if not _is_retryable_grpc_error(exc):
                return None  # NOT_FOUND explicito
            raise
        if not reply.found:
            return None
        return AirportSnapshot(id=reply.id, iata_code=reply.iata_code, name=reply.name)

    # -- REST fallback ----------------------------------------------------
    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=0.2, max=2.0),
        retry=retry_if_exception_type(_RETRYABLE_HTTP_EXCEPTIONS),
    )
    def _get_airport_via_http(self, airport_id: int) -> Optional[AirportSnapshot]:
        token = self._token_cache.get_token()
        response = self._http_client.get(
            f"{self._http_base_url}/api/v1/airports/{airport_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        body = response.json()
        return AirportSnapshot(id=body["id"], iata_code=body["iata_code"], name=body["name"])

    # -- Port implementation ----------------------------------------------
    def get_airport(self, airport_id: int) -> Optional[AirportSnapshot]:
        try:
            return self._get_airport_via_grpc(airport_id)
        except Exception as grpc_exc:  # noqa: BLE001 - cualquier fallo de gRPC dispara el fallback
            logger.warning(
                "gRPC call to Airport Service failed (airport_id=%s): %s. Falling back to REST.",
                airport_id,
                grpc_exc,
            )

        try:
            return self._get_airport_via_http(airport_id)
        except Exception as http_exc:  # noqa: BLE001 - agotados ambos transportes
            logger.error(
                "REST fallback to Airport Service also failed (airport_id=%s): %s",
                airport_id,
                http_exc,
            )
            raise AirportServiceUnavailableError(
                f"Airport service unreachable via gRPC and REST for airport_id={airport_id}"
            ) from http_exc
