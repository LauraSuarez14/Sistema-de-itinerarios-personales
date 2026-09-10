"""Logging estructurado en JSON con trace_id/span_id (OpenTelemetry) y
correlation_id (de negocio) en cada línea, tal como exige el requisito de
observabilidad del reto."""
from __future__ import annotations

import logging
import sys

from opentelemetry import trace
from pythonjsonlogger import jsonlogger

from .correlation import get_correlation_id


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context()
        record.trace_id = format(ctx.trace_id, "032x") if ctx.trace_id else None
        record.span_id = format(ctx.span_id, "016x") if ctx.span_id else None
        record.correlation_id = get_correlation_id() or None
        return True


def configure_json_logging(service_name: str, level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt=(
            "%(asctime)s %(levelname)s %(name)s %(message)s "
            "%(trace_id)s %(span_id)s %(correlation_id)s %(service)s"
        ),
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(TraceContextFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.service = service_name
        return record

    logging.setLogRecordFactory(record_factory)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
