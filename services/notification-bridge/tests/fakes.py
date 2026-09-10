"""Fakes en memoria usados por los tests, para no depender de boto3/pika
reales ni de LocalStack/RabbitMQ levantados."""
from __future__ import annotations

from app.errors import LambdaInvocationError


class FakeLambdaInvoker:
    """Simula `LambdaInvoker.invoke`. `outcomes` es una lista de resultados
    consumidos en orden, uno por llamada: un dict (invocacion exitosa) o una
    excepcion (invocacion fallida). Si se agota la lista, repite el ultimo
    elemento."""

    def __init__(self, outcomes: list) -> None:
        self._outcomes = outcomes
        self.calls: list[dict] = []

    def invoke(self, payload: dict) -> dict:
        self.calls.append(payload)
        index = min(len(self.calls) - 1, len(self._outcomes) - 1)
        outcome = self._outcomes[index]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def always_succeeds() -> FakeLambdaInvoker:
    return FakeLambdaInvoker([{"status": "sent"}])


def always_fails() -> FakeLambdaInvoker:
    return FakeLambdaInvoker([LambdaInvocationError("boom")])


def fails_then_succeeds(failures: int) -> FakeLambdaInvoker:
    outcomes = [LambdaInvocationError("boom")] * failures + [{"status": "sent"}]
    return FakeLambdaInvoker(outcomes)
