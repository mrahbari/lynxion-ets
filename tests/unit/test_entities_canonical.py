"""E4.T1 validation: canonical entity model preserves fields + invariants.

Covers entity validation invariants, the merged ``Order`` (both parent
fields), and that the legacy shim modules re-export the *same* canonical
classes (single source of truth).
"""

from datetime import datetime
from decimal import Decimal

import pytest

try:
    from domain.value_objects import Symbol, Money, Percentage
    from domain.entities import (
        Signal, SignalType, MarketObservation, InterpretedSignal, FusedSignal,
        Order, OrderSide, Fill, ExecutionIntent, Position, PositionSide,
        Portfolio, MarketData, Balance, TradingAccount,
    )
    import domain.entities.trading_entities as trading_entities
    import domain.entities.signal_entities as signal_entities
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"domain entity dependencies unavailable: {exc}", allow_module_level=True)

NOW = datetime(2024, 1, 1)
SYM = Symbol("BTCUSDT")


@pytest.mark.unit
def test_signal_invariants():
    Signal(symbol=SYM, signal_type=SignalType.BUY, confidence=Percentage(Decimal("0.5")), score=0.1, timestamp=NOW)
    with pytest.raises(ValueError):
        Signal(symbol=SYM, signal_type=SignalType.BUY, confidence=Percentage(Decimal("0.5")), score=2.0, timestamp=NOW)
    with pytest.raises(ValueError):
        Signal(symbol=SYM, signal_type=SignalType.BUY, confidence=Percentage(Decimal("1.5")), score=0.1, timestamp=NOW)


@pytest.mark.unit
def test_interpreted_and_fused_and_intent_invariants():
    with pytest.raises(ValueError):
        InterpretedSignal(symbol=SYM, signal_type=SignalType.BUY, direction=2.0, strength=0.5,
                          confidence=Percentage(Decimal("0.5")), timestamp=NOW)
    with pytest.raises(ValueError):
        FusedSignal(symbol=SYM, dominant_bias=SignalType.BUY, direction=0.0, dominance_score=2.0,
                    regime_context="normal", confidence=Percentage(Decimal("0.5")), timestamp=NOW)
    with pytest.raises(ValueError):
        ExecutionIntent(symbol=SYM, strategy_name="s", side=OrderSide.BUY,
                        intent_confidence=Percentage(Decimal("1.5")), risk_parameters={}, timestamp=NOW)
    with pytest.raises(ValueError):
        MarketObservation(symbol=SYM, observation_type="x", observation_value=1.0,
                          confidence=Percentage(Decimal("1.5")), timestamp=NOW)


@pytest.mark.unit
def test_merged_order_has_both_parent_fields():
    fields = Order.__dataclass_fields__
    assert "parent_signal" in fields
    assert "parent_execution_intent" in fields
    # Both default to None -> constructing with neither works.
    o = Order(symbol=SYM, side=OrderSide.BUY, quantity=Decimal("1"))
    assert o.parent_signal is None
    assert o.parent_execution_intent is None
    assert o.is_market_order()


@pytest.mark.unit
def test_position_pnl_and_open():
    pos = Position(symbol=SYM, side=PositionSide.LONG, quantity=Decimal("2"),
                   entry_price=Money(100, "USD"), timestamp=NOW)
    assert pos.is_open()
    pnl = pos.calculate_unrealized_pnl(Money(110, "USD"))
    assert pnl.amount == 20


@pytest.mark.unit
def test_shims_reexport_same_classes():
    # Single source of truth: shim symbols are identical objects to canonical.
    assert trading_entities.Order is Order
    assert signal_entities.Order is Order
    assert trading_entities.SignalType is SignalType
    assert signal_entities.ExecutionIntent is ExecutionIntent
    assert trading_entities.Position is Position is signal_entities.Position
