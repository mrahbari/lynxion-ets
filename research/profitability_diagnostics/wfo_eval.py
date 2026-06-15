#!/usr/bin/env python3
"""Walk-forward / out-of-sample temporal-stability validation (1h).

The production strategies have NO trainable parameters (no tuning allowed), so
walk-forward here = temporal-stability: does a strategy's edge persist across DISJOINT
out-of-sample time segments? We split the ~1-year 1h history into 4 non-overlapping
~3-month segments and run every strategy on each segment × BTC/ETH/SOL at 1h.

A genuine edge is positive across segments AND symbols. Isolated single-segment /
single-symbol positives are in-sample artifacts.

No tuning, no optimization, no new strategies. Reuses BACKTEST_TIMEFRAME=1h hook.
Run:  BACKTEST_TIMEFRAME=1h .venv/bin/python research/profitability_diagnostics/wfo_eval.py
"""
import json, logging, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
logging.disable(logging.INFO)
os.environ["BACKTEST_TIMEFRAME"] = "1h"

from application.use_cases.run_backtest import BacktestRequest, RunBacktestUseCase
from bootstrap.lifecycle import lifespan
from bootstrap.edge_gate_runner import set_forensic_logging
from infrastructure.results_tracking.edge_ledger import EdgeLedger
from infrastructure.results_tracking.edge_gate import evaluate_edge_gate, EdgeGateThresholds

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
# 4 disjoint OOS segments within the 1h data span (2025-06-11 .. 2026-06-11)
SEGMENTS = [
    ("S1", datetime(2025, 6, 15), datetime(2025, 9, 15)),
    ("S2", datetime(2025, 9, 15), datetime(2025, 12, 15)),
    ("S3", datetime(2025, 12, 15), datetime(2026, 3, 15)),
    ("S4", datetime(2026, 3, 15), datetime(2026, 6, 11)),
]
STRATEGIES = [
    "trend_following", "mean_reversion", "momentum", "scalping", "breakout",
    "liquidity", "mtf_trend", "oi_footprint", "sweep_scalper", "vwap_reversal",
    "volatility_breakout", "crypto_breakout",
]
OUT = os.path.join("data", "results_storage", "wfo_1h.json")
THRESHOLDS = EdgeGateThresholds()


def _m(m, k):
    v = m.get(k)
    return v if v is not None else None


def main():
    set_forensic_logging(False)
    results = json.load(open(OUT)) if os.path.exists(OUT) else []
    done = {(r["symbol"], r["segment"], r["strategy"]) for r in results}
    with lifespan() as container:
        uc = RunBacktestUseCase(
            file_repository=container.resolve("file_repository"),
            backtester_factory=container.resolve("backtester_factory"),
            strategy_provider=container.resolve("backtest_strategy_provider"),
            csv_history_loader=container.resolve("csv_history_loader"),
        )
        total = len(SYMBOLS) * len(SEGMENTS) * len(STRATEGIES)
        i = 0
        for seg, start, end in SEGMENTS:
            for sym in SYMBOLS:
                for strat in STRATEGIES:
                    i += 1
                    if (sym, seg, strat) in done:
                        continue
                    rec = {"symbol": sym, "segment": seg, "strategy": strat,
                           "start": start.date().isoformat(), "end": end.date().isoformat()}
                    try:
                        req = BacktestRequest(
                            symbols=[sym], strategy_names=[strat],
                            start_date=start, end_date=end,
                            initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0005,
                        )
                        res = uc.execute(req)
                        m = (res.get("backtest_results") or {}).get(sym, {})
                        if not isinstance(m, dict) or "error" in m or "trades" not in m:
                            rec["status"] = "error"; rec["error"] = (m or {}).get("error", "no metrics")
                        else:
                            ledger = EdgeLedger(); ledger.update_from_metrics(m, strategy=strat)
                            v = evaluate_edge_gate(ledger.records(), THRESHOLDS)
                            attr = ledger.attribution_report()
                            rec.update({"status": "ok", "verdict": v.verdict,
                                        "total_pnl": attr["total_pnl"], "closed_trades": attr["total_trades"],
                                        "win_rate": _m(m, "win_rate")})
                    except Exception as e:
                        rec["status"] = "error"; rec["error"] = str(e)[:180]
                    results.append(rec); done.add((sym, seg, strat))
                    with open(OUT, "w") as f:
                        json.dump(results, f, indent=2, default=str)
                    print(f"[{i}/{total}] {seg} {sym} {strat}: {rec.get('verdict', rec.get('status'))} "
                          f"pnl={rec.get('total_pnl')} tr={rec.get('closed_trades')}")
    print(f"DONE -> {OUT}")


if __name__ == "__main__":
    main()
