"""Validate RETIRED-slot replacement candidates (STR, DCB) — same rigor as the suite re-eval.

Design TF + per-symbol (BTC/ETH/SOL) + regime-conditioned + cross-period (halves) + 4-fold
walk-forward, net of existing round-trip cost. Existing/a-priori params only; no tuning.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import logging
logging.disable(logging.WARNING)

from domain.value_objects import Symbol
from infrastructure.strategies.strategy_config import StrategyConfig
from infrastructure.strategies.adapters.short_term_reversal_strategy_adapter import ShortTermReversalStrategyAdapter
from infrastructure.strategies.adapters.donchian_breakout_strategy_adapter import DonchianBreakoutStrategyAdapter
# reuse the suite re-eval helpers
import scripts.strategy_deployment_revalidation as R

CANDIDATES = {
    "short_term_reversal": (ShortTermReversalStrategyAdapter, {"ranging"}),
    "donchian_breakout": (DonchianBreakoutStrategyAdapter, {"breakout", "trending_up", "trending_down"}),
}
SYMBOLS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
N_FOLDS = 4


def evaluate(name, symbol):
    cls, intended = CANDIDATES[name]
    tf = StrategyConfig.get_strategy_timeframe(name, "1h")
    path = os.path.join("data", "history", "raw", tf, f"{symbol}.csv")
    if not os.path.exists(path):
        return {"error": f"no data {path}"}
    df = pd.read_csv(path).tail(R.MAX_BARS.get(tf, 30000)).reset_index(drop=True)
    regimes = R._label_regimes(df)
    horizon = R.HORIZON_BY_TF.get(tf, 6)
    close = df["close"].values
    bars = [{"open": r.open, "high": r.high, "low": r.low, "close": r.close,
             "volume": r.volume, "timestamp": int(r.timestamp)} for r in df.itertuples()]
    sym = Symbol(symbol.replace("-", ""))
    a = cls({})
    signals = []
    for i, b in enumerate(bars):
        try:
            a.update_with_market_data(b)
            s = a.generate_signal(sym)
        except Exception:
            s = None
        if s is None:
            continue
        st = (getattr(getattr(s, "signal_type", None), "name", "") or "").upper()
        side = 1 if ("BUY" in st or "LONG" in st) else (-1 if ("SELL" in st or "SHORT" in st) else 0)
        if side != 0 and i + horizon < len(close):
            signals.append((i, side, regimes[i]))

    def net(i, side):
        return side * ((close[i + horizon] - close[i]) / close[i]) - R.ROUND_TRIP_COST

    def stats(rs):
        if not rs:
            return {"n": 0, "expectancy": None, "win_rate": None}
        x = np.array(rs)
        return {"n": len(x), "expectancy": float(x.mean()), "win_rate": float((x > 0).mean())}

    in_sig = [(i, s) for (i, s, rg) in signals if rg in intended]
    in_rets = [net(i, s) for (i, s) in in_sig]
    n = len(df)
    mid = n // 2
    h1 = [net(i, s) for (i, s) in in_sig if i < mid]
    h2 = [net(i, s) for (i, s) in in_sig if i >= mid]
    # walk-forward: 4 sequential folds; positive-fold count on in-regime
    folds = []
    for k in range(N_FOLDS):
        lo, hi = k * n // N_FOLDS, (k + 1) * n // N_FOLDS
        fr = [net(i, s) for (i, s) in in_sig if lo <= i < hi]
        folds.append(stats(fr))
    pos_folds = sum(1 for f in folds if f["expectancy"] is not None and f["expectancy"] > 0)
    return {
        "timeframe": tf, "bars": len(df), "horizon": horizon,
        "signals_total": len(signals),
        "all": stats([net(i, s) for (i, s, _) in signals]),
        "in_regime": stats(in_rets),
        "half1": stats(h1), "half2": stats(h2),
        "wfo_folds": folds, "wfo_positive_folds": pos_folds, "wfo_total_folds": N_FOLDS,
    }


def main():
    out = {}
    for name in CANDIDATES:
        out[name] = {"intended_regime": sorted(CANDIDATES[name][1]), "symbols": {}}
        for sym in SYMBOLS:
            out[name]["symbols"][sym] = evaluate(name, sym)
            print(f"done {name} {sym}", file=sys.stderr)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
