"""Servidor HTTP minimo (stdlib `http.server`) para `/health` y `/metrics`.

`notification-bridge` no es una API -- es un puente de mensajeria que pasa
la mayor parte del tiempo bloqueado en `channel.start_consuming()` -- pero
Prometheus necesita un endpoint HTTP para hacer scraping y Docker/K8s
necesitan un endpoint de liveness, por eso se expone este servidor aparte,
en un hilo daemon independiente del hilo de consumo de RabbitMQ.
"""
from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .metrics import render_latest

logger = logging.getLogger(__name__)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - firma de BaseHTTPRequestHandler
        # Silencia el logging por defecto de http.server (texto plano); los
        # logs del proceso ya son JSON estructurado via `common.logging`.
        pass

    def do_GET(self) -> None:  # noqa: N802 - nombre exigido por BaseHTTPRequestHandler
        if self.path == "/health":
            body = b'{"status": "ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/metrics":
            body, content_type = render_latest()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def start_health_server(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, name="health-metrics-server", daemon=True)
    thread.start()
    logger.info("Health/metrics server listening on 0.0.0.0:%s", port)
    return server
