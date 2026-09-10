"""Tests de `RabbitMQBridge` que no requieren una conexion real a RabbitMQ:
se ejercitan `declare_topology` y `_on_message` con un canal/objetos AMQP
falsos, verificando la topologia declarada y la decision ack/nack."""
from __future__ import annotations

from app.bridge import (
    DEAD_LETTER_EXCHANGE_NAME,
    DEAD_LETTER_QUEUE_NAME,
    EXCHANGE_NAME,
    ROUTING_KEY,
    RabbitMQBridge,
)
from app.processor import Decision


class FakeChannel:
    def __init__(self) -> None:
        self.exchanges_declared: list[dict] = []
        self.queues_declared: list[dict] = []
        self.bindings: list[dict] = []
        self.acked: list[int] = []
        self.nacked: list[tuple[int, bool]] = []

    def exchange_declare(self, exchange, exchange_type, durable):
        self.exchanges_declared.append(
            {"exchange": exchange, "type": exchange_type, "durable": durable}
        )

    def queue_declare(self, queue, durable, arguments=None):
        self.queues_declared.append({"queue": queue, "durable": durable, "arguments": arguments})

    def queue_bind(self, queue, exchange, routing_key=None):
        self.bindings.append({"queue": queue, "exchange": exchange, "routing_key": routing_key})

    def basic_ack(self, delivery_tag):
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacked.append((delivery_tag, requeue))


class FakeMethod:
    def __init__(self, delivery_tag: int) -> None:
        self.delivery_tag = delivery_tag


class FakeProcessor:
    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        self.calls: list[bytes] = []

    def process(self, body: bytes) -> Decision:
        self.calls.append(body)
        return self.decision


def test_declare_topology_wires_dead_letter_exchange_and_main_queue():
    channel = FakeChannel()
    bridge = RabbitMQBridge(amqp_url="amqp://unused", processor=FakeProcessor(Decision.ACK))

    bridge.declare_topology(channel)

    exchange_names = {e["exchange"] for e in channel.exchanges_declared}
    assert EXCHANGE_NAME in exchange_names
    assert DEAD_LETTER_EXCHANGE_NAME in exchange_names

    main_queue = next(q for q in channel.queues_declared if q["queue"] == bridge._queue_name)
    assert main_queue["arguments"] == {"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE_NAME}

    dead_queue = next(q for q in channel.queues_declared if q["queue"] == DEAD_LETTER_QUEUE_NAME)
    assert dead_queue["durable"] is True

    main_binding = next(b for b in channel.bindings if b["exchange"] == EXCHANGE_NAME)
    assert main_binding["routing_key"] == ROUTING_KEY
    assert main_binding["queue"] == bridge._queue_name

    dlx_binding = next(b for b in channel.bindings if b["exchange"] == DEAD_LETTER_EXCHANGE_NAME)
    assert dlx_binding["queue"] == DEAD_LETTER_QUEUE_NAME


def test_on_message_acks_when_processor_decides_ack():
    channel = FakeChannel()
    processor = FakeProcessor(Decision.ACK)
    bridge = RabbitMQBridge(amqp_url="amqp://unused", processor=processor)

    bridge._on_message(channel, FakeMethod(delivery_tag=42), None, b"{}")

    assert channel.acked == [42]
    assert channel.nacked == []


def test_on_message_nacks_without_requeue_when_processor_decides_dead_letter():
    channel = FakeChannel()
    processor = FakeProcessor(Decision.DEAD_LETTER)
    bridge = RabbitMQBridge(amqp_url="amqp://unused", processor=processor)

    bridge._on_message(channel, FakeMethod(delivery_tag=7), None, b"{}")

    assert channel.acked == []
    assert channel.nacked == [(7, False)]


def test_on_message_dead_letters_on_unexpected_processor_exception():
    channel = FakeChannel()

    class ExplodingProcessor:
        def process(self, body: bytes) -> Decision:
            raise RuntimeError("boom")

    bridge = RabbitMQBridge(amqp_url="amqp://unused", processor=ExplodingProcessor())

    bridge._on_message(channel, FakeMethod(delivery_tag=1), None, b"{}")

    assert channel.nacked == [(1, False)]
