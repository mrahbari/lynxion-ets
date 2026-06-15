"""Strategy Deployment Re-validation (analysis only; NO tuning / NO logic changes).

Re-evaluates each surviving production strategy in its INTENDED deployment environment:
  * its DESIGN timeframe (via StrategyConfig.get_strategy_timeframe — Phase-A routing fix),
  * PER-SYMBOL (BTC / ETH / SOL evaluated independently — never pooled),
  * REGIME-CONDITIONED (expectancy restricted to the strategy's intended regime),
  * with realistic round-trip cost (existing backtest fee+slippage params, unchanged).

Metric: net forward-return expectancy per actionable signal (signal-quality WITH cost) at a
holding horizon matched to the design timeframe — an assumption-light proxy that needs no
per-strategy SL/TP simulation and no tuned parameters. Cross-period stability = sign agreement
across the first vs second half of the window. This measures whether a directional edge SURVIVES
in the intended environment; it is not a path-dependent P&L backtest.

Run: .venv/bin/python scripts/strategy_deployment_revalidation.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import logging
logging.disable(logging.WARNING)

from domain.value_objects import Symbol
from infrastructure.strategies.strategy_config import StrategyConfig

# Existing production cost params (application/configs/schemas/backtest.py) — UNCHANGED.
FEE_RATE = 0.001
SLIPPAGE = 0.0005
ROUND_TRIP_COST = 2 * (FEE_RATE + SLIPPAGE)   # 0.30%

SYMBOLS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]

# Intended regime per strategy (from strategy_architecture_review.md / code regime gates).
INTENDED_REGIME = {
    "trend_following": {"trending_up", "trending_down"},
    "momentum": {"trending_up", "trending_down"},
    "mtf_trend": {"trending_up", "trending_down"},
    "mean_reversion": {"ranging"},
    "vwap_reversal": {"ranging"},
    "liquidity": {"ranging"},
    "breakout": {"breakout"},
    "volatility_breakout": {"breakout"},
    "sweep_scalper": {"breakout"},
    "scalping": {"breakout", "ranging"},
}
# Holding horizon (bars) ~ intended holding period, by design timeframe.
HORIZON_BY_TF = {"1m": 15, "5m": 12, "15m": 8, "30m": 6, "1h": 6}
MAX_BARS = {"1m": 40000, "5m": 30000, "15m": 35000, "30m": 30000, "1h": 8700}

# Strategies whose CORE mechanism is stubbed/absent (architecture review) — kept INVALIDATED.
INVALIDATED_AS_IMPLEMENTED = {"mtf_trend", "oi_footprint", "sweep_scalper"}
SURVIVING = ["trend_following", "mean_reversion", "momentum", "breakout", "liquidity",
             "mtf_trend", "oi_footprint", "sweep_scalper", "vwap_reversal", "volatility_breakout"]


def _adapter(name):
    from infrastructure.strategies.adapters.trend_follow_strategy_adapter import TrendFollowStrategyAdapter
    from infrastructure.strategies.adapters.mean_reversion_strategy_adapter import MeanReversionStrategyAdapter
    from infrastructure.strategies.adapters.breakout_strategy_adapter import BreakoutStrategyAdapter
    from infrastructure.strategies.adapters.liquidity_strategy_adapter import LiquidityStrategyAdapter
    from infrastructure.strategies.adapters.vwap_reversal_strategy_adapter import VWAPReversalStrategyAdapter
    from infrastructure.strategies.adapters.momentum_strategy_adapter import MomentumStrategyAdapter
    from infrastructure.strategies.adapters.mtf_trend_strategy_adapter import MTFTrendStrategyAdapter
    from infrastructure.strategies.adapters.oi_footprint_strategy_adapter import OIFootprintStrategyAdapter
    from infrastructure.strategies.adapters.sweep_scalper_strategy_adapter import SweepScalperAdapter
    from infrastructure.strategies.strategy_adapters import VolatilityBreakoutStrategy
    m = {"trend_following": TrendFollowStrategyAdapter, "mean_reversion": MeanReversionStrategyAdapter,
         "breakout": BreakoutStrategyAdapter, "liquidity": LiquidityStrategyAdapter,
         "vwap_reversal": VWAPReversalStrategyAdapter, "momentum": MomentumStrategyAdapter,
         "mtf_trend": MTFTrendStrategyAdapter, "oi_footprint": OIFootprintStrategyAdapter,
         "sweep_scalper": SweepScalperAdapter, "volatility_breakout": VolatilityBreakoutStrategy}
    return m[name]({})


def _label_regimes(df: pd.DataFrame) -> list:
    """Transparent, lookahead-safe per-bar regime labels (trend/range/breakout)."""
    close = df["close"].values
    sma20 = pd.Series(close).rolling(20).mean().values
    sma50 = pd.Series(close).rolling(50).mean().values
    atr = (df["high"] - df["low"]).rolling(14).mean().values
    atr_med = pd.Series(atr).rolling(100).median().values
    out = []
    for i in range(len(close)):
        if np.isnan(sma20[i]) or np.isnan(sma50[i]):
            out.append("unknown"); continue
        # breakout regime = current range materially above its median (volatility expansion)
        if not np.isnan(atr_med[i]) and atr_med[i] > 0 and atr[i] > 1.6 * atr_med[i]:
            out.append("breakout")
        elif sma20[i] > sma50[i] and close[i] > sma20[i]:
            out.append("trending_up")
        elif sma20[i] < sma50[i] and close[i] < sma20[i]:
            out.append("trending_down")
        else:
            out.append("ranging")
    return out


def evaluate(name, symbol):
    tf = StrategyConfig.get_strategy_timeframe(name, "1h")
    path = os.path.join("data", "history", "raw", tf, f"{symbol}.csv")
    if not os.path.exists(path):
        return {"error": f"no data {path}"}
    df = pd.read_csv(path).tail(MAX_BARS.get(tf, 30000)).reset_index(drop=True)
    if len(df) < 300:
        return {"error": "insufficient data"}
    regimes = _label_regimes(df)
    horizon = HORIZON_BY_TF.get(tf, 6)
    close = df["close"].values
    bars = [{"open": r.open, "high": r.high, "low": r.low, "close": r.close,
             "volume": r.volume, "timestamp": int(r.timestamp)} for r in df.itertuples()]
    sym = Symbol(symbol.replace("-", ""))
    adapter = _adapter(name)

    signals = []  # (bar_index, side, regime)
    for i, b in enumerate(bars):
        try:
            adapter.update_with_market_data(b)
            sig = adapter.generate_signal(sym)
        except Exception:
            sig = None
        if sig is None:
            continue
        st = getattr(getattr(sig, "signal_type", None), "name", "") or ""
        st = st.upper()
        side = 1 if ("BUY" in st or "LONG" in st) else (-1 if ("SELL" in st or "SHORT" in st) else 0)
        if side != 0 and i + horizon < len(close):
            signals.append((i, side, regimes[i]))

    def net_ret(i, side):
        fwd = (close[i + horizon] - close[i]) / close[i]
        return side * fwd - ROUND_TRIP_COST

    all_rets = [net_ret(i, s) for (i, s, _) in signals]
    intended = INTENDED_REGIME.get(name, set())
    in_rets = [net_ret(i, s) for (i, s, rg) in signals if rg in intended]
    # cross-period stability on in-regime signals (split by bar index midpoint)
    mid = len(df) // 2
    h1 = [net_ret(i, s) for (i, s, rg) in signals if rg in intended and i < mid]
    h2 = [net_ret(i, s) for (i, s, rg) in signals if rg in intended and i >= mid]
    regime_cov = Counter(rg for (_, _, rg) in signals)

    def stats(r):
        if not r:
            return {"n": 0, "expectancy": None, "win_rate": None}
        a = np.array(r)
        return {"n": len(a), "expectancy": float(a.mean()), "win_rate": float((a > 0).mean())}

    return {
        "timeframe": tf, "bars": len(df), "horizon": horizon,
        "signals_total": len(signals),
        "all": stats(all_rets),
        "in_regime": stats(in_rets),
        "half1_in_regime": stats(h1), "half2_in_regime": stats(h2),
        "regime_coverage": dict(regime_cov),
    }


def main():
    results = {}
    for name in SURVIVING:
        results[name] = {"intended_regime": sorted(INTENDED_REGIME.get(name, [])),
                         "invalidated_as_implemented": name in INVALIDATED_AS_IMPLEMENTED,
                         "symbols": {}}
        for sym in SYMBOLS:
            try:
                results[name]["symbols"][sym] = evaluate(name, sym)
            except Exception as e:
                results[name]["symbols"][sym] = {"error": str(e)}
        # progress to stderr
        print(f"done {name}", file=sys.stderr)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
