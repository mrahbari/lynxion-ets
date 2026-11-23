"""E12 — watchers in their OWN roles (regime filter / veto), applied to the platform strategies' real trades.

Why: E11 showed no watcher predicts direction. Their designed roles are REGIME (allow / block trading) and
EXECUTION veto, not direction. This tests that role directly: do the E9 strategy trades taken in a given
watcher state do better than the strategy's trades overall?

Pre-registered before running (2026-11-23):
  Trades: E9 trades (8 strategies, 10 perps, live-equivalent execution, net of fees, in R units).
  States at entry, from bars CLOSED before the entry bar opens (causal), concept-level re-implementation of
  each watcher on Binance 1h bars (not byte-identical to the 1m-fed live code):
    vol      Volatility:  std(last 6 1h log returns) / std(last 168)  -> compression <= 0.67 / normal / >= 1.5 expansion
    trend    TrendMTF:    t-stat of log-close regression, 20 bars, on 1h and 4h (4h = closed 4h buckets);
                          |t| >= 2 on both and same sign -> up / down, else none; reported vs trade side:
                          with / against / none
    funding  FundingRate: latest published Binance funding before entry; crowded = sign(rate) == trade side
                          (long pays) and |rate| >= 0.01% (the 8h base rate), else not_crowded
    pulse    MarketPulse: 24h return sign vs trade side (with / against)
  Cells: strategy x filter x state (8 x 4 x 2-3 = 80 cells). Report the count with any winner.
  DEV (2025-11-01..2026-06-30) pass: n >= 100, mean R >= +0.05, PF >= 1.2, both time halves > 0, and
  >= 6/10 symbols positive. HOLDOUT (2026-07-01..10-31) read ONLY for DEV-passing cells: mean R > 0, PF >= 1.1.
  Also reported, no pass/fail: pooled lift = mean R(state) - mean R(strategy) per filter state (role value
  even when the base strategy is negative).

Usage: python research/v2/experiments/e12_watcher_role_filters.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402

OUT = e9.OUT
DEV0 = int(e9.DEV_START.timestamp() * 1000)
HOLD0 = int(e9.HOLDOUT_START.timestamp() * 1000)
H = 3_600_000


def funding(sym: str) -> pd.DataFrame:
    f = e9.CACHE / f"{sym}_funding.json"
    if not f.exists():
        rows, t = [], DEV0 - 30 * 86_400_000
        while True:
            with urllib.request.urlopen(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}"
                                        f"&startTime={t}&limit=1000", timeout=30) as r:
                b = json.loads(r.read())
            if not b:
                break
            rows += b
            t = int(b[-1]["fundingTime"]) + 1
            if len(b) < 1000:
                break
            time.sleep(0.2)
        f.write_text(json.dumps(rows))
    d = pd.DataFrame(json.loads(f.read_text()))
    return pd.DataFrame({"t": d.fundingTime.astype(np.int64), "rate": d.fundingRate.astype(float)}).sort_values("t")


def tstat(y: np.ndarray) -> float:
    x = np.arange(len(y), dtype=float)
    x -= x.mean()
    y = np.log(y)
    b = (x * (y - y.mean())).sum() / (x * x).sum()
    res = y - y.mean() - b * x
    se = np.sqrt((res * res).sum() / (len(y) - 2) / (x * x).sum())
    return float(b / se) if se > 0 else float(np.sign(b) * 1e6)


def states(sym: str) -> pd.DataFrame:
    """Per 1h bar CLOSE time: watcher states known at that moment."""
    k = e9.klines(sym, "1h").sort_values("t").reset_index(drop=True)
    lr = np.log(k.c).diff()
    ratio = lr.rolling(6).std() / lr.rolling(168).std()
    t1 = k.c.rolling(20).apply(tstat, raw=True)
    b4 = k.assign(b=k.t // (4 * H)).groupby("b").agg(c=("c", "last"), n=("c", "size"), t=("t", "first"))
    b4 = b4[b4.n == 4]
    b4["t4"] = b4.c.rolling(20).apply(tstat, raw=True)
    b4["close_t"] = b4.t + 4 * H
    s = pd.DataFrame({"close_t": k.t + H, "ratio": ratio, "t1": t1, "r24": np.log(k.c / k.c.shift(24))})
    s = pd.merge_asof(s, b4[["close_t", "t4"]].sort_values("close_t"), on="close_t", direction="backward")
    f = funding(sym).rename(columns={"t": "close_t"})
    return pd.merge_asof(s, f, on="close_t", direction="backward")


def label(tr: pd.DataFrame) -> pd.DataFrame:
    out = []
    for sym, g in tr.groupby("symbol"):
        st = states(sym)
        g = pd.merge_asof(g.sort_values("t_in"), st, left_on="t_in", right_on="close_t", direction="backward")
        sgn = np.where(g.side == "BUY", 1, -1)
        g["vol"] = np.where(g.ratio >= 1.5, "expansion", np.where(g.ratio <= 0.67, "compression", "normal"))
        tdir = np.where((g.t1 >= 2) & (g.t4 >= 2), 1, np.where((g.t1 <= -2) & (g.t4 <= -2), -1, 0))
        g["trend"] = np.where(tdir == 0, "none", np.where(tdir == sgn, "with", "against"))
        g["funding"] = np.where((np.sign(g.rate) == sgn) & (g.rate.abs() >= 1e-4), "crowded", "not_crowded")
        g["pulse"] = np.where(np.sign(g.r24) == sgn, "with", "against")
        out.append(g)
    return pd.concat(out)


def stats(g: pd.DataFrame) -> dict:
    g = g.sort_values("t_in")
    w, lo = g.ret[g.ret > 0].sum(), -g.ret[g.ret < 0].sum()
    h = len(g) // 2
    return {"n": len(g), "mean_R": round(g.R.mean(), 3), "PF": round(w / lo, 2) if lo else np.inf,
            "h1_R": round(g.R.iloc[:h].mean(), 3), "h2_R": round(g.R.iloc[h:].mean(), 3),
            "symbols_positive": int((g.groupby("symbol").ret.sum() > 0).sum())}


def main() -> None:
    tr = pd.read_csv(OUT / "E9_strategy_backtest_trades.csv")
    tr = label(tr)
    dev, hold = tr[(tr.t_in >= DEV0) & (tr.t_in < HOLD0)], tr[tr.t_in >= HOLD0]
    rows = []
    for strat, g in dev.groupby("strategy"):
        base = g.R.mean()
        for filt in ("vol", "trend", "funding", "pulse"):
            for state, gg in g.groupby(filt):
                s = stats(gg)
                s.update(strategy=strat, filter=filt, state=state, lift_R=round(gg.R.mean() - base, 3))
                s["dev_pass"] = bool(s["n"] >= 100 and s["mean_R"] >= 0.05 and s["PF"] >= 1.2 and s["h1_R"] > 0
                                     and s["h2_R"] > 0 and s["symbols_positive"] >= 6)
                if s["dev_pass"]:
                    hh = hold[(hold.strategy == strat) & (hold[filt] == state)]
                    hs = stats(hh) if len(hh) > 1 else {"n": len(hh)}
                    s.update({f"holdout_{k}": v for k, v in hs.items()})
                    s["holdout_pass"] = bool(len(hh) > 1 and hs["mean_R"] > 0 and hs["PF"] >= 1.1)
                rows.append(s)
    r = pd.DataFrame(rows)
    cols = ["strategy", "filter", "state", "n", "mean_R", "lift_R", "PF", "h1_R", "h2_R", "symbols_positive", "dev_pass"]
    r = r[cols + [c for c in r.columns if c not in cols]]
    r.to_csv(OUT / "E12_watcher_role_filters.csv", index=False)
    pooled = (dev.assign(base=dev.groupby("strategy").R.transform("mean"))
              .melt(id_vars=["R", "base"], value_vars=["vol", "trend", "funding", "pulse"], var_name="filter",
                    value_name="state")
              .assign(lift=lambda d: d.R - d.base).groupby(["filter", "state"])
              .agg(n=("R", "size"), mean_R=("R", "mean"), lift_R=("lift", "mean"),
                   lift_se=("lift", lambda x: x.std(ddof=1) / np.sqrt(len(x)))).round(3).reset_index())
    pooled["lift_t"] = (pooled.lift_R / pooled.lift_se).round(2)
    pooled.to_csv(OUT / "E12_watcher_role_filters_pooled.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(f"cells tested: {len(r)}; DEV passes: {int(r.dev_pass.sum())}")
    print(r.to_string(index=False))
    print(pooled.to_string(index=False))


if __name__ == "__main__":
    main()
