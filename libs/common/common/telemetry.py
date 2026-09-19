"""Configuración estándar de OpenTelemetry (traza distribuida) exportando a
Jaeger vía OTLP/gRPC. Se usa igual en todos los servicios FastAPI para que las
trazas de un mismo request (frontend -> gateway -> itinerary -> airport)
compartan el mismo trace_id."""
from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(app, service_name: str) -> None:
    """Instrumenta una app FastAPI. Si el colector OTLP (Jaeger) no está
    disponible, los spans simplemente se pierden en el exportador sin tumbar
    el servicio (BatchSpanProcessor es asíncrono y tolera fallos de red).

    Los instrumentadores de FastAPI/httpx se importan aquí (no a nivel de
    módulo) porque `common` lo usan también servicios sin FastAPI instalado
    (p.ej. notification-bridge), que solo necesitan `common.logging`."""
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
