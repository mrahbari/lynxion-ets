"""E35 — MeanReversion rebuilt with a funding (crowding) condition, 4h (operator request, 2026-11-24).

Design rationale (from our own evidence): intraday reversion has no edge (E9-E28, two 2026 papers); reversal
exists at multi-hour/daily horizons before costs (E31 gross Sharpe +0.67 / +0.39); funding is the only validated
information source (XS-COMBO). A stretched move that runs AGAINST the crowded side (funding) is an unwind
candidate, and the position is paid funding while it waits.
Pre-registered (committed before any run). Textbook values, no search.
  Data: Binance USDT-M 1h -> 4h bars (UTC 00/04/08/...), real funding (data/research_cache/e23).
  Universe: BTC ETH SOL XRP DOGE AVAX LINK SUI ADA LTC. DEV 2020-01-01..2024-12-31; HOLDOUT 2025-01-01..2026-10-31.
  Stretch (closed 4h bar): close < SMA20 - 2 x std20 -> LONG candidate; close > SMA20 + 2 x std20 -> SHORT.
  Funding condition (last settled rate at the bar close):
    LONG only if funding <= 0          (shorts crowded / paying);
    SHORT only if funding >= 0.0002    (2 x the 0.01 % base rate: longs crowded).
  Entry: next 4h bar open. Exit: first 4h close back across SMA20 (exit next open), or 18 bars (72 h), or stop
    2.5 x ATR(14) checked on High/Low first. One position per symbol.
  Costs: 5 bp fee + 2 bp slippage per side; real funding over the hold (sign by side).
  CONTROL: identical without the funding condition (measures what funding adds).
  PASS: funding arm DEV mean net >= +15 bp/trade with t >= 2, n >= 150, >= 6/10 symbols positive; HOLDOUT
        mean net > 0 and >= 50 % of DEV; and funding arm > CONTROL in both windows.
  Decision: PASS -> build as the MeanReversion strategy (4h, live on VST, shadow first).
Usage: python research/v2/experiments/e35_funding_mean_reversion.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e23_funding_extreme as e23  # noqa: E402

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT", "ADAUSDT", "LTCUSDT"]
H4 = 4 * 3_600_000
FEE, SLIP = 0.0005, 0.0002


def bars4(sym):
    k = e23.klines(sym).copy()
    k["b"] = k.t // H4
    g = k.groupby("b").agg(t=("t", "first"), o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), n=("c", "size"))
    g = g[g.n == 4].reset_index(drop=True)
    g["sma"] = g.c.rolling(20).mean()
    g["sd"] = g.c.rolling(20).std()
    tr = np.maximum(g.h - g.l, np.maximum((g.h - g.c.shift()).abs(), (g.l - g.c.shift()).abs()))
    g["atr"] = tr.rolling(14).mean()
    fr = e23.funding(sym).sort_values("fundingTime")
    g["close_t"] = g.t + H4
    g = pd.merge_asof(g.sort_values("close_t"), fr.rename(columns={"fundingTime": "ft"}), left_on="close_t",
                      right_on="ft", direction="backward").sort_values("t").reset_index(drop=True)
    return g, fr


def simulate(sym, use_funding):
    g, fr = bars4(sym)
    t, o, h, l, c = (g[x].to_numpy() for x in ("t", "o", "h", "l", "c"))
    sma, sd, atr, f = g.sma.to_numpy(), g.sd.to_numpy(), g.atr.to_numpy(), g.fundingRate.to_numpy()
    ft, fv = fr.fundingTime.to_numpy(), fr.fundingRate.to_numpy()
    trades, i, n = [], 30, len(t)
    while i < n - 2:
        if not (np.isfinite(sma[i]) and np.isfinite(sd[i]) and np.isfinite(atr[i])) or sd[i] <= 0:
            i += 1; continue
        side = 1 if c[i] < sma[i] - 2 * sd[i] else -1 if c[i] > sma[i] + 2 * sd[i] else 0
        if side and use_funding:
            fi = f[i]
            if not np.isfinite(fi) or (side > 0 and fi > 0) or (side < 0 and fi < 0.0002):
                side = 0
        if side == 0:
            i += 1; continue
        e = i + 1
        entry = o[e] * (1 + side * SLIP)
        stop = entry - side * 2.5 * atr[i]
        px, x = None, None
        for m in range(e, min(e + 18, n)):
            if (side > 0 and l[m] <= stop) or (side < 0 and h[m] >= stop):
                gap = (side > 0 and o[m] < stop) or (side < 0 and o[m] > stop)
                px, x = (o[m] if gap else stop), m
                break
            if np.isfinite(sma[m]) and ((side > 0 and c[m] >= sma[m]) or (side < 0 and c[m] <= sma[m])) and m + 1 < n:
                px, x = o[m + 1], m + 1
                break
        if px is None:
            x = min(e + 17, n - 1)
            px = c[x]
        px *= (1 - side * SLIP)
        paid = fv[(ft > t[e]) & (ft <= t[x] + H4)].sum()
        ret = side * (px / entry - 1) - side * paid - 2 * FEE
        trades.append({"symbol": sym, "t_in": int(t[e]), "side": side, "ret": ret, "funding": -side * paid})
        i = x + 1
    return trades


def summ(d):
    n = len(d)
    if n < 2:
        return {"n": n}
    m, s = d.ret.mean(), d.ret.std(ddof=1)
    return {"n": n, "mean_bp": round(m * 1e4, 1), "t": round(m / (s / np.sqrt(n)), 2), "win": round((d.ret > 0).mean(), 3),
            "funding_bp": round(d.funding.mean() * 1e4, 1), "long_share": round((d.side > 0).mean(), 2),
            "symbols_pos": int((d.groupby("symbol").ret.mean() > 0).sum())}


def main():
    hold0 = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp() * 1000)
    dev0 = int(pd.Timestamp("2020-01-01", tz="UTC").timestamp() * 1000)
    end = int(pd.Timestamp("2026-11-01", tz="UTC").timestamp() * 1000)
    rows, res = [], {}
    for arm, uf in (("FUNDING", True), ("CONTROL", False)):
        d = pd.DataFrame([x for s in SYMS for x in simulate(s, uf)])
        d = d[(d.t_in >= dev0) & (d.t_in < end)]
        d.to_csv(e23.CACHE / f"E35_{arm}_trades.csv", index=False)
        for win, m in (("DEV", d.t_in < hold0), ("HOLDOUT", d.t_in >= hold0)):
            res[(arm, win)] = summ(d[m])
            rows.append({"arm": arm, "window": win, **res[(arm, win)]})
    r = pd.DataFrame(rows)
    r.to_csv(e23.OUT / "E35_funding_mean_reversion.csv", index=False)
    print(r.to_string(index=False))
    fd, fh, cd, ch = res[("FUNDING", "DEV")], res[("FUNDING", "HOLDOUT")], res[("CONTROL", "DEV")], res[("CONTROL", "HOLDOUT")]
    ok = (fd["n"] >= 150 and fd["mean_bp"] >= 15 and fd["t"] >= 2 and fd["symbols_pos"] >= 6
          and fh["mean_bp"] > 0 and fh["mean_bp"] >= 0.5 * fd["mean_bp"]
          and fd["mean_bp"] > cd["mean_bp"] and fh["mean_bp"] > ch["mean_bp"])
    print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
