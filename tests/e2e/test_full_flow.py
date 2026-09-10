"""Suite E2E (Nivel 2, "Pruebas E2E con Testcontainers"): levanta el sistema
COMPLETO vía `docker-compose.yml` con `testcontainers.compose.DockerCompose`,
ejercita el flujo real de punta a punta, y destruye todo al finalizar
(fixture de módulo con `yield`, sin importar si el test falla).

Flujo verificado:
1. Login contra el API Gateway (`/auth/login`) obtiene un JWT.
2. Se consulta el mapa de aeropuertos (`/api/v1/airports/plotly/points`).
3. Se crea un itinerario válido (`POST /api/v1/itineraries`) con dos
   aeropuertos reales.
4. Se verifica que el itinerario quede persistido (`GET .../{id}`).
5. Se espera a que `notification-bridge` procese el evento y a que
   `SendNotificationFunction` (LocalStack) registre el historial — se
   comprueba indirectamente vía las métricas Prometheus del bridge
   (`notification_bridge_messages_processed_total` > 0).
6. Caso negativo: crear un itinerario con un aeropuerto inexistente debe
   responder 422 `application/problem+json`.

No se ejecutó en el entorno donde se generó este proyecto (no hay Docker
instalado en la máquina usada para escribir el código — ver README raíz,
sección de limitaciones). Queda completa y lista para correr en cuanto el
proyecto se despliegue con Docker.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

import pytest
import requests
from testcontainers.compose import DockerCompose

PROJECT_ROOT = "../.."  # relativo a este archivo, apunta a la raíz del repo
GATEWAY_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def running_system():
    with DockerCompose(
        PROJECT_ROOT,
        compose_file_name="docker-compose.yml",
        pull=True,
        build=True,
    ) as compose:
        _wait_for_healthy(f"{GATEWAY_URL}/health", timeout=180)
        yield compose


def _wait_for_healthy(url: str, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                return
        except requests.RequestException as exc:  # noqa: PERF203
            last_error = exc
        time.sleep(2)
    raise TimeoutError(f"{url} no respondió sano en {timeout}s (último error: {last_error})")


@pytest.fixture(scope="module")
def auth_token(running_system) -> str:
    response = requests.post(
        f"{GATEWAY_URL}/auth/login",
        json={"username": "viajero", "password": "viajero123"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_plotly_points_available(running_system):
    response = requests.get(f"{GATEWAY_URL}/api/v1/airports/plotly/points", timeout=10)
    assert response.status_code == 200
    points = response.json()
    assert len(points) > 0
    assert {"id", "lat", "lon", "label"} <= points[0].keys()


def test_create_itinerary_end_to_end(running_system, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}

    airports = requests.get(f"{GATEWAY_URL}/api/v1/airports?page=1&page_size=2", timeout=10).json()
    origin, destination = airports["items"][0]["id"], airports["items"][1]["id"]

    payload = {
        "user_name": "Viajero E2E",
        "origin_airport_id": origin,
        "destination_airport_id": destination,
        "travel_date": str(date.today() + timedelta(days=30)),
        "duration_minutes": 90,
    }
    create_response = requests.post(
        f"{GATEWAY_URL}/api/v1/itineraries", json=payload, headers=headers, timeout=10
    )
    assert create_response.status_code == 201, create_response.text
    itinerary = create_response.json()

    get_response = requests.get(
        f"{GATEWAY_URL}/api/v1/itineraries/{itinerary['id']}", headers=headers, timeout=10
    )
    assert get_response.status_code == 200
    assert get_response.json()["user_name"] == "Viajero E2E"

    # Da tiempo al OutboxRelay + notification-bridge + Lambda para procesar.
    deadline = time.monotonic() + 30
    processed = 0.0
    while time.monotonic() < deadline:
        metrics = requests.get("http://localhost:8090/metrics", timeout=5).text
        for line in metrics.splitlines():
            if line.startswith("notification_bridge_messages_processed_total"):
                processed = float(line.rsplit(" ", 1)[-1])
        if processed > 0:
            break
        time.sleep(2)

    assert processed > 0, "notification-bridge no procesó ningún evento a tiempo"


def test_create_itinerary_with_nonexistent_airport_fails(running_system, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {
        "user_name": "Viajero E2E",
        "origin_airport_id": 999999,
        "destination_airport_id": 999998,
        "travel_date": str(date.today() + timedelta(days=30)),
        "duration_minutes": 90,
    }
    response = requests.post(
        f"{GATEWAY_URL}/api/v1/itineraries", json=payload, headers=headers, timeout=10
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
