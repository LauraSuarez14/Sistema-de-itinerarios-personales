from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.application.outbox_relay import OutboxRelay
from app.domain.outbox import OutboxEvent
from tests.fakes import FakeEventPublisher, FakeOutboxRepository


def make_event(published_at=None) -> OutboxEvent:
    return OutboxEvent(
        id=uuid4(),
        aggregate_id=uuid4(),
        event_type="itinerary.created.v1",
        payload={"event_type": "ItineraryCreatedEvent"},
        created_at=datetime.now(timezone.utc),
        published_at=published_at,
    )


class SpyMetrics:
    def __init__(self) -> None:
        self.pending_values: list[int] = []
        self.published_count = 0

    def set_outbox_pending(self, count: int) -> None:
        self.pending_values.append(count)

    def inc_outbox_published(self, amount: int = 1) -> None:
        self.published_count += amount


def test_run_once_publishes_pending_events_and_marks_them_published():
    event = make_event()
    repo = FakeOutboxRepository([event])
    publisher = FakeEventPublisher(should_succeed=True)
    metrics = SpyMetrics()
    relay = OutboxRelay(repo, publisher, metrics=metrics)

    published_count = relay.run_once()

    assert published_count == 1
    assert event.published_at is not None
    assert publisher.published == [("itinerary.created.v1", event.payload)]
    assert metrics.pending_values == [1]
    assert metrics.published_count == 1


def test_run_once_does_not_mark_published_when_broker_does_not_confirm():
    event = make_event()
    repo = FakeOutboxRepository([event])
    publisher = FakeEventPublisher(should_succeed=False)
    relay = OutboxRelay(repo, publisher)

    published_count = relay.run_once()

    assert published_count == 0
    assert event.published_at is None
    # El evento sigue pendiente para el siguiente ciclo.
    assert repo.fetch_pending() == [event]


def test_run_once_ignores_already_published_events():
    already_published = make_event(published_at=datetime.now(timezone.utc))
    pending = make_event()
    repo = FakeOutboxRepository([already_published, pending])
    publisher = FakeEventPublisher(should_succeed=True)
    relay = OutboxRelay(repo, publisher)

    published_count = relay.run_once()

    assert published_count == 1
    assert publisher.published == [("itinerary.created.v1", pending.payload)]


def test_start_and_stop_run_background_thread_without_errors():
    repo = FakeOutboxRepository([make_event()])
    publisher = FakeEventPublisher(should_succeed=True)
    relay = OutboxRelay(repo, publisher, interval_seconds=0.05)

    relay.start()
    relay.start()  # calling twice must be a no-op, not spawn a second thread
    import time

    time.sleep(0.2)
    relay.stop(timeout=1)

    assert publisher.published  # at least one cycle ran
