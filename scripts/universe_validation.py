"""Phase-12 broader-universe validation (analysis only; frozen strategies).

Runs the 10 active strategies on the NEW symbols (BTC/ETH/SOL already done in
_revalidation_results.json) on each strategy's design TF, regime-conditioned, per-symbol,
net of round-trip cost, adding drawdown + cost-adjusted (cumulative) return + 4-fold WFO.
No strategy/param/threshold changes.
"""
from __future__ import annotations
import json, os, sys
import numpy as np, pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import logging; logging.disable(logging.WARNING)
from domain.value_objects import Symbol
from infrastructure.strategies.strategy_config import StrategyConfig
import scripts.strategy_deployment_revalidation as R

NEW_SYMBOLS = ["BNB-USDT", "XRP-USDT", "DOGE-USDT", "ADA-USDT", "LINK-USDT", "TRX-USDT", "SUI-USDT", "AVAX-USDT"]
N_FOLDS = 4


def _maxdd(cum):
    if len(cum) == 0:
        return 0.0
    peak = -1e18; dd = 0.0
    for v in cum:
        peak = max(peak, v); dd = min(dd, v - peak)
    return float(dd)


def evaluate(name, symbol):
    tf = StrategyConfig.get_strategy_timeframe(name, "1h")
    path = os.path.join("data", "history", "raw", tf, f"{symbol}.csv")
    if not os.path.exists(path):
        return {"error": "no data"}
    df = pd.read_csv(path).tail(R.MAX_BARS.get(tf, 30000)).reset_index(drop=True)
    if len(df) < 250:
        return {"error": f"insufficient bars ({len(df)})"}
    regimes = R._label_regimes(df)
    horizon = R.HORIZON_BY_TF.get(tf, 6)
    close = df["close"].values
    bars = [{"open": r.open, "high": r.high, "low": r.low, "close": r.close,
             "volume": r.volume, "timestamp": int(r.timestamp)} for r in df.itertuples()]
    sym = Symbol(symbol.replace("-", ""))
    a = R._adapter(name)
    intended = R.INTENDED_REGIME.get(name, set())
    sigs = []
    for i, b in enumerate(bars):
        try:
            a.update_with_market_data(b); s = a.generate_signal(sym)
        except Exception:
            s = None
        if s is None:
            continue
        st = (getattr(getattr(s, "signal_type", None), "name", "") or "").upper()
        side = 1 if ("BUY" in st or "LONG" in st) else (-1 if ("SELL" in st or "SHORT" in st) else 0)
        if side != 0 and i + horizon < len(close):
            sigs.append((i, side, regimes[i]))

    def net(i, s): return s * ((close[i + horizon] - close[i]) / close[i]) - R.ROUND_TRIP_COST
    in_sig = [(i, s) for (i, s, rg) in sigs if rg in intended] if intended else [(i, s) for (i, s, _) in sigs]
    in_rets = [net(i, s) for (i, s) in in_sig]
    n_all = len(sigs)
    cum = np.cumsum(in_rets) if in_rets else np.array([])
    folds = []
    nbar = len(df)
    for k in range(N_FOLDS):
        lo, hi = k * nbar // N_FOLDS, (k + 1) * nbar // N_FOLDS
        fr = [net(i, s) for (i, s) in in_sig if lo <= i < hi]
        folds.append(float(np.mean(fr)) if fr else None)
    return {
        "timeframe": tf, "bars": len(df), "horizon": horizon, "signals_total": n_all,
        "in_regime_n": len(in_rets),
        "in_regime_expectancy": float(np.mean(in_rets)) if in_rets else None,
        "in_regime_win_rate": float((np.array(in_rets) > 0).mean()) if in_rets else None,
        "cost_adjusted_total_return": float(np.sum(in_rets)) if in_rets else 0.0,
        "max_drawdown": _maxdd(cum),
        "wfo_fold_expectancy": folds,
        "wfo_positive_folds": sum(1 for f in folds if f is not None and f > 0),
    }


def main():
    out = {}
    for name in R.SURVIVING:
        out[name] = {"intended_regime": sorted(R.INTENDED_REGIME.get(name, [])), "symbols": {}}
        for sym in NEW_SYMBOLS:
            out[name]["symbols"][sym] = evaluate(name, sym)
        print(f"done {name}", file=sys.stderr)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
