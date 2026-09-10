"""Utilidades transversales compartidas entre microservicios.

Este paquete NO contiene lógica de dominio ni de negocio de ningún bounded
context: solo infraestructura horizontal (logging, trazabilidad, seguridad
técnica, configuración) reutilizada por Airport Service, Itinerary Service,
API Gateway y Notification Bridge. Compartir esto no acopla los contextos
delimitados entre sí.
"""

from .logging import configure_json_logging, get_logger
from .correlation import CorrelationIdMiddleware, get_correlation_id
from .telemetry import setup_telemetry
from .security import create_access_token, decode_access_token, JWTError
from .vault_client import load_secrets

__all__ = [
    "configure_json_logging",
    "get_logger",
    "CorrelationIdMiddleware",
    "get_correlation_id",
    "setup_telemetry",
    "create_access_token",
    "decode_access_token",
    "JWTError",
    "load_secrets",
]
