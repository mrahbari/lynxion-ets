"""B1 — Guaranteed Protection: a position must never remain open without SL/TP.

When the protective (SL/TP) conditional orders fail, the just-opened position is
unwound; if the unwind also fails, the kill switch is engaged. Deterministic test
with a mocked BingX transport (no network)."""

import logging
import sys
from types import SimpleNamespace
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
    b._contract_precisions = {"BTC-USDT": {"pricePrecision": 1, "quantityPrecision": 4}}
    return b


def _order():
    return Order(symbol=Symbol("BTC-USDT"), side=OrderSide.BUY, quantity=Decimal("0.001"),
                 price=Money(Decimal("60000"), "USDT"), order_type="MARKET",
                 stop_loss_price=Money(Decimal("59000"), "USDT"),
                 take_profit_price=Money(Decimal("61000"), "USDT"),
                 requested_leverage=Decimal("1"),
                 timestamp=datetime.now(timezone.utc))


def test_initial_protective_acknowledgements_are_retained(monkeypatch):
    b = _broker()
    b._format_quantity = lambda symbol, quantity: str(quantity)
    b._format_price = lambda symbol, price: str(price)
    monkeypatch.setattr(b, "_make_request", lambda *args, **kwargs: {
        "code": 0, "data": {"order": {"orderId": "MAIN-ACK"}}})
    monkeypatch.setattr(b, "_place_conditional_order", lambda **kwargs: {
        "success": True, "order_id": "SL-ACK" if kwargs["order_type"] == "STOP_MARKET" else "TP-ACK"})
    result = b.execute_order(_order())
    assert result["success"] is True
    assert result["protective_order_ids"] == {"STOP_MARKET": "SL-ACK", "TAKE_PROFIT_MARKET": "TP-ACK"}


def test_adapter_copies_initial_protective_metadata(monkeypatch):
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter
    adapter = object.__new__(BingXBrokerAdapter)
    adapter.connected = True
    adapter.logger = logging.getLogger("fake_initial_ack")
    adapter._format_symbol = lambda symbol: symbol.value
    ids = {"STOP_MARKET": "SL-ACK", "TAKE_PROFIT_MARKET": "TP-ACK"}
    adapter._broker = SimpleNamespace(execute_order=lambda order: {
        "success": True, "order_id": "MAIN-ACK", "protective_order_ids": ids})
    monkeypatch.setattr(sys.modules["infrastructure.risk.symbol_cooldown_gate"].symbol_cooldown_gate,
                        "is_symbol_allowed", lambda symbol: (True, "fake"), raising=False)
    order = _order()
    assert adapter.place_order(order) == "MAIN-ACK"
    assert order.protective_order_ids == ids
    ids["STOP_MARKET"] = "MUTATED"
    assert order.protective_order_ids["STOP_MARKET"] == "SL-ACK"


@pytest.fixture(autouse=True)
def _reset_guard(monkeypatch):
    from shared.live_execution_guard import live_execution_guard
    monkeypatch.setattr("bootstrap.settings.loaders.load_settings", lambda: SimpleNamespace(
        risk=SimpleNamespace(max_leverage=1, max_leverage_limit=1, max_initial_stop_roe_pct=5),
    ))
    monkeypatch.setitem(sys.modules, "infrastructure.strategies.strategy_manager", SimpleNamespace(
        strategy_manager=SimpleNamespace(record_trade_result=lambda *args, **kwargs: None),
    ))
    monkeypatch.setitem(sys.modules, "infrastructure.risk.symbol_cooldown_gate", SimpleNamespace(
        symbol_cooldown_gate=SimpleNamespace(record_stop_loss_exit=lambda *args: None),
    ))
    live_execution_guard.disengage_kill_switch()
    yield
    live_execution_guard.disengage_kill_switch()


def test_protection_failure_unwinds_position(monkeypatch):
    b = _broker()
    calls = {"unwind": 0}

    def fake_request(method, endpoint, params=None, data=None, signed=False):
        if method == "GET":
            return {"code": 0, "data": [{"symbol": "BTC-USDT", "positionAmt": "0"}]}
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


def test_accepted_unwind_with_open_snapshot_engages_kill_switch(monkeypatch):
    from shared.live_execution_guard import live_execution_guard
    b = _broker()

    def fake_request(method, endpoint, params=None, data=None, signed=False):
        if method == "GET":
            return {"code": 0, "data": [{"symbol": "BTC-USDT", "positionAmt": "0.001"}]}
        return {"code": 0, "data": {"order": {"orderId": "MAIN1"}}}

    monkeypatch.setattr(b, "_make_request", fake_request)
    monkeypatch.setattr(b, "_place_conditional_order",
                        lambda **_kwargs: {"success": False, "error": "fake conflict"})
    result = b.execute_order(_order())
    assert result["protection_failed"] is True
    assert result["unwound"] is False
    assert result["orphaned_main_order_id"] == "MAIN1"
    assert live_execution_guard.is_killed() is True


def test_unwind_position_helper(monkeypatch):
    b = _broker()
    monkeypatch.setattr(b, "_make_request", lambda *a, **k: {"code": 0, "data": []})
    assert b._unwind_position("BTC-USDT", "BUY", "0.001", "LONG") is True
    monkeypatch.setattr(b, "_make_request", lambda *a, **k: {"code": 1, "msg": "x"})
    assert b._unwind_position("BTC-USDT", "BUY", "0.001", "LONG") is False


def test_unwind_position_reduce_only_hedge_mode(monkeypatch):
    b = _broker()
    sent_data = {}

    def fake_request(method, endpoint, params=None, data=None, signed=False):
        nonlocal sent_data
        if method == "POST":
            sent_data = data
        return {"code": 0, "data": []}

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

