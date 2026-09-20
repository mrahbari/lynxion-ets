from decimal import Decimal

import pytest

from domain.entities import Order
from domain.value_objects import Money, Symbol
from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker


class _Logger:
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

    assert result["success"] is True
    assert result["order_id"] == "LIMIT1"
    assert sent[0]["timeInForce"] == "PostOnly"
