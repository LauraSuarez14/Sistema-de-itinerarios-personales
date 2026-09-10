"""Arranque del servidor gRPC (asyncio), corrido en paralelo al servidor
HTTP/uvicorn dentro del mismo proceso (ver `app/main.py`)."""
from __future__ import annotations

import grpc

from app.application.use_cases import GetAirportByIdUseCase, ListAirportsUseCase
from app.grpc_server import airport_pb2_grpc  # type: ignore
from app.grpc_server.auth_interceptor import JwtAuthInterceptor
from app.grpc_server.servicer import AirportGrpcServicer
from app.infrastructure.caching_adapter import CachingAirportAdapter


async def create_grpc_server(repository: CachingAirportAdapter, port: int) -> grpc.aio.Server:
    server = grpc.aio.server(interceptors=[JwtAuthInterceptor()])
    servicer = AirportGrpcServicer(
        get_by_id_use_case=GetAirportByIdUseCase(repository=repository),
        list_use_case=ListAirportsUseCase(repository=repository),
    )
    airport_pb2_grpc.add_AirportServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    return server
