"""Contract test (lado consumidor): Itinerary Service consume
`GET /api/v1/airports/{id}` de Airport Service como fallback REST de la
validación de aeropuertos (ver `AirportValidationAdapter` en
`services/itinerary-service/app/infrastructure/airport_client/`). Genera el
archivo de pacto en `tests/contract/pacts/itinerary-service-airport-service.json`,
que luego se usa para verificar al proveedor real en
`test_provider_airport.py`.

Requiere `pip install -r requirements.txt` (descarga los binarios standalone
de Pact la primera vez). No se ejecutó en el entorno donde se generó este
proyecto (sin conexión estable para descargar los binarios de Pact ni
Docker para levantar Airport Service real) — queda documentado como
pendiente de ejecución por quien continúe el proyecto con Docker instalado.
"""
from __future__ import annotations

import atexit

import requests
from pact import Consumer, Like, Provider

PACT_DIR = "./tests/contract/pacts"

pact = Consumer("itinerary-service").has_pact_with(
    Provider("airport-service"), pact_dir=PACT_DIR, port=1234
)
pact.start_service()
atexit.register(pact.stop_service)

# Aeropuerto real y estable de API Colombia (verificado contra
# https://api-colombia.com/api/v1/Airport/1 al construir este proyecto), ya
# con latitude/longitude corregidos por el Adapter (ver ADR y
# api_colombia_adapter.py) — se usa un aeropuerto real, no inventado, para
# que el pacto siga siendo válido contra el proveedor real sin necesitar un
# endpoint de "provider states" que reconfigure datos externos.
EXPECTED_AIRPORT = {
    "id": 1,
    "name": "Aeropuerto Internacional El Edén",
    "iata_code": "AXM",
    "city": "Armenia",
    "latitude": 4.4532428642135,
    "longitude": -75.7659806671205,
}


def test_get_existing_airport_by_id():
    (
        pact.given("el aeropuerto 1 (El Edén, Armenia) existe en API Colombia")
        .upon_receiving("una solicitud del aeropuerto 1")
        .with_request("GET", "/api/v1/airports/1")
        .will_respond_with(200, body=EXPECTED_AIRPORT)
    )

    with pact:
        response = requests.get(f"{pact.uri}/api/v1/airports/1", timeout=5)

    assert response.status_code == 200
    assert response.json() == EXPECTED_AIRPORT


def test_get_missing_airport_returns_404_problem_json():
    (
        pact.given("el aeropuerto 999999 no existe")
        .upon_receiving("una solicitud de un aeropuerto inexistente")
        .with_request("GET", "/api/v1/airports/999999")
        .will_respond_with(
            404,
            body={
                "type": "about:blank",
                "title": "airport 999999 not found",
                "status": 404,
                "detail": "airport 999999 not found",
                # La URL exacta (host/puerto) varía según dónde corra el
                # servidor; solo importa que el campo exista y sea string.
                "instance": Like("http://airport-service:8001/api/v1/airports/999999"),
            },
        )
    )

    with pact:
        response = requests.get(f"{pact.uri}/api/v1/airports/999999", timeout=5)

    assert response.status_code == 404
