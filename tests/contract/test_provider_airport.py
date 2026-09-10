"""Contract test (lado proveedor): verifica que el Airport Service REAL
(corriendo, p. ej. vía `docker compose up airport-service redis`) cumple el
pacto generado por `test_consumer_itinerary.py`. Requiere que el pacto ya
exista en `tests/contract/pacts/` y que Airport Service esté escuchando en
`http://localhost:8001`.

No se ejecutó en el entorno donde se generó este proyecto (requiere Docker
para levantar Airport Service real, no disponible aquí) — queda como
verificación pendiente para cuando el proyecto se despliegue con Docker.

Nota sobre "provider states": Airport Service no expone un endpoint de
`provider_states_setup_url` (no tiene sentido "preparar" el estado de un
aeropuerto real de API Colombia como se haría con una BD propia). El
"given(...)" del pacto usa a propósito un aeropuerto real y estable
(id=1, El Edén/Armenia) que siempre existe en la fuente externa, así que la
verificación puede correr igualmente pasando `provider_states_setup_url=None`
si el endpoint de setup no está implementado — ajusta esa línea si agregas
el endpoint más adelante.
"""
from __future__ import annotations

from pact import Verifier

PROVIDER_BASE_URL = "http://localhost:8001"
PACT_FILE = "./tests/contract/pacts/itinerary-service-airport-service.json"


def test_airport_service_honors_itinerary_service_pact():
    verifier = Verifier(provider="airport-service", provider_base_url=PROVIDER_BASE_URL)

    success, _ = verifier.verify_pacts(
        PACT_FILE,
        provider_states_setup_url=f"{PROVIDER_BASE_URL}/_pact/provider_states",
    )

    assert success == 0
