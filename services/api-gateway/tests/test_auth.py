"""Tests de /auth/login: éxito y fallo del mock de autenticación demo."""
from fastapi.testclient import TestClient

from app.main import create_app
from factories import make_settings


def test_login_success_returns_jwt():
    app = create_app(make_settings())
    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"username": "viajero", "password": "viajero123"}
        )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 10


def test_login_wrong_password_returns_401_problem_json():
    app = create_app(make_settings())
    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"username": "viajero", "password": "incorrecta"}
        )
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == 401
    assert "detail" in body


def test_login_unknown_user_returns_401():
    app = create_app(make_settings())
    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"username": "otro", "password": "viajero123"}
        )
    assert response.status_code == 401
