"""Interceptor gRPC que exige un token OAuth2 Client Credentials válido
(mismo JWT compartido que emite /oauth/token) en la metadata `authorization`.
Es la aplicación concreta de "Seguridad S2S" (Nivel 3) sobre el canal
gRPC interno Itinerary -> Airport."""
from __future__ import annotations

import grpc

from common.logging import get_logger
from common.security import JWTError, decode_access_token

logger = get_logger(__name__)


class JwtAuthInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata or [])
        auth_header = metadata.get("authorization", "")

        if not auth_header.lower().startswith("bearer "):
            return _unauthenticated_handler("missing bearer token in gRPC metadata")

        token = auth_header.split(" ", 1)[1]
        try:
            decode_access_token(token)
        except JWTError as exc:
            logger.warning("rejected grpc call: invalid token", extra={"error": str(exc)})
            return _unauthenticated_handler(f"invalid token: {exc}")

        return await continuation(handler_call_details)


def _unauthenticated_handler(message: str):
    async def unary_unary(request, context):
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, message)

    return grpc.unary_unary_rpc_method_handler(unary_unary)
