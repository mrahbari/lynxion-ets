#!/usr/bin/env python3
"""E-P5.2 multi-window / multi-symbol strategy evaluation matrix.

For each (symbol, window, strategy) runs the backtest (Option-A per-strategy
signals, realistic fills, time-aware discipline), captures full metrics
(expectancy/PF/win-rate/sharpe/sortino/max-DD + per-regime edge), and the edge
gate verdict. Writes results incrementally to JSON so a long run is resumable
and partial progress is usable.

Run from repo root:  .venv/bin/python tasks/phase5-evaluate/eval_matrix.py
"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Quiet per-bar logging + forensic (irrelevant to offline edge measurement; dominate runtime).
logging.disable(logging.INFO)

from application.use_cases.run_backtest import BacktestRequest, RunBacktestUseCase
from bootstrap.lifecycle import lifespan
from bootstrap.edge_gate_runner import set_forensic_logging
from infrastructure.results_tracking.edge_ledger import EdgeLedger
from infrastructure.results_tracking.edge_gate import evaluate_edge_gate, EdgeGateThresholds

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
WINDOWS = [90, 180, 365]
STRATEGIES = [
    "trend_following", "mean_reversion", "momentum", "scalping", "breakout",
    "liquidity", "mtf_trend", "oi_footprint", "sweep_scalper", "vwap_reversal",
    "volatility_breakout", "crypto_breakout",
]
OUT = os.path.join("data", "results_storage", "eval_matrix.json")
THRESHOLDS = EdgeGateThresholds()  # defaults: min_trades 30, exp>0, PF>1


def _metric(m, *keys):
    for k in keys:
        if k in m:
            return m[k]
    return None


def main():
    set_forensic_logging(False)
    now = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
    results = []
    if os.path.exists(OUT):
        try:
            results = json.load(open(OUT))
        except Exception:
            results = []
    done = {(r["symbol"], r["window"], r["strategy"]) for r in results}

    with lifespan() as container:
        uc = RunBacktestUseCase(
            file_repository=container.resolve("file_repository"),
            backtester_factory=container.resolve("backtester_factory"),
            strategy_provider=container.resolve("backtest_strategy_provider"),
            csv_history_loader=container.resolve("csv_history_loader"),
        )
        total = len(SYMBOLS) * len(WINDOWS) * len(STRATEGIES)
        i = 0
        for w in WINDOWS:  # window-outermost: 90d completes across all symbols first (feasible baseline)
            for sym in SYMBOLS:
                for strat in STRATEGIES:
                    i += 1
                    if (sym, w, strat) in done:
                        continue
                    rec = {"symbol": sym, "window": w, "strategy": strat}
                    try:
                        req = BacktestRequest(
                            symbols=[sym], strategy_names=[strat],
                            start_date=now - timedelta(days=w), end_date=now,
                            initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0005,
                        )
                        res = uc.execute(req)
                        m = (res.get("backtest_results") or {}).get(sym, {})
                        if not isinstance(m, dict) or "error" in m or "trades" not in m:
                            rec["status"] = "error"
                            rec["error"] = (m or {}).get("error", "no metrics")
                        else:
                            ledger = EdgeLedger()
                            ledger.update_from_metrics(m, strategy=strat)
                            verdict = evaluate_edge_gate(ledger.records(), THRESHOLDS)
                            attr = ledger.attribution_report()
                            rec.update({
                                "status": "ok",
                                "verdict": verdict.verdict,
                                "total_return": _metric(m, "total_return"),
                                "sharpe": _metric(m, "sharpe_ratio"),
                                "sortino": _metric(m, "sortino_ratio"),
                                "max_drawdown": _metric(m, "max_drawdown"),
                                "win_rate": _metric(m, "win_rate"),
                                "profit_factor": (None if _metric(m, "profit_factor") == float("inf")
                                                  else _metric(m, "profit_factor")),
                                "total_trades_raw": _metric(m, "total_trades"),
                                "closed_trades": attr["total_trades"],
                                "total_pnl": attr["total_pnl"],
                                "total_fees": _metric(m, "total_fees"),
                                "by_regime": attr["by_regime"],
                                "cells": [{"regime": r.regime, "trades": r.trade_count,
                                           "expectancy": r.expectancy, "win_rate": r.win_rate,
                                           "avg_rr": r.avg_rr,
                                           "profit_factor": (None if r.profit_factor == float("inf")
                                                             else r.profit_factor)}
                                          for r in ledger.records()],
                            })
                    except Exception as e:
                        rec["status"] = "error"
                        rec["error"] = str(e)[:200]
                    results.append(rec)
                    done.add((sym, w, strat))
                    # incremental write
                    with open(OUT, "w") as f:
                        json.dump(results, f, indent=2, default=str)
                    print(f"[{i}/{total}] {sym} {w}d {strat}: "
                          f"{rec.get('verdict', rec.get('status'))} "
                          f"pnl={rec.get('total_pnl')} sharpe={rec.get('sharpe')}", flush=True)
    print("EVAL_MATRIX_COMPLETE", len(results), "records ->", OUT)


if __name__ == "__main__":
    main()
