"""E4.T4 — unit tests for infrastructure/messaging/message_bus_adapter.py.

Deeper than the conformance behavioral slice: pins ordering, multi-subscriber
fan-out, idempotent-safe unsubscribe, the publish-time snapshot semantics, and
the E3.T6 'callback exceptions propagate, not swallowed' guarantee. No I/O.
"""

import pytest

from infrastructure.messaging.message_bus_adapter import MessageBusAdapter


@pytest.mark.unit
def test_fan_out_preserves_subscription_order():
    bus = MessageBusAdapter()
    seen = []
    bus.subscribe("e", lambda d: seen.append(("a", d)))
    bus.subscribe("e", lambda d: seen.append(("b", d)))
    bus.publish("e", 1)
    assert seen == [("a", 1), ("b", 1)]


@pytest.mark.unit
def test_publish_to_topic_with_no_subscribers_is_noop():
    MessageBusAdapter().publish("nobody", {"x": 1})   # must not raise


@pytest.mark.unit
def test_unsubscribe_unknown_callback_and_topic_is_safe():
    bus = MessageBusAdapter()
    bus.unsubscribe("missing-topic", lambda d: None)   # unknown topic -> no-op
    cb = lambda d: None
    bus.subscribe("e", cb)
    bus.unsubscribe("e", lambda d: None)               # not-subscribed cb -> no-op (ValueError swallowed)
    received = []
    bus.subscribe("e", received.append)
    bus.publish("e", 7)
    assert received == [7]


@pytest.mark.unit
def test_publish_uses_snapshot_so_mid_dispatch_subscribe_is_deferred():
    bus = MessageBusAdapter()
    late = []

    def subscribes_during_dispatch(_):
        bus.subscribe("e", late.append)

    bus.subscribe("e", subscribes_during_dispatch)
    bus.publish("e", "first")     # the late subscriber is added but not called this round
    assert late == []
    bus.publish("e", "second")    # now it fires
    assert late == ["second"]


@pytest.mark.unit
def test_callback_exception_propagates_to_publisher():
    bus = MessageBusAdapter()

    def boom(_):
        raise RuntimeError("not swallowed")

    bus.subscribe("e", boom)
    with pytest.raises(RuntimeError, match="not swallowed"):
        bus.publish("e", None)
