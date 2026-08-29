"""B1 — Guaranteed Protection: a position must never remain open without SL/TP.

When the protective (SL/TP) conditional orders fail, the just-opened position is
unwound; if the unwind also fails, the kill switch is engaged. Deterministic test
with a mocked BingX transport (no network)."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker


def _broker():
    b = object.__new__(_BingXBroker)          # bypass __init__ (no network/keys)
    b.logger = logging.getLogger("test_b1")
    b._assert_entry_admission = lambda order: (True, "test admission")
    return b


def _order():
    return Order(symbol=Symbol("BTC-USDT"), side=OrderSide.BUY, quantity=Decimal("0.001"),
                 price=Money(Decimal("60000"), "USDT"), order_type="MARKET",
                 stop_loss_price=Money(Decimal("59000"), "USDT"),
                 take_profit_price=Money(Decimal("61000"), "USDT"),
                 timestamp=datetime.now(timezone.utc))


@pytest.fixture(autouse=True)
def _reset_guard():
    from shared.live_execution_guard import live_execution_guard
    live_execution_guard.disengage_kill_switch()
    yield
    live_execution_guard.disengage_kill_switch()


def test_protection_failure_unwinds_position(monkeypatch):
    b = _broker()
    calls = {"unwind": 0}

    def fake_request(method, endpoint, params=None, data=None, signed=False):
        # In Hedge mode (LONG/SHORT), reduceOnly is not sent.
        if data and (data.get("reduceOnly") == "true" or (data.get("side") == "SELL" and data.get("positionSide") == "LONG")):
            calls["unwind"] += 1
            return {"code": 0, "data": {"order": {"orderId": "UNWIND1"}}}   # unwind accepted
        return {"code": 0, "data": {"order": {"orderId": "MAIN1"}}}          # main order accepted

    monkeypatch.setattr(b, "_make_request", fake_request)
    monkeypatch.setattr(b, "_place_conditional_order",
                        lambda **k: {"success": False, "error": "sim conditional reject"})

    result = b.execute_order(_order())
    assert result["success"] is False and result["protection_failed"] is True
    assert result["unwound"] is True and result["orphaned_main_order_id"] is None
    assert calls["unwind"] == 1, "must place exactly one reduceOnly unwind order"


def test_unwind_failure_engages_kill_switch(monkeypatch):
    from shared.live_execution_guard import live_execution_guard
    b = _broker()

    def fake_request(method, endpoint, params=None, data=None, signed=False):
        # In Hedge mode (LONG/SHORT), reduceOnly is not sent.
        if data and (data.get("reduceOnly") == "true" or (data.get("side") == "SELL" and data.get("positionSide") == "LONG")):
            return {"code": 100, "msg": "unwind rejected"}                   # unwind FAILS
        return {"code": 0, "data": {"order": {"orderId": "MAIN1"}}}

    monkeypatch.setattr(b, "_make_request", fake_request)
    monkeypatch.setattr(b, "_place_conditional_order",
                        lambda **k: {"success": False, "error": "sim conditional reject"})

    result = b.execute_order(_order())
    assert result["success"] is False and result["unwound"] is False
    assert result["orphaned_main_order_id"] == "MAIN1"
    assert live_execution_guard.is_killed() is True, "naked position must halt trading"


def test_unwind_position_helper(monkeypatch):
    b = _broker()
    monkeypatch.setattr(b, "_make_request", lambda *a, **k: {"code": 0})
    assert b._unwind_position("BTC-USDT", "BUY", "0.001", "LONG") is True
    monkeypatch.setattr(b, "_make_request", lambda *a, **k: {"code": 1, "msg": "x"})
    assert b._unwind_position("BTC-USDT", "BUY", "0.001", "LONG") is False


def test_unwind_position_reduce_only_hedge_mode(monkeypatch):
    b = _broker()
    sent_data = {}

    def fake_request(method, endpoint, params=None, data=None, signed=False):
        nonlocal sent_data
        sent_data = data
        return {"code": 0}

    monkeypatch.setattr(b, "_make_request", fake_request)

    # In LONG position (hedge mode), reduceOnly should NOT be set
    b._unwind_position("BTC-USDT", "BUY", "0.001", "LONG")
    assert "reduceOnly" not in sent_data

    # In SHORT position (hedge mode), reduceOnly should NOT be set
    b._unwind_position("BTC-USDT", "BUY", "0.001", "SHORT")
    assert "reduceOnly" not in sent_data

    # In BOTH position (one-way mode), reduceOnly SHOULD be set
    b._unwind_position("BTC-USDT", "BUY", "0.001", "BOTH")
    assert sent_data.get("reduceOnly") == "true"


def test_precision_formatting(monkeypatch):
    b = _broker()
    b._contract_precisions = {
        "BTC-USDT": {"pricePrecision": 1, "quantityPrecision": 4},
        "XRP-USDT": {"pricePrecision": 4, "quantityPrecision": 0}
    }
    
    assert b._format_price("BTC-USDT", 65432.1234) == "65432.1"
    assert b._format_price("BTC-USDT", 65432) == "65432.0"
    assert b._format_quantity("BTC-USDT", 0.123456) == "0.1235"
    
    assert b._format_price("XRP-USDT", 0.54321) == "0.5432"
    assert b._format_quantity("XRP-USDT", 123.456) == "123"

