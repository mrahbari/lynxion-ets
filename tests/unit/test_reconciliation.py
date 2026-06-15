"""Reconciliation + restart-recovery validation (E11 P3/P4): live engine state vs the
immutable Execution Truth Ledger — detect and repair divergence."""

from decimal import Decimal
from datetime import datetime, timezone

import pytest

from domain.entities import Order, OrderSide, PositionSide
from domain.value_objects import Money, Symbol
from infrastructure.execution.paper_trading_engine import PaperTradingEngine
from infrastructure.execution import reconciliation_service as rec


def _order(side, qty, price, symbol="BTCUSDT"):
    return Order(symbol=Symbol(symbol), side=side, quantity=Decimal(str(qty)),
                 price=Money(Decimal(str(price)), "USDT"), order_type="MARKET",
                 strategy_name="trend_following", timestamp=datetime.now(timezone.utc))


def _fill_and_log(engine, ledger, side, qty, price, symbol="BTCUSDT"):
    """Simulate a fill and append a ledger 'result' record (ETL shape) wrapping it."""
    r = engine.simulate_fill(_order(side, qty, price, symbol))
    ledger.append({"event": "result", "paper_fill": r})
    return r


def test_reconcile_in_sync_after_normal_fills():
    eng = PaperTradingEngine(initial_capital=10000.0)
    ledger = []
    _fill_and_log(eng, ledger, OrderSide.BUY, 2, 100)
    _fill_and_log(eng, ledger, OrderSide.SELL, 1, 120)
    _fill_and_log(eng, ledger, OrderSide.BUY, 1, 90, symbol="ETHUSDT")
    report = rec.reconcile(eng, ledger)
    assert report["in_sync"] is True
    assert report["divergences"] == []
    assert report["fills_replayed"] == 3


def test_reconcile_detects_and_repairs_divergence():
    eng = PaperTradingEngine(initial_capital=10000.0)
    ledger = []
    _fill_and_log(eng, ledger, OrderSide.BUY, 2, 100)
    _fill_and_log(eng, ledger, OrderSide.SELL, 1, 120)

    # Corrupt the live engine's state (simulating drift / persistence bug / tampering).
    eng.positions["BTCUSDT"].quantity = Decimal("5")
    eng.realized_pnl = Decimal("999")

    report = rec.reconcile(eng, ledger)
    assert report["in_sync"] is False
    fields = {d.get("symbol") or d.get("field") for d in report["divergences"]}
    assert "BTCUSDT" in fields and "realized_pnl" in fields

    # Repair rebuilds the live engine from the ledger -> back in sync.
    after = rec.repair(eng, ledger)
    assert after["in_sync"] is True
    assert eng.positions["BTCUSDT"].quantity == Decimal("1")


def test_reconcile_after_restart_recovery(tmp_path):
    p = str(tmp_path / "paper_state.json")
    ledger = []
    e1 = PaperTradingEngine(initial_capital=10000.0, persist_path=p)
    _fill_and_log(e1, ledger, OrderSide.BUY, 2, 100)
    _fill_and_log(e1, ledger, OrderSide.SELL, 1, 120)

    # Restart: a new engine recovers persisted state and must reconcile with the ledger.
    e2 = PaperTradingEngine(persist_path=p)
    report = rec.reconcile(e2, ledger)
    assert report["in_sync"] is True
    assert e2.positions["BTCUSDT"].side == PositionSide.LONG
    assert e2.positions["BTCUSDT"].quantity == Decimal("1")
