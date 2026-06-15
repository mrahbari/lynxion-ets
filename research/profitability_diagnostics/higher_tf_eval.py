#!/usr/bin/env python3
"""Timeframe-suitability evaluation (Rehab Mode, dimension 9).

Re-runs the SAME production strategies (no code/param/hypothesis change) on
resampled higher-timeframe data to test the Type-C finding that 1m is structurally
cost-incompatible (TP=2.25*ATR << 0.30% round-trip cost on 1m; cost-breakeven ~15m).

Uses BACKTEST_TIMEFRAME env hook -> data/history/raw/<tf>/. Writes a separate output
file per timeframe so it never collides with the canonical 1m eval_matrix.json.

Run:  BACKTEST_TIMEFRAME=1h .venv/bin/python research/profitability_diagnostics/higher_tf_eval.py 1h
"""
import json, logging, os, sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
logging.disable(logging.INFO)

from application.use_cases.run_backtest import BacktestRequest, RunBacktestUseCase
from bootstrap.lifecycle import lifespan
from bootstrap.edge_gate_runner import set_forensic_logging
from infrastructure.results_tracking.edge_ledger import EdgeLedger
from infrastructure.results_tracking.edge_gate import evaluate_edge_gate, EdgeGateThresholds

TF = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BACKTEST_TIMEFRAME", "1h")
os.environ["BACKTEST_TIMEFRAME"] = TF
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
WINDOWS = [90, 180, 365]
STRATEGIES = [
    "trend_following", "mean_reversion", "momentum", "scalping", "breakout",
    "liquidity", "mtf_trend", "oi_footprint", "sweep_scalper", "vwap_reversal",
    "volatility_breakout", "crypto_breakout",
]
OUT = os.path.join("data", "results_storage", f"eval_matrix_{TF}.json")
THRESHOLDS = EdgeGateThresholds()


def _metric(m, *keys):
    for k in keys:
        v = m.get(k)
        if v is not None:
            return v
    return None


def main():
    set_forensic_logging(False)
    now = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
    results = json.load(open(OUT)) if os.path.exists(OUT) else []
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
        for w in WINDOWS:
            for sym in SYMBOLS:
                for strat in STRATEGIES:
                    i += 1
                    if (sym, w, strat) in done:
                        continue
                    rec = {"symbol": sym, "window": w, "strategy": strat, "tf": TF}
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
                                "status": "ok", "verdict": verdict.verdict,
                                "total_return": _metric(m, "total_return"),
                                "sharpe": _metric(m, "sharpe_ratio"),
                                "max_drawdown": _metric(m, "max_drawdown"),
                                "win_rate": _metric(m, "win_rate"),
                                "profit_factor": (None if _metric(m, "profit_factor") == float("inf")
                                                  else _metric(m, "profit_factor")),
                                "closed_trades": attr["total_trades"],
                                "total_pnl": attr["total_pnl"],
                                "by_regime": attr["by_regime"],
                            })
                    except Exception as e:
                        rec["status"] = "error"
                        rec["error"] = str(e)[:200]
                    results.append(rec)
                    done.add((sym, w, strat))
                    with open(OUT, "w") as f:
                        json.dump(results, f, indent=2, default=str)
                    print(f"[{i}/{total}] {TF} {sym} {w}d {strat}: "
                          f"{rec.get('verdict', rec.get('status'))} "
                          f"pnl={rec.get('total_pnl')} trades={rec.get('closed_trades')}")
    print(f"DONE -> {OUT}")


if __name__ == "__main__":
    main()
