"""Tests for the Paper Trading Engine: fills, slippage/fees, position lifecycle,
realized/unrealized PnL, equity, and persistence/restart recovery."""

from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from domain.entities import Order, OrderSide, PositionSide
from domain.value_objects import Money, Symbol
from infrastructure.execution.paper_trading_engine import PaperTradingEngine


def _order(side, qty, price, symbol="BTCUSDT", strategy="trend_following"):
    return Order(symbol=Symbol(symbol), side=side, quantity=Decimal(str(qty)),
                 price=Money(Decimal(str(price)), "USDT"), order_type="MARKET",
                 strategy_name=strategy, timestamp=datetime.now(timezone.utc))


@pytest.fixture
def eng():
    return PaperTradingEngine(initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0005)


def test_buy_fill_applies_slippage_and_fee(eng):
    r = eng.simulate_fill(_order(OrderSide.BUY, 1, 100))
    assert r["filled"] is True
    assert Decimal(r["fill_price"]) == Decimal("100.05")          # buy slips up 0.05%
    assert Decimal(r["fee"]) == Decimal("100.05") * Decimal("0.001")
    pos = eng.positions["BTCUSDT"]
    assert pos.side == PositionSide.LONG and pos.quantity == Decimal("1")
    assert pos.avg_entry == Decimal("100.05")


def test_unrealized_pnl_marks_to_price(eng):
    eng.simulate_fill(_order(OrderSide.BUY, 2, 100))
    eng.mark_prices({"BTCUSDT": 110})
    snap = eng.snapshot()
    # (110 - 100.05) * 2 = 19.90
    assert Decimal(snap["unrealized_pnl"]) == Decimal("19.90")


def test_partial_then_full_close_books_realized(eng):
    eng.simulate_fill(_order(OrderSide.BUY, 2, 100))         # avg 100.05
    r1 = eng.simulate_fill(_order(OrderSide.SELL, 1, 120))   # sell fills 120*(1-0.0005)=119.94
    # realized on 1 unit = 119.94 - 100.05 = 19.89
    assert Decimal(r1["realized_pnl_delta"]) == Decimal("19.89")
    assert eng.positions["BTCUSDT"].quantity == Decimal("1")
    r2 = eng.simulate_fill(_order(OrderSide.SELL, 1, 120))
    assert Decimal(r2["realized_pnl_delta"]) == Decimal("19.89")
    assert eng.positions["BTCUSDT"].side == PositionSide.FLAT
    assert eng.realized_pnl == Decimal("39.78")
    assert len(eng.closed_trades) == 2


def test_flip_long_to_short(eng):
    eng.simulate_fill(_order(OrderSide.BUY, 1, 100))         # long 1 @100.05
    r = eng.simulate_fill(_order(OrderSide.SELL, 3, 100))    # sell 3 -> close 1, open short 2
    pos = eng.positions["BTCUSDT"]
    assert pos.side == PositionSide.SHORT and pos.quantity == Decimal("2")
    # short opened at the sell fill price 99.95
    assert pos.avg_entry == Decimal("99.95")
    # realized on the closed long unit = 99.95 - 100.05 = -0.10
    assert Decimal(r["realized_pnl_delta"]) == Decimal("-0.10")


def test_short_pnl(eng):
    eng.simulate_fill(_order(OrderSide.SELL, 1, 100))        # short @ 99.95
    r = eng.simulate_fill(_order(OrderSide.BUY, 1, 90))      # cover @ 90.045
    # realized short = entry - exit = 99.95 - 90.045 = 9.905
    assert Decimal(r["realized_pnl_delta"]) == Decimal("9.905")
    assert eng.positions["BTCUSDT"].side == PositionSide.FLAT


def test_equity_identity(eng):
    eng.simulate_fill(_order(OrderSide.BUY, 1, 100))
    eng.simulate_fill(_order(OrderSide.SELL, 1, 120))
    eng.mark_prices({"BTCUSDT": 0})  # flat -> no unrealized
    snap = eng.snapshot()
    # equity = initial + realized - fees  (flat)
    expected = (Decimal("10000") + eng.realized_pnl - eng.total_fees)
    assert Decimal(snap["equity"]) == expected
    assert Decimal(snap["cash"]) == expected


def test_rejects_nonpositive(eng):
    r = eng.simulate_fill(_order(OrderSide.BUY, 0, 100))
    assert r["filled"] is False


def test_persistence_and_restart_recovery(tmp_path):
    p = str(tmp_path / "paper_state.json")
    e1 = PaperTradingEngine(initial_capital=10000.0, persist_path=p)
    e1.simulate_fill(_order(OrderSide.BUY, 2, 100))
    e1.simulate_fill(_order(OrderSide.SELL, 1, 120))
    realized_before = e1.realized_pnl
    pos_before = e1.positions["BTCUSDT"].quantity

    # New engine loads from disk -> state recovered (restart recovery)
    e2 = PaperTradingEngine(persist_path=p)
    assert e2.realized_pnl == realized_before
    assert e2.positions["BTCUSDT"].quantity == pos_before
    assert e2.positions["BTCUSDT"].side == PositionSide.LONG
    # continuing on the recovered engine keeps booking correctly
    r = e2.simulate_fill(_order(OrderSide.SELL, 1, 120))
    assert e2.positions["BTCUSDT"].side == PositionSide.FLAT
    assert Decimal(r["cumulative_realized_pnl"]) == e2.realized_pnl
