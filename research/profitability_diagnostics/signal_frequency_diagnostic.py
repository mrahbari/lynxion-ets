"""Signal-frequency diagnostic (Strategy Fidelity & Remediation).

Feeds real BTC 1m bars to each strategy's REAL generate_signal() and counts
BUY/SELL/HOLD/None outcomes — the fast 'measure/diagnose' step for remediation
(no execution layer). A strategy producing ~0 BUY/SELL is signal-starved; the
cause (impossible threshold, choppy filter, never-aligning indicators) is then
read from its generate_signal. No execution, no optimization.

Run from repo root:
    .venv/bin/python3 research/profitability_diagnostics/signal_frequency_diagnostic.py [n_bars] [strat,strat,...]
"""
from __future__ import annotations

import os
import sys
from collections import Counter

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
import logging
logging.disable(logging.WARNING)

from domain.value_objects import Symbol  # noqa: E402
from infrastructure.backtest.strategy_provider import load_sample_strategy  # noqa: E402

ALL = ["trend_following", "mean_reversion", "momentum", "breakout", "crypto_breakout",
       "scalping", "liquidity", "mtf_trend", "oi_footprint", "vwap_reversal",
       "sweep_scalper", "volatility_breakout"]


def _adapter(name):
    # mirror load_sample_strategy's adapter map to get the raw adapter instance
    from infrastructure.strategies.adapters.trend_follow_strategy_adapter import TrendFollowStrategyAdapter
    from infrastructure.strategies.adapters.mean_reversion_strategy_adapter import MeanReversionStrategyAdapter
    from infrastructure.strategies.adapters.scalping_strategy_adapter import ScalpingStrategyAdapter
    from infrastructure.strategies.adapters.breakout_strategy_adapter import BreakoutStrategyAdapter
    from infrastructure.strategies.adapters.liquidity_strategy_adapter import LiquidityStrategyAdapter
    from infrastructure.strategies.adapters.vwap_reversal_strategy_adapter import VWAPReversalStrategyAdapter
    from infrastructure.strategies.adapters.momentum_strategy_adapter import MomentumStrategyAdapter
    from infrastructure.strategies.adapters.mtf_trend_strategy_adapter import MTFTrendStrategyAdapter
    from infrastructure.strategies.adapters.oi_footprint_strategy_adapter import OIFootprintStrategyAdapter
    from infrastructure.strategies.adapters.sweep_scalper_strategy_adapter import SweepScalperAdapter
    from infrastructure.strategies.strategy_adapters import VolatilityBreakoutStrategy
    m = {"trend_following": TrendFollowStrategyAdapter, "mean_reversion": MeanReversionStrategyAdapter,
         "scalping": ScalpingStrategyAdapter, "breakout": BreakoutStrategyAdapter,
         "crypto_breakout": BreakoutStrategyAdapter, "liquidity": LiquidityStrategyAdapter,
         "vwap_reversal": VWAPReversalStrategyAdapter, "momentum": MomentumStrategyAdapter,
         "mtf_trend": MTFTrendStrategyAdapter, "oi_footprint": OIFootprintStrategyAdapter,
         "sweep_scalper": SweepScalperAdapter, "volatility_breakout": VolatilityBreakoutStrategy}
    return m[name]({})


def main():
    n_bars = int(sys.argv[1]) if len(sys.argv) > 1 else 45000
    df = pd.read_csv(os.path.join("data", "history", "raw", "1m", "BTC-USDT.csv"))
    df = df.tail(n_bars).reset_index(drop=True)
    bars = [{"open": r.open, "high": r.high, "low": r.low, "close": r.close,
             "volume": r.volume, "timestamp": int(r.timestamp)} for r in df.itertuples()]
    sym = Symbol("BTCUSDT")
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else ALL
    print(f"=== signal-frequency over {len(bars)} BTC 1m bars ===")
    for name in names:
        a = _adapter(name)
        c = Counter()
        for b in bars:
            a.update_with_market_data(b)
            sig = a.generate_signal(sym)
            if sig is None:
                c["None"] += 1
                continue
            st = getattr(getattr(sig, "signal_type", None), "name", "?").upper()
            if "BUY" in st or "LONG" in st:
                c["BUY"] += 1
            elif "SELL" in st or "SHORT" in st:
                c["SELL"] += 1
            else:
                c["HOLD"] += 1
        actionable = c["BUY"] + c["SELL"]
        print(f"{name:18}: actionable={actionable:6d} (BUY={c['BUY']} SELL={c['SELL']}) "
              f"HOLD={c['HOLD']} None={c['None']}  -> {'STARVED' if actionable == 0 else 'fires'}")


def strat_sym(x):
    return f"{x}-USDT"


if __name__ == "__main__":
    main()
