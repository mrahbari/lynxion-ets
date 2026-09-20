"""B2 — broker-level idempotency: a client_order_id is generated once and transmitted,
so a retry of the same order deduplicates at the exchange."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.brokers.adapters.bingx_adapter import (
    BingXBrokerAdapter,
    _BingXBroker,
    ensure_client_order_id,
)


def _order(coid=None):
    return Order(symbol=Symbol("BTC-USDT"), side=OrderSide.BUY, quantity=Decimal("0.001"),
                 price=Money(Decimal("60000"), "USDT"), order_type="MARKET",
                 client_order_id=coid, timestamp=datetime.now(timezone.utc))


def test_ensure_client_order_id_generates_once_and_is_valid():
    o = _order()
    a = ensure_client_order_id(o)
    b = ensure_client_order_id(o)            # same object -> same id (idempotent)
    assert a == b == o.client_order_id
    assert a.startswith("x") and a[1:].isalnum() and len(a) <= 40
    # an order that already carries an id is preserved unchanged
    o2 = _order(coid="myfixedid123")
    assert ensure_client_order_id(o2) == "myfixedid123"


def test_place_order_transmits_client_order_id(monkeypatch):
    b = object.__new__(_BingXBroker)
    b.logger = logging.getLogger("test_b2")
    monkeypatch.setattr(b, "_assert_entry_admission", lambda order: (True, "test admission"))
    sent = []
    monkeypatch.setattr(b, "_make_request",
                        lambda method, endpoint, params=None, data=None, signed=False:
                        (sent.append(data), {"code": 0, "data": {"order": {"orderId": "MAIN1"}}})[1])

    o = _order()
    b.execute_order(o)                        # no SL/TP -> single order_data path
    assert sent, "an order payload must have been sent"
    assert sent[0].get("clientOrderId") == o.client_order_id
    assert o.client_order_id, "order must now carry the generated idempotency key"


def test_retry_of_same_order_reuses_id(monkeypatch):
    b = object.__new__(_BingXBroker)
    b.logger = logging.getLogger("test_b2")
    monkeypatch.setattr(b, "_assert_entry_admission", lambda order: (True, "test admission"))
    sent = []
    monkeypatch.setattr(b, "_make_request",
                        lambda method, endpoint, params=None, data=None, signed=False:
                        (sent.append(data.get("clientOrderId")), {"code": 0, "data": {"order": {"orderId": "M"}}})[1])
    o = _order()
    b.execute_order(o)
    b.execute_order(o)                        # "retry" of the same logical order
    assert sent[0] == sent[1], "exchange must receive the same idempotency key on retry -> dedup"


def test_adapter_retry_reuses_id_on_original_logical_order(monkeypatch):
    adapter = object.__new__(BingXBrokerAdapter)
    adapter.connected = True
    adapter.logger = logging.getLogger("test_b2_adapter")
    adapter._format_symbol = lambda symbol: symbol
    sent = []

    class Broker:
        def execute_order(self, order):
            sent.append(order.client_order_id)
            return {"success": True, "order_id": "accepted"}

    adapter._broker = Broker()
    monkeypatch.setattr(
        "infrastructure.risk.symbol_cooldown_gate.symbol_cooldown_gate.is_symbol_allowed",
        lambda _symbol: (True, "test"),
    )
    order = _order()

    adapter.place_order(order)
    adapter.place_order(order)

    assert order.client_order_id
    assert sent == [order.client_order_id, order.client_order_id]
