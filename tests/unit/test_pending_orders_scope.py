from datetime import datetime, timedelta, timezone

from domain.value_objects import Symbol
from infrastructure.messaging.clock import ReplayClock
from infrastructure.shared.pending_orders_tracker import PendingOrdersState, PendingOrdersTracker


def test_two_pending_order_scopes_and_live_facade_are_independent():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = PendingOrdersState(clock=ReplayClock(start))
    second = PendingOrdersState(clock=ReplayClock(start))
    symbol = Symbol("BTCUSDT")
    first.add_pending_order(symbol, "BUY", "same-id")
    assert first.has_pending_order_in_direction(symbol, "BUY")
    assert not second.has_pending_order_in_direction(symbol, "BUY")
    assert not PendingOrdersTracker.has_pending_order_in_direction(symbol, "BUY")
    second.add_pending_order(symbol, "SELL", "same-id")
    assert second.has_pending_order_in_direction(symbol, "SELL")
    assert not first.has_pending_order_in_direction(symbol, "SELL")


def test_scoped_pending_expiry_uses_event_clock():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    clock = ReplayClock(start)
    state = PendingOrdersState(clock=clock)
    symbol = Symbol("ETHUSDT")
    state.add_pending_order(symbol, "SHORT", "e1")
    assert state.has_pending_order_in_direction(symbol, "SHORT")
    clock.advance(start + timedelta(seconds=31))
    assert not state.has_pending_order_in_direction(symbol, "SHORT")
