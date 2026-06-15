#!/usr/bin/env python3
"""E-P5.3 lifecycle forensics — per-trade capture (run POST baseline-freeze).

Runs backtests for a strategy x symbol x window set and dumps EVERY realised
(pnl-bearing) closed trade with its full lifecycle fields to JSON, for the
lifecycle-forensics analyzer. Does NOT modify the backtester; relies on the
exit-forensics fields already on trade records (entry_price, exit price,
stop_loss, take_profit, mfe, mae, realized_R, exit_type, same_bar_collision,
pnl, regime) plus entry_timestamp/bars_in_trade if present.

Run from repo root:  .venv/bin/python tasks/phase5-profitability/eval_lifecycle_dump.py
"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
logging.disable(logging.INFO)

from application.use_cases.run_backtest import BacktestRequest, RunBacktestUseCase
from bootstrap.lifecycle import lifespan
from bootstrap.edge_gate_runner import set_forensic_logging

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
WINDOWS = [90]   # B7/B8 are STRUCTURAL (placeholder SL/TP + uncalled lifecycle
# logic affect every trade) → identical leak at any horizon; 90d×3sym×12strat
# (~10k trades) is a robust, representative sample that runs cleanly in one pass
# (365d on 1m OOM-crashes; dumper is not resumable). Extend later if needed.
STRATEGIES = [
    "trend_following", "mean_reversion", "momentum", "scalping", "breakout",
    "liquidity", "mtf_trend", "oi_footprint", "sweep_scalper", "vwap_reversal",
    "volatility_breakout", "crypto_breakout",
]
OUT = os.path.join("data", "results_storage", "lifecycle_trades.json")
FIELDS = ("strategy", "symbol", "window", "side", "entry_price", "price",
          "stop_loss", "take_profit", "mfe", "mae", "realized_R", "exit_type",
          "same_bar_collision", "pnl", "regime", "entry_regime", "exit_regime",
          "timestamp", "entry_timestamp", "bars_in_trade")


def main():
    set_forensic_logging(False)
    now = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
    out = []
    with lifespan() as c:
        uc = RunBacktestUseCase(
            file_repository=c.resolve("file_repository"),
            backtester_factory=c.resolve("backtester_factory"),
            strategy_provider=c.resolve("backtest_strategy_provider"),
            csv_history_loader=c.resolve("csv_history_loader"),
        )
        total = len(SYMBOLS) * len(WINDOWS) * len(STRATEGIES); i = 0
        for sym in SYMBOLS:
            for w in WINDOWS:
                for strat in STRATEGIES:
                    i += 1
                    try:
                        res = uc.execute(BacktestRequest(
                            symbols=[sym], strategy_names=[strat],
                            start_date=now - timedelta(days=w), end_date=now,
                            initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0005))
                        m = (res.get("backtest_results") or {}).get(sym, {})
                        trades = m.get("trades", []) if isinstance(m, dict) else []
                        n = 0
                        for t in trades:
                            if t.get("pnl") is None:
                                continue
                            rec = {k: t.get(k) for k in FIELDS}
                            rec["strategy"], rec["symbol"], rec["window"] = strat, sym, w
                            out.append(rec); n += 1
                        print(f"[{i}/{total}] {sym} {w}d {strat}: {n} closed trades", flush=True)
                    except Exception as e:
                        print(f"[{i}/{total}] {sym} {w}d {strat}: ERROR {str(e)[:120]}", flush=True)
                    with open(OUT, "w") as f:
                        json.dump(out, f, default=str)
    print("LIFECYCLE_DUMP_COMPLETE", len(out), "trades ->", OUT)


if __name__ == "__main__":
    main()
