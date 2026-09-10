"""Test del rate limiting: con un límite bajo configurado, las primeras N
peticiones a una ruta proxyada pasan y la N+1 recibe 429. También verifica
que /health nunca se limita."""
import httpx
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from factories import make_settings


@respx.mock
def test_rate_limit_blocks_requests_beyond_configured_limit():
    settings = make_settings(rate_limit_per_minute=3)
    app = create_app(settings)
    respx.get("http://airport-service:8001/api/v1/airports").mock(
        return_value=httpx.Response(200, json={"items": [], "page": 1, "page_size": 20, "total": 0})
    )

    with TestClient(app) as client:
        statuses = [client.get("/api/v1/airports").status_code for _ in range(3)]
        assert statuses == [200, 200, 200]

        blocked_response = client.get("/api/v1/airports")

    assert blocked_response.status_code == 429
    assert blocked_response.headers["content-type"] == "application/problem+json"
    assert blocked_response.json()["status"] == 429


def test_health_endpoint_is_never_rate_limited():
    settings = make_settings(rate_limit_per_minute=1)
    app = create_app(settings)

    with TestClient(app) as client:
        responses = [client.get("/health").status_code for _ in range(10)]

    assert all(status == 200 for status in responses)
