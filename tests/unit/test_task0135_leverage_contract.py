"""Contract and hydration regressions for TASK-0135."""

from decimal import Decimal
from types import SimpleNamespace


def _adapter_with_positions(rows):
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter

    adapter = object.__new__(BingXBrokerAdapter)
    adapter.connected = True
    adapter.logger = SimpleNamespace(warning=lambda *args, **kwargs: None)
    adapter._broker = SimpleNamespace(get_open_positions=lambda: rows)
    return adapter


def _position_row(symbol="BTC-USDT", leverage="5", isolated=True):
    return {
        "symbol": symbol,
        "positionAmt": "0.01",
        "avgPrice": "100",
        "markPrice": "101",
        "unrealisedPnl": "0.01",
        "positionSide": "LONG",
        "leverage": leverage,
        "isolated": isolated,
        "time": "1788450000000",
    }


def test_hydration_retains_authoritative_leverage_and_margin_mode():
    position = _adapter_with_positions([_position_row()]).get_all_positions()[0]

    assert position.leverage == Decimal("5")
    assert position.isolated is True


def test_malformed_leverage_stays_untrusted_without_breaking_reconciliation():
    rows = [
        _position_row("BTC-USDT", leverage="NaN", isolated="true"),
        _position_row("ETH-USDT", leverage="5", isolated=True),
    ]

    positions = _adapter_with_positions(rows).get_all_positions()

    assert len(positions) == 2
    assert positions[0].leverage is None
    assert positions[0].isolated is None
    assert positions[1].leverage == Decimal("5")
    assert positions[1].isolated is True


def test_non_derivatives_contracts_remain_backward_compatible():
    from domain.entities import ExecutionIntent, Order, OrderSide, Position, PositionSide
    from domain.value_objects import Money, Percentage, Symbol
    from datetime import datetime

    intent = ExecutionIntent(
        symbol=Symbol("BTCUSDT"),
        strategy_name="compat",
        side=OrderSide.BUY,
        intent_confidence=Percentage(Decimal("0.5")),
        risk_parameters={},
        timestamp=datetime.now(),
    )
    order = Order(symbol=Symbol("BTCUSDT"), side=OrderSide.BUY, quantity=Decimal("1"))
    position = Position(
        symbol=Symbol("BTCUSDT"),
        side=PositionSide.LONG,
        quantity=Decimal("1"),
        entry_price=Money(Decimal("100"), "USDT"),
        timestamp=datetime.now(),
    )

    assert intent.requested_leverage is None
    assert order.requested_leverage is None
    assert position.leverage is None and position.isolated is None
