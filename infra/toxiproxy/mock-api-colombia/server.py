"""Stub mínimo (sin dependencias, solo librería estándar) que imita la forma
real de `GET /api/v1/Airport` y `GET /api/v1/Airport/{id}` de API Colombia
(verificada contra la API real, incluido el intercambio de latitude/
longitude que ya absorbe el Adapter). Se usa EXCLUSIVAMENTE para las
demostraciones de Chaos Engineering (`TOXIPROXY_ENABLED=true`): en vez de
inyectar fallos de red contra la API pública real de un tercero (poco
reproducible y potencialmente abusivo), Toxiproxy pone sus "toxics"
(latencia, cortes de conexión) delante de este stub local, 100% controlado.

En operación normal (`TOXIPROXY_ENABLED=false`, el valor por defecto),
Airport Service llama directamente a la API Colombia real y este contenedor
ni siquiera recibe tráfico."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AIRPORTS = [
    {
        "id": 1,
        "name": "Aeropuerto Internacional El Dorado",
        "iataCode": "BOG",
        "oaciCode": "SKBO",
        "type": "Internacional",
        "city": {"id": 1, "name": "Bogotá"},
        # Mismo intercambio lat/lon que la API real (el Adapter lo corrige).
        "latitude": -74.1469,
        "longitude": 4.70159,
    },
    {
        "id": 2,
        "name": "Aeropuerto Internacional Ernesto Cortissoz",
        "iataCode": "BAQ",
        "oaciCode": "SKBQ",
        "type": "Internacional",
        "city": {"id": 2, "name": "Barranquilla"},
        "latitude": -74.7806769994191,
        "longitude": 10.8894609990694,
    },
]


class Handler(BaseHTTPRequestHandler):
    def _write_json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - nombre exigido por BaseHTTPRequestHandler
        if self.path.rstrip("/") == "/Airport":
            self._write_json(200, AIRPORTS)
            return

        if self.path.startswith("/Airport/"):
            try:
                airport_id = int(self.path.rsplit("/", 1)[-1])
            except ValueError:
                self._write_json(400, {"detail": "invalid id"})
                return
            match = next((a for a in AIRPORTS if a["id"] == airport_id), None)
            if match is None:
                self._write_json(404, {"detail": "not found"})
                return
            self._write_json(200, match)
            return

        self._write_json(404, {"detail": "unknown route"})

    def log_message(self, format: str, *args) -> None:  # silencia logs de acceso ruidosos
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 80), Handler)
    server.serve_forever()
