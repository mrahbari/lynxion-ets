"""Reconciliation service (E11, Priority 4).

Compares the live position store (PaperTradingEngine — the local "broker state") against
an independent reconstruction from the immutable Execution Truth Ledger (the source of
truth for what was actually filled). Detects divergence per symbol and in realized PnL,
and can repair the live engine by rebuilding it from the ledger.

In paper mode the ETL is authoritative (it records every fill before/at execution); the
same mechanism extends to live trading by replaying broker-reported fills. Reconciliation
catches persistence corruption, dropped writes, or tampering (the ledger is hash-chained).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from domain.enums.position_side import PositionSide
from infrastructure.execution.paper_trading_engine import PaperTradingEngine

_TOL = Decimal("0.00000001")


def rebuild_from_ledger(records: List[Dict], initial_capital=10000.0,
                        fee_rate=0.001, slippage_factor=0.0005) -> PaperTradingEngine:
    """Replay the ledger's PAPER fills into a fresh engine (no persistence) -> expected state."""
    rebuilt = PaperTradingEngine(initial_capital=initial_capital, fee_rate=fee_rate,
                                 slippage_factor=slippage_factor, persist_path=None)
    for rec in records:
        if rec.get("event") != "result":
            continue
        pf = rec.get("paper_fill")
        if not (isinstance(pf, dict) and pf.get("filled")):
            continue
        rebuilt.replay_fill(pf["symbol"], pf["side"], pf["quantity"], pf["fill_price"],
                            pf.get("fee", 0))
    return rebuilt


def _positions_map(engine: PaperTradingEngine) -> Dict[str, Dict[str, str]]:
    out = {}
    for sym, p in engine.positions.items():
        if p.side != PositionSide.FLAT and p.quantity > 0:
            out[sym] = {"side": p.side.value, "quantity": str(p.quantity), "avg_entry": str(p.avg_entry)}
    return out


def reconcile(live_engine: PaperTradingEngine, ledger_records: List[Dict],
              initial_capital: Optional[float] = None) -> Dict[str, Any]:
    """Compare live engine state vs ledger reconstruction. Returns a divergence report."""
    cap = float(live_engine.initial_capital) if initial_capital is None else initial_capital
    expected = rebuild_from_ledger(ledger_records, initial_capital=cap,
                                   fee_rate=float(live_engine.fee_rate),
                                   slippage_factor=float(live_engine.slippage_factor))
    live_pos = _positions_map(live_engine)
    exp_pos = _positions_map(expected)

    divergences: List[Dict[str, Any]] = []
    for sym in set(live_pos) | set(exp_pos):
        lv, ev = live_pos.get(sym), exp_pos.get(sym)
        if lv != ev:
            divergences.append({"symbol": sym, "live": lv, "ledger": ev})

    realized_div = abs(live_engine.realized_pnl - expected.realized_pnl) > _TOL
    if realized_div:
        divergences.append({"field": "realized_pnl",
                            "live": str(live_engine.realized_pnl),
                            "ledger": str(expected.realized_pnl)})

    return {
        "in_sync": not divergences,
        "divergences": divergences,
        "live_positions": live_pos,
        "ledger_positions": exp_pos,
        "live_realized_pnl": str(live_engine.realized_pnl),
        "ledger_realized_pnl": str(expected.realized_pnl),
        "fills_replayed": len(expected.fills) if expected.fills else
                          sum(1 for r in ledger_records if r.get("event") == "result"
                              and isinstance(r.get("paper_fill"), dict) and r["paper_fill"].get("filled")),
    }


def repair(live_engine: PaperTradingEngine, ledger_records: List[Dict]) -> Dict[str, Any]:
    """Repair the live engine in place by rebuilding its position/PnL state from the ledger."""
    expected = rebuild_from_ledger(ledger_records, initial_capital=float(live_engine.initial_capital),
                                   fee_rate=float(live_engine.fee_rate),
                                   slippage_factor=float(live_engine.slippage_factor))
    with live_engine._lock:
        live_engine.positions = expected.positions
        live_engine.realized_pnl = expected.realized_pnl
        live_engine.total_fees = expected.total_fees
        live_engine.closed_trades = expected.closed_trades
        live_engine._save()
    return reconcile(live_engine, ledger_records)


__all__ = ["reconcile", "repair", "rebuild_from_ledger"]
