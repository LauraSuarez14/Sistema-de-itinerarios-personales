"""Adapter concreto de `MetricsPort` usando `prometheus_client` (via
`prometheus_fastapi_instrumentator`, que ya registra las metricas HTTP
estandar). Este modulo agrega las metricas de negocio especificas del
Outbox pedidas por el reto: `outbox_pending_events` (Gauge) y
`outbox_events_published_total` (Counter)."""
from __future__ import annotations

from prometheus_client import Counter, Gauge

from ..domain.ports import MetricsPort

outbox_pending_events = Gauge(
    "outbox_pending_events",
    "Cantidad de filas de outbox_events pendientes de publicar en el ultimo ciclo del relay",
)
outbox_events_published_total = Counter(
    "outbox_events_published_total",
    "Cantidad total de eventos de outbox publicados exitosamente en RabbitMQ",
)


class PrometheusMetrics(MetricsPort):
    def set_outbox_pending(self, count: int) -> None:
        outbox_pending_events.set(count)

    def inc_outbox_published(self, amount: int = 1) -> None:
        outbox_events_published_total.inc(amount)
