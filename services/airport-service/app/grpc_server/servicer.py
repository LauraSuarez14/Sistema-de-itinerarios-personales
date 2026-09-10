"""Implementación del servicio gRPC `airport.v1.AirportService`, definido en
`proto/airport.proto`. Traduce entre el mensaje Protobuf y los casos de uso
de la capa `application/` — es, junto con `api/routes.py`, la otra cara de
la API (REST) del mismo dominio."""
from __future__ import annotations

from app.application.use_cases import GetAirportByIdUseCase, ListAirportsUseCase
from app.domain.entities import Airport
from app.domain.exceptions import ExternalSourceUnavailableError

# Generados en build time por protoc a partir de proto/airport.proto (ver Dockerfile).
from app.grpc_server import airport_pb2, airport_pb2_grpc  # type: ignore
import grpc


def _to_reply(airport: Airport | None) -> "airport_pb2.AirportReply":
    if airport is None:
        return airport_pb2.AirportReply(found=False)
    return airport_pb2.AirportReply(
        id=airport.id,
        name=airport.name,
        iata_code=airport.iata_code,
        city=airport.city,
        latitude=airport.latitude,
        longitude=airport.longitude,
        found=True,
    )


class AirportGrpcServicer(airport_pb2_grpc.AirportServiceServicer):
    def __init__(self, get_by_id_use_case: GetAirportByIdUseCase, list_use_case: ListAirportsUseCase) -> None:
        self._get_by_id_use_case = get_by_id_use_case
        self._list_use_case = list_use_case

    async def GetAirportById(self, request, context):
        try:
            airport = await self._get_by_id_use_case.execute(request.airport_id)
        except ExternalSourceUnavailableError as exc:
            await context.abort(grpc.StatusCode.UNAVAILABLE, str(exc))
            return
        return _to_reply(airport)

    async def ListAirports(self, request, context):
        page = request.page or 1
        page_size = request.page_size or 20
        try:
            result = await self._list_use_case.execute(page, page_size)
        except ExternalSourceUnavailableError as exc:
            await context.abort(grpc.StatusCode.UNAVAILABLE, str(exc))
            return
        return airport_pb2.ListAirportsReply(
            items=[_to_reply(a) for a in result.items],
            page=result.page,
            page_size=result.page_size,
            total=result.total,
        )
