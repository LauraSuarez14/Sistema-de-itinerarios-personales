"""DTOs de entrada/salida de los casos de uso. Dataclasses simples (no
Pydantic) para que `application/` no dependa de nada externo -- la
validacion de FORMA (tipos, campos requeridos) ya la hace Pydantic en
`api/schemas.py`; aqui solo se transportan datos ya con forma correcta."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CreateItineraryCommand:
    user_name: str
    origin_airport_id: int
    destination_airport_id: int
    travel_date: date
    duration_minutes: int


@dataclass
class UpdateItineraryCommand:
    user_name: str
    origin_airport_id: int
    destination_airport_id: int
    travel_date: date
    duration_minutes: int
