"""E51 — H3 volatility-risk regime overlay for XS-COMBO-V1 (PRE-REGISTERED 2026-11-26).

Mechanism: implied-volatility shocks (BTC DVOL, Deribit, forward-looking options market) mark stress when crowded
shorts squeeze and illiquid longs gap; a market-neutral carry book is hit in those windows.
Rule (fixed): DVOL shock on day D = 7-day log change of BTC DVOL daily close above its 90th percentile computed on
the DEV window only. After a shock day, XS-COMBO-V1 runs at HALF gross for the next 7 days (days D+1..D+7).
Each switch (to half or back to full) costs 0.05 % of capital (half the book traded, fee + spread).
Base series: V1 daily net returns averaged over the 7 weekly phases (frozen machinery, live-like universe).
Windows: DEV 2021-04-01..2024-12-31 (DVOL history starts 2021); TEST 2025-01-01..2026-10-31 (read once).
PASS: overlay Sharpe > V1 Sharpe in BOTH windows, TEST max drawdown smaller, and TEST annual return not lower than
90 % of V1's. One-window improvement -> R5 INFO line only. Otherwise reject.
Note (E38): weak XS-COMBO periods were followed by recovery; de-risking after stress may cut the rebound -> this is
exactly what the TEST window must show or refute.
Usage: cd research/v2 && python experiments/e51_dvol_overlay.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "lake" / "deribit_dvol_btc_daily.parquet"
P = S.PARAMS
DEV = ("2021-04-01", "2024-12-31")
TEST = ("2025-01-01", "2026-10-31")
SWITCH = 0.0005


def dvol() -> pd.Series:
    if not CACHE.exists():
        rows, start = [], int(pd.Timestamp("2021-01-01", tz="UTC").timestamp() * 1000)
        end = int(pd.Timestamp("2026-11-01", tz="UTC").timestamp() * 1000)
        while start < end:
            stop = min(end, start + 900 * 86_400_000)
            u = (f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&start_timestamp={start}"
                 f"&end_timestamp={stop}&resolution=86400")
            rows += json.loads(urllib.request.urlopen(u, timeout=60).read())["result"]["data"]
            start = stop
        d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"]).drop_duplicates("t")
        d.to_parquet(CACHE, index=False)
    d = pd.read_parquet(CACHE)
    return pd.Series(d.c.to_numpy(), index=pd.to_datetime(d.t, unit="ms", utc=True)).sort_index()


def v1_daily() -> pd.Series:
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    fr = pn.forward_returns(p)
    w = bt.rank_long_short(S.signal(p, mask), mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
    parts = []
    for k in range(7):
        a = pd.Timestamp(DEV[0], tz="UTC") + pd.Timedelta(days=k)
        ww = w[(w.index >= a) & (w.index <= TEST[1])]
        parts.append(bt.run(ww, fr.reindex(ww.index), p, bt.CostModel(), rebalance_every=P["rebalance_every"]).net.iloc[:-1])
    return pd.concat(parts, axis=1).mean(1)


def stats(y):
    eq = (1 + y).cumprod()
    return {"ann": round(y.mean() * 365, 4), "sharpe": round(y.mean() / y.std() * np.sqrt(365), 3),
            "mdd": round(float((eq / eq.cummax() - 1).min()), 4)}


def main():
    base = v1_daily()
    dv = dvol().reindex(base.index).ffill()
    ch = np.log(dv).diff(7)
    thr = float(ch.loc[DEV[0]:DEV[1]].quantile(0.9))
    shock = ch > thr
    half = pd.Series(False, index=base.index)
    for d in shock[shock].index:
        half.loc[d + pd.Timedelta(days=1): d + pd.Timedelta(days=7)] = True
    scale = np.where(half, 0.5, 1.0)
    switches = pd.Series(scale, index=base.index).diff().abs().fillna(0) > 0
    ov = base * scale - switches * SWITCH
    print(f"DVOL shock threshold (DEV p90 of 7d log change): {thr:.3f}; share of days at half gross: {half.mean():.2%}")
    res = {}
    for name, (a, b) in (("DEV", DEV), ("TEST", TEST)):
        res[name] = {"v1": stats(base.loc[a:b]), "overlay": stats(ov.loc[a:b]), "half_share": round(float(half.loc[a:b].mean()), 3)}
        print(name, res[name])
    ok = (res["DEV"]["overlay"]["sharpe"] > res["DEV"]["v1"]["sharpe"] and res["TEST"]["overlay"]["sharpe"] > res["TEST"]["v1"]["sharpe"]
          and res["TEST"]["overlay"]["mdd"] > res["TEST"]["v1"]["mdd"] and res["TEST"]["overlay"]["ann"] >= 0.9 * res["TEST"]["v1"]["ann"])
    one = (res["DEV"]["overlay"]["sharpe"] > res["DEV"]["v1"]["sharpe"]) != (res["TEST"]["overlay"]["sharpe"] > res["TEST"]["v1"]["sharpe"])
    print("E51", "CANDIDATE" if ok else ("R5 INFO ONLY" if one else "REJECT"))


if __name__ == "__main__":
    main()
