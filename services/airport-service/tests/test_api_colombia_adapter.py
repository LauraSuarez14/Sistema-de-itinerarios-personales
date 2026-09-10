"""Verifica que el Adapter traduzca correctamente la forma cruda de la API
Colombia al modelo de dominio, incluyendo el intercambio de latitude/
longitude confirmado contra la API real (ver docstring del módulo adapter)."""
from app.infrastructure.api_colombia_adapter import _to_domain

RAW_BARRANQUILLA = {
    "id": 2,
    "name": "Aeropuerto Internacional Ernesto Cortissoz",
    "iataCode": "BAQ",
    "oaciCode": "SKBQ",
    "type": "Internacional",
    "city": {"id": 890, "name": "Barranquilla"},
    "latitude": -74.7806769994191,
    "longitude": 10.8894609990694,
}


def test_to_domain_swaps_lat_lon_quirk_from_external_api():
    airport = _to_domain(RAW_BARRANQUILLA)

    assert airport.id == 2
    assert airport.iata_code == "BAQ"
    assert airport.city == "Barranquilla"
    # Barranquilla está en ~10.88°N, -74.78°O: la API externa entrega estos
    # valores en los campos opuestos, y el Adapter debe corregirlo.
    assert airport.latitude == 10.8894609990694
    assert airport.longitude == -74.7806769994191


def test_to_domain_handles_missing_optional_fields():
    airport = _to_domain({"id": 1, "latitude": 0, "longitude": 0})
    assert airport.name == ""
    assert airport.iata_code == "N/A"
    assert airport.city == ""
