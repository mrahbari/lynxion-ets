"""The platform must not see, manage, count or enter symbols owned by the v2 sleeve."""
import json
from types import SimpleNamespace

import pytest

from infrastructure.brokers.adapters import bingx_adapter as ba
from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker


@pytest.fixture
def owned(tmp_path, monkeypatch):
    p = tmp_path / "owned.json"
    p.write_text(json.dumps({"symbols": ["BTCUSDT", "XRP-USDT"]}))
    monkeypatch.setenv("V2_OWNED_SYMBOLS_FILE", str(p))
    return p


def _broker(response):
    b = _BingXBroker.__new__(_BingXBroker)
    b._make_request = lambda *a, **k: response
    b.logger = ba.logging.getLogger("t")
    return b


def test_owned_positions_hidden(owned):
    rows = [{"symbol": "BTC-USDT", "positionAmt": "1"}, {"symbol": "ETH-USDT", "positionAmt": "2"},
            {"symbol": "XRP-USDT", "positionAmt": "-3"}]
    assert [r["symbol"] for r in _broker({"code": 0, "data": rows}).get_open_positions()] == ["ETH-USDT"]


def test_owned_pending_orders_hidden(owned):
    orders = [{"symbol": "BTC-USDT", "type": "STOP_MARKET"}, {"symbol": "SOL-USDT", "type": "STOP_MARKET"}]
    ev = _broker({"code": 0, "data": {"orders": orders}}).get_pending_orders_evidence()
    assert ev["status"] == "OK" and [o["symbol"] for o in ev["orders"]] == ["SOL-USDT"]


def test_entry_on_owned_symbol_rejected_before_admission(owned):
    b = _broker({"code": 0, "data": []})
    b._assert_entry_admission = lambda order: pytest.fail("admission must not be reached")
    r = b.execute_order(SimpleNamespace(symbol=SimpleNamespace(value="XRPUSDT")))
    assert r["success"] is False and "v2 sleeve" in r["error"]


def test_no_file_means_nothing_owned(tmp_path, monkeypatch):
    monkeypatch.setenv("V2_OWNED_SYMBOLS_FILE", str(tmp_path / "missing.json"))
    assert ba.v2_owned_symbols() == frozenset()


def test_corrupt_file_without_prior_good_read_fails_closed(tmp_path, monkeypatch):
    p = tmp_path / "bad.json"; p.write_text("{not json")
    monkeypatch.setenv("V2_OWNED_SYMBOLS_FILE", str(p))
    with pytest.raises(RuntimeError, match="unreadable"):
        ba.v2_owned_symbols()


def test_pre_request_rejection_is_reported_as_not_sent(owned):
    b = _broker({"code": 0, "data": []})
    r = b.execute_order(SimpleNamespace(symbol=SimpleNamespace(value="BTCUSDT")))
    assert r["not_sent"] is True


def test_wrapper_raises_order_not_sent_for_not_sent_results(owned, monkeypatch):
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter, OrderNotSentError
    from infrastructure.risk import symbol_cooldown_gate as g
    monkeypatch.setattr(g.symbol_cooldown_gate, "is_symbol_allowed", lambda *a, **k: (True, "ok"))
    ad = BingXBrokerAdapter.__new__(BingXBrokerAdapter)
    ad.connected = True; ad.logger = ba.logging.getLogger("t")
    ad._broker = SimpleNamespace(execute_order=lambda o: {"success": False, "error": "owned", "not_sent": True})
    from datetime import datetime, timezone
    from decimal import Decimal
    from domain.entities import Order, OrderSide
    from domain.value_objects import Money, Symbol
    order = Order(symbol=Symbol("BTC-USDT"), side=OrderSide.BUY, quantity=Decimal("0.001"),
                  price=Money(Decimal("60000"), "USDT"), order_type="MARKET",
                  timestamp=datetime.now(timezone.utc))
    with pytest.raises(OrderNotSentError):
        ad.place_order(order)
