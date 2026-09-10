"""Proxy transparente hacia los servicios internos. Es infraestructura pura:
no interpreta ni transforma el body de negocio, solo reenvía método, path,
query params, headers (incluyendo Authorization, para "propagar el JWT del
usuario") y agrega/propaga el X-Correlation-Id. La respuesta del servicio
destino (status code, content-type, body) se devuelve tal cual.

Un único handler genérico (`_proxy`) se reutiliza para los tres prefijos
(`/api/v1/airports`, `/api/v1/itineraries`, `/oauth/token`) parametrizado por
la URL base destino, en vez de repetir la lógica de reenvío por cada uno.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response

from app.problem_json import problem_response
from common.correlation import HEADER_NAME as CORRELATION_HEADER
from common.correlation import get_correlation_id

# Headers que no deben reenviarse tal cual (son específicos de la conexión
# punto a punto cliente<->gateway o gateway<->upstream, y httpx los recalcula).
_HOP_BY_HOP_REQUEST_HEADERS = {
    "host",
    "content-length",
    "connection",
    "keep-alive",
    "transfer-encoding",
    "upgrade",
    "te",
    "trailer",
    "proxy-authenticate",
    "proxy-authorization",
}

_HOP_BY_HOP_RESPONSE_HEADERS = {
    "content-encoding",
    "transfer-encoding",
    "connection",
    "content-length",
}

_TIMEOUT_SECONDS = 10.0


def _build_forward_headers(request: Request) -> dict[str, str]:
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP_REQUEST_HEADERS
    }
    # El gateway es el punto de entrada del sistema: siempre garantiza que
    # exista un X-Correlation-Id (lo genera CorrelationIdMiddleware si no
    # vino en la petición original) y lo propaga hacia el servicio interno.
    correlation_id = get_correlation_id()
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id
    return headers


async def _proxy(request: Request, rest: str, target_base_url: str, mount_prefix: str) -> Response:
    forward_path = f"{mount_prefix}{rest}"
    url = f"{target_base_url}{forward_path}"
    headers = _build_forward_headers(request)
    body = await request.body()
    client: httpx.AsyncClient = request.app.state.http_client

    try:
        upstream_response = await client.request(
            request.method,
            url,
            headers=headers,
            params=request.query_params.multi_items(),
            content=body,
            timeout=_TIMEOUT_SECONDS,
        )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException) as exc:
        return problem_response(
            503,
            "Service unavailable",
            f"upstream service unreachable ({target_base_url}): {exc}",
            str(request.url),
        )
    except httpx.HTTPError as exc:  # cualquier otro fallo de transporte inesperado
        return problem_response(
            503,
            "Service unavailable",
            f"upstream request failed ({target_base_url}): {exc}",
            str(request.url),
        )

    response_headers = {
        k: v for k, v in upstream_response.headers.items() if k.lower() not in _HOP_BY_HOP_RESPONSE_HEADERS
    }
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )


def build_proxy_router(mount_prefix: str, target_base_url_getter) -> APIRouter:
    """Crea un router que reenvía TODO lo que llegue bajo `mount_prefix`
    (incluida la ruta exacta, sin sufijo) hacia `target_base_url_getter()`.

    `target_base_url_getter` es un callable (no un string) para poder leer la
    URL destino desde `app.state.settings` en tiempo de request, lo que
    facilita sobre-escribirla en los tests sin recrear la app.
    """
    router = APIRouter()

    @router.api_route(
        mount_prefix + "{rest:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    async def _proxy_endpoint(rest: str, request: Request) -> Response:
        return await _proxy(request, rest, target_base_url_getter(request), mount_prefix)

    return router
