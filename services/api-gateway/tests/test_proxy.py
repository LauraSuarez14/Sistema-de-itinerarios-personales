"""Tests del proxy transparente: propagación del header Authorization hacia
el servicio interno, y respuesta 503 application/problem+json cuando el
servicio destino no responde. Los servicios internos se mockean con `respx`
(intercepta a nivel de transporte httpx), sin necesidad de Docker."""
import httpx
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from factories import make_settings


@respx.mock
def test_proxy_forwards_authorization_header_to_airport_service():
    app = create_app(make_settings())
    route = respx.get("http://airport-service:8001/api/v1/airports").mock(
        return_value=httpx.Response(
            200, json={"items": [], "page": 1, "page_size": 20, "total": 0}
        )
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/airports", headers={"Authorization": "Bearer test-token-123"}
        )

    assert response.status_code == 200
    assert route.called
    forwarded_request = route.calls.last.request
    assert forwarded_request.headers["authorization"] == "Bearer test-token-123"


@respx.mock
def test_proxy_forwards_authorization_header_to_itinerary_service():
    app = create_app(make_settings())
    route = respx.get("http://itinerary-service:8002/api/v1/itineraries").mock(
        return_value=httpx.Response(200, json={"items": [], "page": 1, "page_size": 20, "total": 0})
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/itineraries", headers={"Authorization": "Bearer another-token"}
        )

    assert response.status_code == 200
    forwarded_request = route.calls.last.request
    assert forwarded_request.headers["authorization"] == "Bearer another-token"


@respx.mock
def test_proxy_forwards_query_params_and_path_suffix():
    app = create_app(make_settings())
    route = respx.get(
        "http://airport-service:8001/api/v1/airports/plotly/points"
    ).mock(return_value=httpx.Response(200, json=[{"id": 1, "lat": 4.6, "lon": -74.0, "label": "BOG"}]))

    with TestClient(app) as client:
        response = client.get("/api/v1/airports/plotly/points", params={"limit": "5"})

    assert response.status_code == 200
    assert response.json() == [{"id": 1, "lat": 4.6, "lon": -74.0, "label": "BOG"}]
    assert route.called
    assert route.calls.last.request.url.params["limit"] == "5"


@respx.mock
def test_proxy_returns_503_problem_json_when_upstream_unreachable():
    app = create_app(make_settings())
    respx.get("http://airport-service:8001/api/v1/airports").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/airports")

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == 503
    assert "detail" in body


@respx.mock
def test_proxy_returns_upstream_error_body_unchanged():
    """El gateway no reinterpreta errores 4xx del servicio destino, los
    devuelve tal cual (p. ej. un 404 de aeropuerto inexistente)."""
    app = create_app(make_settings())
    respx.get("http://airport-service:8001/api/v1/airports/999").mock(
        return_value=httpx.Response(
            404,
            json={"type": "about:blank", "title": "Not Found", "status": 404,
                  "detail": "airport 999 not found", "instance": "/api/v1/airports/999"},
            headers={"content-type": "application/problem+json"},
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/airports/999")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "airport 999 not found"
