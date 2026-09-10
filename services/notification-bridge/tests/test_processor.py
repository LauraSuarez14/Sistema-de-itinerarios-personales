from __future__ import annotations

import json

from app.processor import Decision, MessageProcessor
from tests.fakes import always_fails, always_succeeds, fails_then_succeeds
from tests.test_schema import VALID_EVENT


class SpyMetrics:
    def __init__(self) -> None:
        self.processed = 0
        self.failed = 0
        self.dead_lettered = 0

    def inc_processed(self) -> None:
        self.processed += 1

    def inc_failed(self) -> None:
        self.failed += 1

    def inc_dead_lettered(self) -> None:
        self.dead_lettered += 1


def _body(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def test_valid_event_and_successful_invocation_is_acked():
    invoker = always_succeeds()
    metrics = SpyMetrics()
    processor = MessageProcessor(invoker, metrics=metrics, sleep_fn=lambda s: None)

    decision = processor.process(_body(VALID_EVENT))

    assert decision is Decision.ACK
    assert invoker.calls == [VALID_EVENT]
    assert metrics.processed == 1
    assert metrics.dead_lettered == 0


def test_malformed_json_is_dead_lettered_without_calling_lambda():
    invoker = always_succeeds()
    metrics = SpyMetrics()
    processor = MessageProcessor(invoker, metrics=metrics, sleep_fn=lambda s: None)

    decision = processor.process(b"not-json-at-all")

    assert decision is Decision.DEAD_LETTER
    assert invoker.calls == []
    assert metrics.dead_lettered == 1


def test_invalid_schema_is_dead_lettered_without_calling_lambda():
    invoker = always_succeeds()
    metrics = SpyMetrics()
    processor = MessageProcessor(invoker, metrics=metrics, sleep_fn=lambda s: None)

    broken = {"event_type": "ItineraryCreatedEvent"}  # le faltan campos requeridos

    decision = processor.process(_body(broken))

    assert decision is Decision.DEAD_LETTER
    assert invoker.calls == []
    assert metrics.dead_lettered == 1


def test_lambda_failure_is_retried_up_to_max_attempts_then_dead_lettered():
    invoker = always_fails()
    metrics = SpyMetrics()
    processor = MessageProcessor(
        invoker, max_attempts=3, metrics=metrics, sleep_fn=lambda s: None
    )

    decision = processor.process(_body(VALID_EVENT))

    assert decision is Decision.DEAD_LETTER
    assert len(invoker.calls) == 3
    assert metrics.failed == 3
    assert metrics.dead_lettered == 1
    assert metrics.processed == 0


def test_lambda_succeeds_on_retry_before_exhausting_attempts():
    invoker = fails_then_succeeds(failures=2)
    metrics = SpyMetrics()
    processor = MessageProcessor(
        invoker, max_attempts=3, metrics=metrics, sleep_fn=lambda s: None
    )

    decision = processor.process(_body(VALID_EVENT))

    assert decision is Decision.ACK
    assert len(invoker.calls) == 3
    assert metrics.failed == 2
    assert metrics.processed == 1
    assert metrics.dead_lettered == 0


def test_backoff_sleep_is_called_between_retries_but_not_after_last_attempt():
    invoker = always_fails()
    sleep_calls: list[float] = []
    processor = MessageProcessor(
        invoker,
        max_attempts=3,
        initial_backoff_seconds=1.0,
        sleep_fn=sleep_calls.append,
    )

    processor.process(_body(VALID_EVENT))

    # 3 intentos -> solo 2 backoffs entre ellos, nunca despues del ultimo intento.
    assert sleep_calls == [1.0, 2.0]
