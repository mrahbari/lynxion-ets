"""E4.T2 — unit tests for infrastructure/shared/pending_orders_tracker.py.

PendingOrdersTracker is a process-wide singleton with CLASS-LEVEL state, so the
autouse fixture clears it around every test for isolation. In-memory only, no I/O.
Pins the duplicate-prevention contract used to block duplicate same-direction
trades per symbol.
"""

from datetime import datetime, timedelta

import pytest

from domain.value_objects import Symbol
from infrastructure.shared.pending_orders_tracker import (
    PendingOrdersTracker,
    PendingOrderInfo,
)

BTC = Symbol("BTCUSDT")
ETH = Symbol("ETHUSDT")


@pytest.fixture(autouse=True)
def _clean_tracker_state():
    PendingOrdersTracker.clear_all_pending_orders()
    yield
    PendingOrdersTracker.clear_all_pending_orders()


@pytest.mark.unit
def test_singleton_identity():
    assert PendingOrdersTracker() is PendingOrdersTracker()


@pytest.mark.unit
def test_add_then_detect_same_direction_only():
    PendingOrdersTracker.add_pending_order(BTC, "BUY", "o1")
    assert PendingOrdersTracker.has_pending_order_in_direction(BTC, "BUY") is True
    assert PendingOrdersTracker.has_pending_order_in_direction(BTC, "SELL") is False
    # different symbol is unaffected
    assert PendingOrdersTracker.has_pending_order_in_direction(ETH, "BUY") is False


@pytest.mark.unit
def test_add_is_idempotent_per_order_id():
    PendingOrdersTracker.add_pending_order(BTC, "BUY", "o1")
    PendingOrdersTracker.add_pending_order(BTC, "BUY", "o1")   # duplicate id
    assert len(PendingOrdersTracker.get_pending_orders_for_symbol(BTC)) == 1


@pytest.mark.unit
def test_distinct_order_ids_accumulate():
    PendingOrdersTracker.add_pending_order(BTC, "BUY", "o1")
    PendingOrdersTracker.add_pending_order(BTC, "SELL", "o2")
    orders = PendingOrdersTracker.get_pending_orders_for_symbol(BTC)
    assert {o.order_id for o in orders} == {"o1", "o2"}


@pytest.mark.unit
def test_remove_order_and_cleanup_empty_symbol():
    PendingOrdersTracker.add_pending_order(BTC, "BUY", "o1")
    PendingOrdersTracker.remove_pending_order(BTC, "o1")
    # removing the last order for a symbol drops the symbol key entirely
    assert PendingOrdersTracker.get_pending_orders_for_symbol(BTC) == []
    assert PendingOrdersTracker.has_pending_order_in_direction(BTC, "BUY") is False


@pytest.mark.unit
def test_get_for_unknown_symbol_is_empty():
    assert PendingOrdersTracker.get_pending_orders_for_symbol(ETH) == []


@pytest.mark.unit
def test_clear_all_empties_everything():
    PendingOrdersTracker.add_pending_order(BTC, "BUY", "o1")
    PendingOrdersTracker.add_pending_order(ETH, "SELL", "o2")
    PendingOrdersTracker.clear_all_pending_orders()
    assert PendingOrdersTracker.get_pending_orders_for_symbol(BTC) == []
    assert PendingOrdersTracker.get_pending_orders_for_symbol(ETH) == []


@pytest.mark.unit
def test_cleanup_removes_only_stale_orders():
    PendingOrdersTracker.add_pending_order(BTC, "BUY", "old")
    PendingOrdersTracker.add_pending_order(BTC, "SELL", "fresh")
    # Age the "old" order past the 30-minute window (mutate the live reference).
    for info in PendingOrdersTracker.get_pending_orders_for_symbol(BTC):
        if info.order_id == "old":
            info.timestamp = datetime.now() - timedelta(minutes=45)

    PendingOrdersTracker.cleanup_old_pending_orders(max_age_minutes=30)

    remaining = {o.order_id for o in PendingOrdersTracker.get_pending_orders_for_symbol(BTC)}
    assert remaining == {"fresh"}


@pytest.mark.unit
def test_pending_order_info_defaults_timestamp_to_now():
    before = datetime.now()
    info = PendingOrderInfo("BUY", "o1")
    assert info.side == "BUY" and info.order_id == "o1"
    assert info.timestamp >= before
