"""Errores de dominio del Airport Context."""
from __future__ import annotations


class AirportDomainError(Exception):
    """Base de todos los errores de dominio de este contexto."""


class ExternalSourceUnavailableError(AirportDomainError):
    """La fuente externa (API Colombia) no respondió tras agotar los
    reintentos, o el disyuntor (circuit breaker) está abierto."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"external airport source unavailable: {reason}")
