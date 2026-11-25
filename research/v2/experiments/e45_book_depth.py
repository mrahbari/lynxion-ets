"""E45 — order-book depth: directional imbalance and thin-book risk (PRE-REGISTERED 2026-11-25, before the data is read).

Data: free Binance daily bookDepth archive -> data/lake/binance_um/bookdepth_5m (40 most liquid perps, 2023-01..),
5-minute buckets, cumulative order-book notional within +/-0.2..5 % of price; `t` = bucket end (known time).
Prices: 1h lake klines. Never used before in E1-E44.
Windows: DEV 2023-01-01..2024-12-31, TEST 2025-01-01..2026-10-31 (read once for this family).

H1 (direction, 4h): imbalance OBI = (bid_1% - ask_1%) / (bid_1% + ask_1%) from n_m1 / n_p1, sampled at each hour end;
   z = (OBI - mean) / std over the previous 7 days (168 hourly samples) per symbol.
   Event: z >= +2 -> LONG, z <= -2 -> SHORT; entry = open of the next 1h bar, exit 4 bars later (4 h);
   non-overlap per symbol; net of 2 x (5 bp fee + 2 bp slippage).
   PASS: DEV mean net >= +5 bp/trade with day-clustered t >= 2 and >= 60 % of symbols positive; TEST mean net > 0 and
   >= 50 % of DEV, >= 50 % of symbols positive.
H2 (risk, 4h): thin book = total notional within +/-1 % below 30 % of its 7-day median. Measure the next 4h absolute
   return and the 4h range, in units of the 14-hour ATR, after thin-book hours vs all other hours.
   PASS (useful as an entry filter): thin-book mean 4h range >= 1.5x normal in BOTH windows, and >= 60 % of symbols
   in each window show a higher range after thin-book hours.
Decision: H1 PASS -> candidate entry-timing input (prospective shadow next); H2 PASS -> candidate "do not enter into a
thin book" filter for the platform entries and the Radar (prospective shadow next). FAIL -> recorded, no change.
Usage: cd research/v2 && python experiments/e45_book_depth.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
DEPTH = pn.LAKE / "bookdepth_5m"
H = 3_600_000
SPLIT = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp() * 1000)
END = int(pd.Timestamp("2026-10-31", tz="UTC").timestamp() * 1000)
COST = 2 * (0.0005 + 0.0002)


def load(sym):
    d = pd.read_parquet(DEPTH / f"{sym}.parquet")
    d = d[(d.t % H) == 0].set_index("t").sort_index()                   # hour-end samples
    k = pd.read_parquet(pn.LAKE / "klines_1h" / f"{sym}.parquet", columns=["open_time", "open", "high", "low", "close"])
    k = k.drop_duplicates("open_time").set_index("open_time").sort_index()
    return d, k


def analyse(sym):
    d, k = load(sym)
    obi = (d.n_m1 - d.n_p1) / (d.n_m1 + d.n_p1)
    z = (obi - obi.rolling(168, min_periods=100).mean().shift(1)) / obi.rolling(168, min_periods=100).std().shift(1)
    tot = d.n_m1 + d.n_p1
    thin = tot < 0.3 * tot.rolling(168, min_periods=100).median().shift(1)
    o, h, l, c = (k[x] for x in ("open", "high", "low", "close"))
    tr = np.maximum(h - l, np.maximum((h - c.shift()).abs(), (l - c.shift()).abs()))
    atr = tr.rolling(14).mean()
    trades, last_exit, risk = [], -1, []
    for t in d.index:
        if t >= END or t not in k.index:
            continue
        i = k.index.get_loc(t)                                           # bar opening at t = first bar after the sample
        if i + 4 >= len(k) or i < 15:
            continue
        a = atr.iloc[i - 1]
        if not np.isfinite(a) or a <= 0:
            continue
        fwd = k.iloc[i:i + 4]
        risk.append({"t": t, "thin": bool(thin.get(t, False)), "range_atr": (fwd.high.max() - fwd.low.min()) / a,
                     "absret_atr": abs(fwd.close.iloc[-1] - fwd.open.iloc[0]) / a})
        zt = z.get(t, np.nan)
        if not np.isfinite(zt) or abs(zt) < 2 or i <= last_exit:
            continue
        side = 1 if zt > 0 else -1
        ret = side * (fwd.close.iloc[-1] / fwd.open.iloc[0] - 1) - COST
        trades.append({"t": t, "sym": sym, "side": side, "net": ret})
        last_exit = i + 3
    r = pd.DataFrame(risk); r["sym"] = sym
    return pd.DataFrame(trades), r


def stats(x):
    if len(x) < 30:
        return {"n": len(x)}
    day = x.assign(day=x.t // 86_400_000).groupby("day").net.mean()
    tv = day.mean() / (day.std(ddof=1) / np.sqrt(len(day)))
    sp = x.groupby("sym").net.mean()
    return {"n": len(x), "net_bp": round(x.net.mean() * 1e4, 2), "t_day": round(float(tv), 2),
            "p": float(tdist.sf(tv, len(day) - 1)), "sym_pos": round(float((sp > 0).mean()), 2)}


def main():
    syms = sorted(p.stem for p in DEPTH.glob("*.parquet"))
    out = [analyse(s) for s in syms]
    tr = pd.concat([o[0] for o in out], ignore_index=True)
    rk = pd.concat([o[1] for o in out], ignore_index=True)
    print("symbols", len(syms))
    res = {}
    for win, m in (("DEV", tr.t < SPLIT), ("TEST", tr.t >= SPLIT)):
        res[win] = stats(tr[m])
        print("H1", win, res[win])
    d, te = res["DEV"], res["TEST"]
    h1 = (d.get("net_bp", -1) >= 5 and d.get("t_day", 0) >= 2 and d.get("sym_pos", 0) >= 0.6
          and te.get("net_bp", -1) > 0 and te.get("net_bp", -1) >= 0.5 * d["net_bp"] and te.get("sym_pos", 0) >= 0.5)
    print("H1", "PASS" if h1 else "FAIL")
    h2 = True
    for win, m in (("DEV", rk.t < SPLIT), ("TEST", rk.t >= SPLIT)):
        x = rk[m]
        g = x.groupby("thin").range_atr.mean()
        per = x.groupby(["sym", "thin"]).range_atr.mean().unstack()
        share = float((per[True] > per[False]).mean()) if True in per and False in per else 0.0
        ratio = float(g.get(True, np.nan) / g.get(False, np.nan))
        print("H2", win, {"thin_hours": int(x.thin.sum()), "range_ratio": round(ratio, 2), "sym_share": round(share, 2)})
        h2 &= bool(ratio >= 1.5 and share >= 0.6)
    print("H2", "PASS" if h2 else "FAIL")
    tr.to_csv(ROOT / "data/research_cache/E45_obi_trades.csv", index=False)


if __name__ == "__main__":
    main()
