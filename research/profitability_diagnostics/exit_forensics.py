#!/usr/bin/env python3
"""E-P5.2 Priority-1: exit-path root-cause forensics.

Runs representative backtests and dissects every realised (pnl-bearing) trade:
exit_type distribution, SL/TP validity (NaN?), same-bar collisions, MFE/MAE,
realized R, and whether price reached the TP level but the trade still exited a
loss (exit-logic failure). Diagnostic only — no parameter tuning.

Run from repo root:  .venv/bin/python tasks/phase5-evaluate/exit_forensics.py
"""
import logging
import math
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
logging.disable(logging.INFO)

from application.use_cases.run_backtest import BacktestRequest, RunBacktestUseCase
from bootstrap.lifecycle import lifespan
from bootstrap.edge_gate_runner import set_forensic_logging

CASES = [
    ("trend_following", "BTCUSDT", 90),   # adapter (suspected NaN SL/TP)
    ("momentum", "BTCUSDT", 90),          # adapter, high trade count
    ("volatility_breakout", "BTCUSDT", 90),  # function path (real ATR SL/TP)
    ("breakout", "BTCUSDT", 90),          # adapter
]


def _isnan(x):
    try:
        return x is None or math.isnan(float(x))
    except (TypeError, ValueError):
        return x is None


def analyze(strat, trades):
    closed = [t for t in trades if t.get("pnl") is not None]
    if not closed:
        print(f"  {strat}: no pnl-bearing trades"); return
    et = Counter(t.get("exit_type") for t in closed)
    sl_nan = sum(1 for t in closed if _isnan(t.get("stop_loss")))
    tp_nan = sum(1 for t in closed if _isnan(t.get("take_profit")))
    collisions = sum(1 for t in closed if t.get("same_bar_collision"))
    wins = [t for t in closed if t["pnl"] > 0]
    Rs = [t["realized_R"] for t in closed if t.get("realized_R") is not None]
    # MFE/MAE as % of entry
    mfe_pct = [100 * t.get("mfe", 0) / t["entry_price"] for t in closed if t.get("entry_price")]
    mae_pct = [100 * t.get("mae", 0) / t["entry_price"] for t in closed if t.get("entry_price")]
    # did price reach TP level but trade exited non-TP at a loss?
    reached_tp_but_not = 0
    for t in closed:
        tp, ep, mfe = t.get("take_profit"), t.get("entry_price"), t.get("mfe", 0)
        if not _isnan(tp) and ep and t.get("exit_type") != "TP":
            if mfe >= abs(float(tp) - ep):
                reached_tp_but_not += 1
    avg = lambda xs: (sum(xs) / len(xs)) if xs else float("nan")
    print(f"  {strat}: closed={len(closed)} win%={100*len(wins)/len(closed):.1f}")
    print(f"    exit_type: {dict(et)}")
    print(f"    SL NaN: {sl_nan}/{len(closed)}   TP NaN: {tp_nan}/{len(closed)}   same-bar collisions: {collisions}")
    print(f"    mean MFE%={avg(mfe_pct):.3f}  mean MAE%={avg(mae_pct):.3f}")
    print(f"    realized_R: n={len(Rs)} mean={avg(Rs):.3f} (R>0: {sum(1 for r in Rs if r>0)})")
    print(f"    reached-TP-level-but-exited-otherwise: {reached_tp_but_not}/{len(closed)}")


def main():
    set_forensic_logging(False)
    now = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
    print("=== EXIT-PATH FORENSICS (BTCUSDT 90d) ===")
    with lifespan() as c:
        uc = RunBacktestUseCase(
            file_repository=c.resolve("file_repository"),
            backtester_factory=c.resolve("backtester_factory"),
            strategy_provider=c.resolve("backtest_strategy_provider"),
            csv_history_loader=c.resolve("csv_history_loader"),
        )
        for strat, sym, w in CASES:
            try:
                req = BacktestRequest(symbols=[sym], strategy_names=[strat],
                                      start_date=now - timedelta(days=w), end_date=now,
                                      initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0005)
                res = uc.execute(req)
                m = (res.get("backtest_results") or {}).get(sym, {})
                analyze(strat, m.get("trades", []) if isinstance(m, dict) else [])
            except Exception as e:
                print(f"  {strat}: ERROR {e}")
    print("FORENSICS_DONE")


if __name__ == "__main__":
    main()
