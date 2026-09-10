"""GenerateItineraryReportFunction -- Lambda invocada BAJO DEMANDA (no
reacciona a eventos, a diferencia de SendNotificationFunction).

Sin dependencias externas a proposito (solo libreria estandar: `urllib`
para el HTTP GET), para mantener el paquete de despliegue trivial. Consulta
Itinerary Service para consolidar metricas simples sin sobrecargar los
servicios principales con esa logica de agregacion.

Autenticacion
-------------
`GET /api/v1/itineraries` en Itinerary Service exige un JWT
(`Authorization: Bearer <token>`), pero esta funcion corre bajo demanda, sin
un usuario interactivo detras que pueda iniciar sesion. Para este proyecto
academico se resuelve con un token de servicio pre-generado,
`INTERNAL_SERVICE_TOKEN` (variable de entorno inyectada por infraestructura,
ver `infra/localstack/init/01_create_functions.sh`). Si no hay token
configurado (caso tipico si nadie genero uno manualmente todavia), la
funcion NO revienta: devuelve un reporte con un mensaje claro indicando que
la autenticacion quedo pendiente de configurar, en vez de una excepcion no
controlada -- se documenta aqui como una simplificacion consciente del
alcance: en un escenario productivo real, esta funcion usaria credenciales
de maquina-a-maquina (client credentials OAuth2, igual que
Itinerary Service usa contra Airport Service) en vez de un JWT estatico.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime

DEFAULT_ITINERARY_SERVICE_HTTP_URL = "http://itinerary-service:8002"
ITINERARIES_PATH = "/api/v1/itineraries?page=1&page_size=200"
REQUEST_TIMEOUT_SECONDS = 10


def _fetch_itineraries(base_url: str, token: str | None) -> list[dict]:
    url = base_url.rstrip("/") + ITINERARIES_PATH
    request = urllib.request.Request(url, method="GET")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))

    # Se acepta tanto una lista directa como un envoltorio paginado
    # ({"items": [...]} / {"results": [...]}) para no acoplar el reporte a
    # un detalle de formato de paginacion que no forma parte del contrato
    # documentado explicitamente aqui.
    if isinstance(body, list):
        return body
    for key in ("items", "results", "data"):
        if isinstance(body, dict) and isinstance(body.get(key), list):
            return body[key]
    return []


def _consolidate(itineraries: list[dict]) -> dict:
    total = len(itineraries)
    if total == 0:
        return {
            "total_itineraries": 0,
            "average_duration_minutes": 0,
            "itineraries_by_month": {},
            "top_routes": [],
        }

    durations = []
    month_counter: Counter[str] = Counter()
    route_counter: Counter[str] = Counter()

    for itinerary in itineraries:
        duration = itinerary.get("duration_minutes")
        if isinstance(duration, (int, float)):
            durations.append(duration)

        travel_date = itinerary.get("travel_date")
        if travel_date:
            try:
                month_key = datetime.fromisoformat(str(travel_date)).strftime("%Y-%m")
            except ValueError:
                month_key = "unknown"
            month_counter[month_key] += 1

        origin = (itinerary.get("origin_airport") or {}).get("iata_code", "???")
        destination = (itinerary.get("destination_airport") or {}).get("iata_code", "???")
        route_counter[f"{origin}-{destination}"] += 1

    average_duration = round(sum(durations) / len(durations), 2) if durations else 0

    return {
        "total_itineraries": total,
        "average_duration_minutes": average_duration,
        "itineraries_by_month": dict(sorted(month_counter.items())),
        "top_routes": [
            {"route": route, "count": count}
            for route, count in route_counter.most_common(5)
        ],
    }


def lambda_handler(event: dict, context) -> dict:
    base_url = os.environ.get("ITINERARY_SERVICE_HTTP_URL", DEFAULT_ITINERARY_SERVICE_HTTP_URL)
    token = os.environ.get("INTERNAL_SERVICE_TOKEN") or None

    if not token:
        message = (
            "INTERNAL_SERVICE_TOKEN no esta configurado: no es posible "
            "autenticar contra Itinerary Service (requiere JWT). Configura "
            "esta variable de entorno de la funcion con un token valido "
            "(ver infra/localstack/init/01_create_functions.sh) para "
            "generar el reporte real. Esto queda como configuracion "
            "pendiente/opcional para el alcance de este proyecto academico."
        )
        print(json.dumps({"message": message}))
        return {
            "status": "skipped",
            "reason": "missing_internal_service_token",
            "report": None,
            "message": message,
        }

    try:
        itineraries = _fetch_itineraries(base_url, token)
    except urllib.error.HTTPError as exc:
        message = f"Itinerary Service respondio HTTP {exc.code}: {exc.reason}"
        print(json.dumps({"message": message}))
        return {"status": "error", "reason": message, "report": None}
    except urllib.error.URLError as exc:
        message = f"No se pudo contactar a Itinerary Service ({base_url}): {exc.reason}"
        print(json.dumps({"message": message}))
        return {"status": "error", "reason": message, "report": None}

    report = _consolidate(itineraries)
    print(json.dumps({"message": "reporte generado", "report": report}))
    return {"status": "ok", "report": report}
