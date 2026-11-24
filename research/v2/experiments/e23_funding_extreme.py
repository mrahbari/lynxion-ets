"""E23 — funding-extreme reversal as a standalone signal (Strategy layer, roadmap E16-U4 claim, 2026-11-24).

Why: the only validated edge in the project is funding (XS-COMBO-V1). Literature on crypto perps reports
that extreme funding marks crowded positioning that tends to unwind over the next hours. E22 used funding
only as a filter on price setups (fail); here funding IS the signal, on its natural 8-24 h horizon.

Pre-registered (2026-11-24, committed before any run). No parameter search.
  Universe: BTC ETH SOL XRP DOGE AVAX LINK SUI ADA LTC (Binance USDT-M; 1h klines + funding history).
  Windows: DEV 2020-01-01 .. 2024-12-31; HOLDOUT 2025-01-01 .. 2026-10-31 (read once).
  Signal at each funding settlement t (8 h): z = (f_t - mean) / std over the PREVIOUS 90 settlements.
    SHORT if z >= +2 and f_t > 0 (crowded longs); LONG if z <= -2 and f_t < 0 (crowded shorts).
  Entry: open of the 1h bar starting at t + 1 h (causal margin). One position per symbol.
  Exit: after H hours at the bar close; protective stop 2 x ATR(14, 1h) from entry, checked on High/Low
    (stop first). Costs: 5 bp fee per side + 2 bp slippage per side; funding settlements during the hold are
    paid/received at the real rates (short receives positive funding).
  Variants (all reported): V1 z>=2, H=24 h (PRIMARY); V2 z>=2, H=8 h; V3 z>=3, H=24 h.
  PASS (PRIMARY decides): DEV net mean >= +10 bp per trade with t >= 2.0, n >= 200, >= 6/10 symbols positive;
  HOLDOUT net mean > 0 and >= 50 % of the DEV mean.
  Decision: PASS -> build it as a platform strategy (shadow first). FAIL -> record, continue with E24.
Usage: python research/v2/experiments/e23_funding_extreme.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "research_cache" / "e23"
OUT = ROOT / "docs" / "v2" / "reports"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT", "ADAUSDT", "LTCUSDT"]
T0 = int(datetime(2019, 10, 1, tzinfo=timezone.utc).timestamp() * 1000)
END = int(datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp() * 1000)
HOLD0 = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
DEV0 = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
H = 3_600_000
FEE, SLIP = 0.0005, 0.0002


def _get(url):
    for i in range(5):
        try:
            return json.loads(urllib.request.urlopen(url, timeout=30).read())
        except Exception:
            time.sleep(2 + 3 * i)
    raise RuntimeError(url)


def klines(sym):
    f = CACHE / f"{sym}_1h.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows, t = [], T0
    while t < END:
        b = _get(f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1h&startTime={t}&limit=1500")
        if not b:
            break
        rows += b
        t = b[-1][0] + H
        time.sleep(0.1)
    d = pd.DataFrame(rows).iloc[:, :5]
    d.columns = ["t", "o", "h", "l", "c"]
    d = d.astype({"t": "int64", "o": float, "h": float, "l": float, "c": float}).drop_duplicates("t")
    d = d[d.t < END].reset_index(drop=True)
    d.to_parquet(f)
    return d


def funding(sym):
    f = CACHE / f"{sym}_funding.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows, t = [], T0
    while t < END:
        b = _get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&startTime={t}&limit=1000")
        if not b:
            break
        rows += b
        t = b[-1]["fundingTime"] + 1
        time.sleep(0.15)
    d = pd.DataFrame(rows)[["fundingTime", "fundingRate"]].astype({"fundingTime": "int64", "fundingRate": float})
    d = d[d.fundingTime < END].drop_duplicates("fundingTime").reset_index(drop=True)
    d.to_parquet(f)
    return d


def simulate(sym, zmin, hold_h):
    k, fr = klines(sym), funding(sym)
    t, o, h, l, c = (k[x].to_numpy() for x in ("t", "o", "h", "l", "c"))
    tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
    atr = np.r_[np.nan, pd.Series(tr).rolling(14).mean().to_numpy()]          # ATR known at bar close
    f = fr.fundingRate.to_numpy()
    mu = pd.Series(f).rolling(90).mean().shift(1).to_numpy()
    sd = pd.Series(f).rolling(90).std().shift(1).to_numpy()
    z = (f - mu) / sd
    ft = fr.fundingTime.to_numpy()
    idx = {int(x): i for i, x in enumerate(t)}
    trades, busy_until = [], -1
    for j in range(len(f)):
        if not np.isfinite(z[j]) or ft[j] < DEV0:
            continue
        side = -1 if (z[j] >= zmin and f[j] > 0) else 1 if (z[j] <= -zmin and f[j] < 0) else 0
        if side == 0:
            continue
        t_entry = (ft[j] // H) * H + H                       # bar starting >= settlement + 1 h margin
        i = idx.get(int(t_entry))
        if i is None or t_entry <= busy_until or i < 15 or i + hold_h >= len(t):
            continue
        a = atr[i - 1]
        if not np.isfinite(a) or a <= 0:
            continue
        entry = o[i] * (1 + side * SLIP)
        stop = entry - side * 2 * a
        exit_px, exit_i = None, i + hold_h - 1
        for m in range(i, i + hold_h):
            if (side > 0 and l[m] <= stop) or (side < 0 and h[m] >= stop):
                gap = (side > 0 and o[m] < stop) or (side < 0 and o[m] > stop)
                exit_px, exit_i = (o[m] if gap else stop), m
                break
        if exit_px is None:
            exit_px = c[exit_i]
        exit_px *= (1 - side * SLIP)
        t_exit = t[exit_i] + H
        paid = f[(ft > t_entry) & (ft <= t_exit)].sum()           # longs pay positive funding
        ret = side * (exit_px / entry - 1) - side * paid - 2 * FEE
        trades.append({"symbol": sym, "t_in": int(t_entry), "side": side, "z": z[j], "ret": ret,
                       "R": ret / (2 * a / entry), "stopped": exit_i < i + hold_h - 1, "funding": -side * paid})
        busy_until = t_exit
    return trades


def summarize(d):
    n = len(d)
    m, s = d.ret.mean(), d.ret.std(ddof=1)
    return {"n": n, "mean_bp": round(m * 1e4, 1), "t": round(m / (s / np.sqrt(n)), 2) if n > 1 and s > 0 else None,
            "win": round((d.ret > 0).mean(), 3), "mean_R": round(d.R.mean(), 3), "stopped": round(d.stopped.mean(), 2),
            "funding_bp": round(d.funding.mean() * 1e4, 1), "short_share": round((d.side < 0).mean(), 2),
            "symbols_pos": f"{int((d.groupby('symbol').ret.mean() > 0).sum())}/{d.symbol.nunique()}"}


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    rows, primary = [], None
    for name, zmin, hh in (("V1_z2_24h", 2.0, 24), ("V2_z2_8h", 2.0, 8), ("V3_z3_24h", 3.0, 24)):
        d = pd.DataFrame([x for s in SYMBOLS for x in simulate(s, zmin, hh)])
        d.to_csv(CACHE / f"E23_{name}_trades.csv", index=False)
        for win, g in (("DEV", d[d.t_in < HOLD0]), ("HOLDOUT", d[d.t_in >= HOLD0])):
            rows.append({"variant": name, "window": win, **summarize(g)})
        if name.startswith("V1"):
            primary = d
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "E23_funding_extreme.csv", index=False)
    pd.set_option("display.width", 220)
    print(r.to_string(index=False))
    dv, ho = primary[primary.t_in < HOLD0], primary[primary.t_in >= HOLD0]
    sd, sh = summarize(dv), summarize(ho)
    pos = int(sd["symbols_pos"].split("/")[0])
    ok = (sd["n"] >= 200 and sd["mean_bp"] >= 10 and (sd["t"] or 0) >= 2 and pos >= 6
          and sh["mean_bp"] > 0 and sh["mean_bp"] >= 0.5 * sd["mean_bp"])
    print("PRIMARY", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
