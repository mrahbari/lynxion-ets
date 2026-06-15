"""Phase 15 — Long-History Validation (analysis only; NO tuning / NO logic changes).

Re-evaluates the 5 strategies that showed ANY positive evidence, on the LONGEST available
history for the symbols that showed positive/partial-positive behavior. Same evaluation
contract as scripts/strategy_deployment_revalidation.py (design-TF, per-symbol, regime-
conditioned, cost-adjusted net forward-return expectancy per actionable signal), PLUS a
4-fold walk-forward (sequential) on the in-regime signals.

The question: do XRP/DOGE/LINK positives persist across multi-year history or collapse, and
does longer coverage change the READY=0 verdict? No strategy logic / thresholds / params /
risk / execution touched.

Run: .venv/bin/python scripts/phase15_long_history_validation.py
"""
from __future__ import annotations
import json, os, sys
from collections import Counter
import numpy as np, pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import logging; logging.disable(logging.WARNING)

from domain.value_objects import Symbol
from infrastructure.strategies.strategy_config import StrategyConfig

# Existing production cost params — UNCHANGED.
FEE_RATE = 0.001; SLIPPAGE = 0.0005
ROUND_TRIP_COST = 2 * (FEE_RATE + SLIPPAGE)   # 0.30%

SYMBOLS = ["XRP-USDT", "DOGE-USDT", "LINK-USDT", "BTC-USDT", "ETH-USDT"]
STRATEGIES = ["trend_following", "momentum", "oi_footprint", "mean_reversion", "vwap_reversal"]

INTENDED_REGIME = {
    "trend_following": {"trending_up", "trending_down"},
    "momentum": {"trending_up", "trending_down"},
    "oi_footprint": {"trending_up", "trending_down", "breakout"},  # vol-spike/momentum as-implemented
    "mean_reversion": {"ranging"},
    "vwap_reversal": {"ranging"},
}
HORIZON_BY_TF = {"1m": 15, "5m": 12, "15m": 8, "30m": 6, "1h": 6}
# Use ALL available history (longest coverage is the whole point of this phase).
MAX_BARS = {"1m": 10_000_000, "5m": 10_000_000, "15m": 10_000_000, "30m": 10_000_000, "1h": 10_000_000}
WFO_FOLDS = 4


def _adapter(name):
    from infrastructure.strategies.adapters.trend_follow_strategy_adapter import TrendFollowStrategyAdapter
    from infrastructure.strategies.adapters.mean_reversion_strategy_adapter import MeanReversionStrategyAdapter
    from infrastructure.strategies.adapters.vwap_reversal_strategy_adapter import VWAPReversalStrategyAdapter
    from infrastructure.strategies.adapters.momentum_strategy_adapter import MomentumStrategyAdapter
    from infrastructure.strategies.adapters.oi_footprint_strategy_adapter import OIFootprintStrategyAdapter
    m = {"trend_following": TrendFollowStrategyAdapter, "mean_reversion": MeanReversionStrategyAdapter,
         "vwap_reversal": VWAPReversalStrategyAdapter, "momentum": MomentumStrategyAdapter,
         "oi_footprint": OIFootprintStrategyAdapter}
    return m[name]({})


def _label_regimes(df: pd.DataFrame) -> list:
    close = df["close"].values
    sma20 = pd.Series(close).rolling(20).mean().values
    sma50 = pd.Series(close).rolling(50).mean().values
    atr = (df["high"] - df["low"]).rolling(14).mean().values
    atr_med = pd.Series(atr).rolling(100).median().values
    out = []
    for i in range(len(close)):
        if np.isnan(sma20[i]) or np.isnan(sma50[i]):
            out.append("unknown"); continue
        if not np.isnan(atr_med[i]) and atr_med[i] > 0 and atr[i] > 1.6 * atr_med[i]:
            out.append("breakout")
        elif sma20[i] > sma50[i] and close[i] > sma20[i]:
            out.append("trending_up")
        elif sma20[i] < sma50[i] and close[i] < sma20[i]:
            out.append("trending_down")
        else:
            out.append("ranging")
    return out


def _stats(r):
    if len(r) < 1:
        return {"n": 0, "expectancy": None, "win_rate": None}
    a = np.array(r)
    return {"n": len(a), "expectancy": float(a.mean()), "win_rate": float((a > 0).mean())}


def evaluate(name, symbol):
    tf = StrategyConfig.get_strategy_timeframe(name, "1h")
    path = os.path.join("data", "history", "raw", tf, f"{symbol}.csv")
    if not os.path.exists(path):
        return {"error": f"no data {path}", "timeframe": tf}
    df = pd.read_csv(path).tail(MAX_BARS.get(tf, 10_000_000)).reset_index(drop=True)
    if len(df) < 300:
        return {"error": f"insufficient data ({len(df)})", "timeframe": tf}
    regimes = _label_regimes(df)
    horizon = HORIZON_BY_TF.get(tf, 6)
    close = df["close"].values
    span = (f"{pd.to_datetime(df.timestamp.min(),unit='s').date()}"
            f"->{pd.to_datetime(df.timestamp.max(),unit='s').date()}")
    bars = [{"open": r.open, "high": r.high, "low": r.low, "close": r.close,
             "volume": r.volume, "timestamp": int(r.timestamp)} for r in df.itertuples()]
    sym = Symbol(symbol.replace("-", ""))
    adapter = _adapter(name)

    signals = []
    for i, b in enumerate(bars):
        try:
            adapter.update_with_market_data(b)
            sig = adapter.generate_signal(sym)
        except Exception:
            sig = None
        if sig is None:
            continue
        st = (getattr(getattr(sig, "signal_type", None), "name", "") or "").upper()
        side = 1 if ("BUY" in st or "LONG" in st) else (-1 if ("SELL" in st or "SHORT" in st) else 0)
        if side != 0 and i + horizon < len(close):
            signals.append((i, side, regimes[i]))

    def net_ret(i, side):
        return side * ((close[i + horizon] - close[i]) / close[i]) - ROUND_TRIP_COST

    intended = INTENDED_REGIME.get(name, set())
    all_rets = [net_ret(i, s) for (i, s, _) in signals]
    in_sig = [(i, s) for (i, s, rg) in signals if rg in intended]
    in_rets = [net_ret(i, s) for (i, s) in in_sig]

    # 4-fold walk-forward on in-regime signals, split by bar index into equal calendar quarters
    nbars = len(df)
    fold_bounds = [(k * nbars // WFO_FOLDS, (k + 1) * nbars // WFO_FOLDS) for k in range(WFO_FOLDS)]
    wfo = []
    for (a, bnd) in fold_bounds:
        fr = [net_ret(i, s) for (i, s) in in_sig if a <= i < bnd]
        wfo.append(_stats(fr))
    fold_exp = [f["expectancy"] for f in wfo if f["expectancy"] is not None and f["n"] >= 10]
    pos_folds = sum(1 for e in fold_exp if e > 0)
    wfo_summary = {
        "folds_with_signals": len(fold_exp),
        "folds_positive": pos_folds,
        "all_folds_positive": (len(fold_exp) >= 3 and pos_folds == len(fold_exp)),
        "fold_expectancies": [round(e, 5) for e in fold_exp],
    }
    return {
        "timeframe": tf, "bars": len(df), "span": span, "horizon": horizon,
        "signals_total": len(signals),
        "all": _stats(all_rets),
        "in_regime": _stats(in_rets),
        "walkforward": wfo, "wfo_summary": wfo_summary,
        "regime_coverage": dict(Counter(rg for (_, _, rg) in signals)),
    }


def main():
    results = {}
    for name in STRATEGIES:
        results[name] = {"design_tf": StrategyConfig.get_strategy_timeframe(name, "1h"),
                         "intended_regime": sorted(INTENDED_REGIME.get(name, [])), "symbols": {}}
        for sym in SYMBOLS:
            try:
                results[name]["symbols"][sym] = evaluate(name, sym)
            except Exception as e:
                results[name]["symbols"][sym] = {"error": str(e)}
        print(f"done {name}", file=sys.stderr)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
