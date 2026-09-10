"""Puertos (interfaces) del contexto Itinerary. Definen los contratos que la
capa `application/` usa para orquestar el dominio, implementados por adapters
concretos en `infrastructure/`. Ninguna clase de este modulo importa
SQLAlchemy, grpc, pika ni prometheus_client: son abstracciones puras."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .entities import AirportSnapshot, Itinerary
from .outbox import OutboxEvent


class AirportValidationPort(ABC):
    """Valida la existencia de un aeropuerto contra el Airport Service.

    Contrato:
    - Devuelve `AirportSnapshot` si el aeropuerto existe.
    - Devuelve `None` si el Airport Service respondio explicitamente que no
      existe (found=false / HTTP 404).
    - Lanza `AirportServiceUnavailableError` (definido en `domain.errors`) si
      el Airport Service no pudo contactarse en absoluto (ni por gRPC ni por
      el fallback REST) tras agotar los reintentos.
    """

    @abstractmethod
    def get_airport(self, airport_id: int) -> Optional[AirportSnapshot]:
        raise NotImplementedError


class ItineraryRepositoryPort(ABC):
    """Persistencia del agregado `Itinerary`. `add_with_outbox` es la
    operacion clave del patron Transactional Outbox (ADR 0002): inserta el
    itinerario y la fila de outbox en una unica transaccion atomica."""

    @abstractmethod
    def add_with_outbox(self, itinerary: Itinerary, outbox_event: OutboxEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, itinerary_id: UUID) -> Optional[Itinerary]:
        raise NotImplementedError

    @abstractmethod
    def list(self, page: int, page_size: int) -> tuple[list[Itinerary], int]:
        raise NotImplementedError

    @abstractmethod
    def update(self, itinerary: Itinerary) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, itinerary_id: UUID) -> bool:
        """Devuelve True si existia y fue eliminado, False si no existia."""
        raise NotImplementedError


class OutboxRepositoryPort(ABC):
    """Acceso a las filas de `outbox_events` pendientes de publicar. Lo usa
    el `OutboxRelay` (capa application), nunca los casos de uso de negocio."""

    @abstractmethod
    def fetch_pending(self, limit: int = 50) -> list[OutboxEvent]:
        raise NotImplementedError

    @abstractmethod
    def mark_published(self, event_id: UUID, published_at) -> None:
        raise NotImplementedError


class EventPublisherPort(ABC):
    """Publica un payload ya serializable en el broker de mensajeria. Debe
    devolver True solo si el broker confirmo la entrega (publisher confirms
    en el caso de RabbitMQ/pika), False en cualquier otro caso -- nunca debe
    lanzar hacia el llamador salvo por errores de programacion."""

    @abstractmethod
    def publish(self, routing_key: str, payload: dict) -> bool:
        raise NotImplementedError


class MetricsPort(ABC):
    """Abstrae la emision de metricas para que `application/` no dependa de
    `prometheus_client` directamente (esa dependencia vive solo en el adapter
    de infraestructura `infrastructure/metrics.py`)."""

    @abstractmethod
    def set_outbox_pending(self, count: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def inc_outbox_published(self, amount: int = 1) -> None:
        raise NotImplementedError
