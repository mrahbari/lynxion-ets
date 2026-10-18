"""Offline regression for ambiguous BingX order POST responses."""

import logging
from types import SimpleNamespace

import pytest
import requests


@pytest.mark.parametrize("order_type", ["MARKET", "STOP_MARKET", "TAKE_PROFIT_MARKET"])
def test_order_post_timeout_is_not_blindly_retried(order_type):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    attempts = []

    def lost_response(*_args, **_kwargs):
        attempts.append(1)
        raise requests.exceptions.Timeout("response lost")

    broker = object.__new__(_BingXBroker)
    broker.base_url = "https://example.invalid"
    broker.api_key = "isolated-test-key"
    broker.secret_key = "isolated-test-secret"
    broker.default_timeout = 1
    broker.logger = logging.getLogger("test_bingx_order_post_retry")
    broker.session = SimpleNamespace(post=lost_response)
    broker._rate_limit = lambda **_kwargs: 0.0

    with pytest.raises(requests.exceptions.Timeout):
        broker._make_request(
            "POST", "/openApi/swap/v2/trade/order",
            data={"symbol": "BTC-USDT", "type": order_type}, signed=True,
        )
    assert len(attempts) == 1


def test_non_order_post_retains_transient_retry():
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    attempts = []

    def transient(*_args, **_kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise requests.exceptions.Timeout("response lost")
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"code": 0})

    broker = object.__new__(_BingXBroker)
    broker.base_url = "https://example.invalid"
    broker.api_key = "isolated-test-key"
    broker.secret_key = "isolated-test-secret"
    broker.default_timeout = 1
    broker.logger = logging.getLogger("test_bingx_non_order_post_retry")
    broker.session = SimpleNamespace(post=transient)
    broker._rate_limit = lambda **_kwargs: 0.0

    result = broker._make_request(
        "POST", "/openApi/swap/v2/trade/leverage",
        data={"symbol": "BTC-USDT"}, signed=True,
    )
    assert result["code"] == 0
    assert len(attempts) == 2


@pytest.mark.parametrize("order_type", ["STOP_MARKET", "TAKE_PROFIT_MARKET"])
def test_conditional_conflict_preserves_existing_protection(monkeypatch, order_type):
    from infrastructure.brokers.adapters import bingx_adapter

    broker = object.__new__(bingx_adapter._BingXBroker)
    broker.logger = logging.getLogger("test_bingx_conditional_conflict")
    broker._format_price = lambda _symbol, price: str(price)
    broker._format_quantity = lambda _symbol, quantity: str(quantity)
    requests_seen = []
    broker._make_request = lambda *args, **kwargs: (
        requests_seen.append((args, kwargs)),
        {"code": 110406, "msg": "position protection already exists"},
    )[1]
    broker.get_pending_orders = lambda _symbol: [
        {"type": order_type, "orderId": "existing-protection"},
    ]
    cancelled = []
    broker.cancel_order = lambda order_id, symbol: cancelled.append((order_id, symbol))
    monkeypatch.setattr(bingx_adapter.time, "sleep", lambda _seconds: None)

    result = broker._place_conditional_order(
        "BTC-USDT", "SELL", "1", "95", order_type, "LONG",
    )
    assert result["success"] is False
    assert len(requests_seen) == 1
    assert cancelled == []


@pytest.mark.parametrize("position_response,expected", [
    ({"code": 0, "data": [{"symbol": "BTC-USDT", "positionAmt": "1"}]}, False),
    ({"code": 0, "data": [{"symbol": "BTC-USDT", "positionAmt": "0"}]}, True),
    ({"code": 0, "data": [{"symbol": "ETH-USDT", "positionAmt": "0"}]}, False),
    ({"code": 100001, "msg": "position query failed"}, False),
])
def test_unwind_ack_requires_flat_broker_snapshot(position_response, expected):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("test_bingx_unwind_snapshot")
    calls = []

    def request(method, _endpoint, params=None, data=None, signed=False):
        calls.append(method)
        if method == "POST":
            return {"code": 0, "data": {"order": {"orderId": "close-accepted"}}}
        return position_response

    broker._make_request = request
    assert broker._unwind_position("BTC-USDT", "BUY", "1", "LONG") is expected
    assert calls == ["POST", "GET"]
