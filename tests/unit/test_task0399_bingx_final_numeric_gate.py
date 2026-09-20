from decimal import Decimal
import json

import pytest

from domain.entities import Order
from domain.value_objects import Money, Symbol
from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker, extract_bingx_order_id


class _Logger:
    def debug(self, *_args, **_kwargs):
        pass

    def info(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass

    def warning(self, *_args, **_kwargs):
        pass


def _broker():
    broker = object.__new__(_BingXBroker)
    broker.logger = _Logger()
    broker._contract_precisions = {}
    broker._make_request = lambda *_args, **_kwargs: pytest.fail("broker request must not run")
    return broker


def _order(**overrides):
    values = {
        "symbol": Symbol("BTCUSDT"),
        "side": "BUY",
        "quantity": Decimal("0.001"),
        "price": Money(Decimal("60000"), "USDT"),
        "stop_loss_price": Money(Decimal("59000"), "USDT"),
        "take_profit_price": Money(Decimal("62000"), "USDT"),
    }
    values.update(overrides)
    return Order(**values)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quantity", Decimal("NaN")),
        ("price", Money(Decimal("Infinity"), "USDT")),
        ("stop_loss_price", Money(Decimal("NaN"), "USDT")),
        ("take_profit_price", Money(Decimal("-Infinity"), "USDT")),
    ],
)
def test_low_level_exchange_boundary_rejects_nonfinite_values(field, value):
    result = _broker()._execute_order_after_admission(_order(**{field: value}))

    assert result["success"] is False
    assert field in result["error"]
    assert "finite" in result["error"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"symbol": Symbol("NOTREALUSDT")}, "symbol is not approved: NOTREALUSDT"),
        ({"side": "HOLD"}, "side must be BUY or SELL"),
        ({"order_type": "ICEBERG"}, "entry order type must be MARKET or LIMIT"),
        (
            {"order_type": "LIMIT", "price": None},
            "limit order requires price",
        ),
        (
            {"order_type": "LIMIT", "time_in_force": "DAY"},
            "limit time in force must be GTC, IOC, FOK, or PostOnly",
        ),
        ({"position_side": "UP"}, "position side must be LONG, SHORT, or BOTH"),
        (
            {"client_order_id": "invalid-id"},
            "client order id must be alphanumeric and at most 40 characters",
        ),
        (
            {"client_order_id": "x" * 41},
            "client order id must be alphanumeric and at most 40 characters",
        ),
    ],
)
def test_low_level_exchange_boundary_rejects_unknown_entry_contract(overrides, message):
    result = _broker()._execute_order_after_admission(_order(**overrides))

    assert result == {"success": False, "order_id": None, "error": message}


def test_limit_order_transmits_canonical_post_only_time_in_force():
    broker = _broker()
    sent = []
    broker._make_request = lambda _method, _endpoint, **kwargs: (
        sent.append(kwargs["data"]),
        {"code": 0, "data": {"orderId": "LIMIT1"}},
    )[1]

    result = broker._execute_order_after_admission(
        _order(
            order_type="LIMIT",
            time_in_force="POST_ONLY",
            stop_loss_price=None,
            take_profit_price=None,
        )
    )

    assert result["success"] is True, result
    assert result["order_id"] == "LIMIT1"
    assert sent[0]["timeInForce"] == "PostOnly"


def test_order_identity_prefers_precision_safe_string_field():
    response = {
        "code": 0,
        "data": {"orderID": "9223372036854775807", "orderId": 9223372036854775807},
    }

    assert extract_bingx_order_id(response) == "9223372036854775807"


def test_limit_protection_uses_official_nested_json_fields():
    broker = _broker()
    sent = []
    broker._make_request = lambda _method, _endpoint, **kwargs: (
        sent.append(kwargs["data"]),
        {"code": 0, "data": {"orderID": "LIMIT2"}},
    )[1]

    result = broker._execute_order_after_admission(_order(order_type="LIMIT"))

    assert result["success"] is True, result
    payload = sent[0]
    assert "stopLossPrice" not in payload
    assert "takeProfitPrice" not in payload
    stop_loss = json.loads(payload["stopLoss"])
    take_profit = json.loads(payload["takeProfit"])
    assert stop_loss == {
        "type": "STOP_MARKET",
        "stopPrice": 59000.0,
        "workingType": "MARK_PRICE",
    }
    assert take_profit == {
        "type": "TAKE_PROFIT_MARKET",
        "stopPrice": 62000.0,
        "workingType": "MARK_PRICE",
    }
    assert isinstance(stop_loss["stopPrice"], float)
    assert isinstance(take_profit["stopPrice"], float)


def test_conditional_conflict_recovery_uses_client_identity_and_current_response(monkeypatch):
    broker = _broker()
    responses = [
        {"code": 110406, "msg": "position sl already exists"},
        {"code": 0, "data": {"orderID": "NEWSTOP"}},
    ]
    broker._make_request = lambda *_args, **_kwargs: responses.pop(0)
    broker.get_pending_orders = lambda _symbol: [
        {"type": "STOP_MARKET", "orderId": None, "clientOrderId": "xoldstop"}
    ]
    cancelled = []
    broker.cancel_order = lambda order_id, symbol: cancelled.append((order_id, symbol)) or True
    monkeypatch.setattr("infrastructure.brokers.adapters.bingx_adapter.time.sleep", lambda _delay: None)

    result = broker._place_conditional_order(
        symbol="BTC-USDT",
        side="SELL",
        quantity="0.001",
        stop_price="59000",
        order_type="STOP_MARKET",
        position_side="LONG",
    )

    assert result["success"] is True
    assert result["order_id"] == "NEWSTOP"
    assert cancelled == [("xoldstop", "BTC-USDT")]
