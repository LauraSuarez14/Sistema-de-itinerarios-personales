"""Value object del patron Transactional Outbox (ver ADR 0002). Vive en el
dominio porque el caso de uso `CreateItineraryUseCase` es quien decide que
fila de outbox crear (evento de dominio -> evento de integracion), aunque su
persistencia y publicacion sean responsabilidad de infraestructura."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID


@dataclass
class OutboxEvent:
    id: UUID
    aggregate_id: UUID
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
    published_at: Optional[datetime] = None
