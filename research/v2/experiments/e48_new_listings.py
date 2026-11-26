"""E48 — New Binance USDT-M perp listings: do new contracts underperform after launch? (PRE-REGISTERED 2026-11-26)

Idea: newly listed tokens/perps are often launched at high valuations with low float and fall afterwards (unlock and
emission overhang, hype decay). The listing date is public, so a hedged short after launch is tradable.
Data: Binance 1h lake (delisted contracts included -> no survivorship bias); listing day = first full UTC day of 1h
data; funding from the lake. New event family for Lynxion.
Rule (fixed): SHORT at the close of listing day +1 (first two days skipped: no reliable price discovery / borrow),
hedged long 50 % BTC + 50 % ETH; exit at the close of day +31 (30 days), or when the daily high reaches entry x 1.30
(hard stop at that price). Net = -token return + hedge return - 4 x 7 bp + funding received on the short.
Eligibility: daily quote volume on day +1 >= $20M; BTCUSDT / ETHUSDT and non-perpetual symbols excluded.
Windows: DEV listings 2021-01-01..2024-12-31; TEST 2025-01-01..2026-09-30 (read once).
PASS: DEV mean net >= +3 % per event, t >= 2 (clustered by listing week), >= 55 % positive; TEST mean net > 0 and
>= 50 % of DEV. Reported also: no-stop variant and 14-day hold (descriptive, not decisive).
Usage: cd research/v2 && python experiments/e48_new_listings.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
COST, STOP, HOLD = 4 * (0.0005 + 0.0002), 0.30, 30
DEV0, SPLIT, END = pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-09-30", tz="UTC")


def main():
    p = pn.load_daily(start="2020-06-01", end="2026-10-31")
    close, high, qv, ff = p["close"], p["high"], p["quote_volume"], p["funding_fwd"].fillna(0)
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    hedge = (close["BTCUSDT"] / close["BTCUSDT"].shift(1) * 0.5 + close["ETHUSDT"] / close["ETHUSDT"].shift(1) * 0.5).fillna(1).cumprod()
    rows = []
    for s in close.columns:
        if s in nps or s in ("BTCUSDT", "ETHUSDT") or not s.endswith("USDT"):
            continue
        c = close[s].dropna()
        if len(c) < 40:
            continue
        d0 = c.index[0]                                    # first full day row
        if d0 < DEV0 or d0 > END:
            continue
        e_day = d0 + pd.Timedelta(days=1)
        x_day = e_day + pd.Timedelta(days=HOLD)
        if e_day not in c.index or x_day not in c.index or not (qv.at[e_day, s] >= 20e6):
            continue
        entry = c.at[e_day]
        path = high[s].loc[e_day + pd.Timedelta(days=1):x_day]
        hit = path[path >= entry * (1 + STOP)]
        out_day = hit.index[0] if len(hit) else x_day
        tok_ret = STOP if len(hit) else c.at[x_day] / entry - 1
        h_ret = hedge.at[out_day] / hedge.at[e_day] - 1
        fund = float(ff[s].loc[e_day:out_day - pd.Timedelta(days=1)].sum())
        nostop = -(c.at[x_day] / entry - 1) + (hedge.at[x_day] / hedge.at[e_day] - 1) - COST + float(ff[s].loc[e_day:x_day - pd.Timedelta(days=1)].sum())
        d14 = e_day + pd.Timedelta(days=14)
        h14 = -(c.at[d14] / entry - 1) + (hedge.at[d14] / hedge.at[e_day] - 1) - COST if d14 in c.index else np.nan
        rows.append({"sym": s, "listed": d0, "stopped": bool(len(hit)), "net": -tok_ret + h_ret - COST + fund,
                     "net_nostop": nostop, "net_14d": h14, "funding": fund})
    ev = pd.DataFrame(rows)
    ev.to_csv(ROOT / "data/research_cache/E48_listing_events.csv", index=False)

    def st(x, col="net"):
        if len(x) < 10:
            return {"n": len(x)}
        wk = x.groupby(x["listed"].dt.to_period("W"))[col].mean()
        return {"n": len(x), "mean": round(x[col].mean(), 4), "median": round(x[col].median(), 4),
                "t_week": round(wk.mean() / (wk.std(ddof=1) / np.sqrt(len(wk))), 2), "pos": round((x[col] > 0).mean(), 3)}
    res = {}
    for win, m in (("DEV", ev.listed < SPLIT), ("TEST", ev.listed >= SPLIT)):
        x = ev[m]
        res[win] = st(x)
        print(win, "PRIMARY (30d, stop 30%)", res[win], "stopped", round(x.stopped.mean(), 3), "funding", round(x.funding.mean(), 4))
        print(win, "  no stop", st(x, "net_nostop"), "| 14d", st(x.dropna(subset=["net_14d"]), "net_14d"))
    d, t = res["DEV"], res["TEST"]
    ok = (d.get("mean", -1) >= 0.03 and d.get("t_week", 0) >= 2 and d.get("pos", 0) >= 0.55
          and t.get("mean", -1) > 0 and t.get("mean", -1) >= 0.5 * d["mean"])
    print("E48", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
