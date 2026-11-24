"""E24 — liquidation-flush reversal from open interest (Strategy layer, 2026-11-24).

Why: forced liquidations show as a sharp DROP in open interest together with a sharp price move; once the
forced flow is done, part of the move tends to revert. Different from E20 (fixed 2 % OI drop over 5 bars
inside a momentum setup): here the event is an OI flush relative to the symbol's own recent behaviour.

Pre-registered (2026-11-24, committed before any run). No parameter search.
  Universe: BTC ETH SOL XRP ADA BNB (Binance USDT-M 5m OI metrics; 1h klines; funding history).
  Windows: DEV = start of OI data .. 2024-12-31; HOLDOUT = 2025-01-01 .. 2026-08-29 (OI ends) — read once.
  1h bars. OI of a bar = last 5m snapshot with create_time <= bar close - 5 min (causal).
  dOI = OI_t / OI_{t-4} - 1; dP = close_t / close_{t-4} - 1. z-scores of dOI and dP over the PREVIOUS
  720 bars (30 days), shifted by one bar.
  Event: z(dOI) <= -2.5 AND |z(dP)| >= 2. Long-liquidation flush (dP < 0) -> LONG; short-squeeze flush
  (dP > 0) -> SHORT.
  Entry: next bar open. Exit after H bars at close; protective stop 2 x ATR(14) (High/Low, stop first).
  Costs 5 bp fee + 2 bp slippage per side; real funding during the hold. One position per symbol.
  Variants: V1 H=12 (PRIMARY); V2 H=4; V3 z(dOI) <= -3, H=12.
  PASS (PRIMARY): DEV net mean >= +10 bp, t >= 2.0, n >= 100, >= 4/6 symbols positive; HOLDOUT net mean > 0
  and >= 50 % of DEV mean. PASS -> platform strategy (shadow first). FAIL -> record.
Usage: python research/v2/experiments/e24_oi_flush.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e23_funding_extreme as e23  # noqa: E402

OI_DIR = e23.ROOT / "data" / "research" / "oi_metrics" / "normalized"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "BNBUSDT"]
HOLD0 = e23.HOLD0
OI_END = int(datetime(2026, 8, 30, tzinfo=timezone.utc).timestamp() * 1000)
H = e23.H


def bars(sym):
    k = e23.klines(sym).copy()
    oi = pd.read_csv(OI_DIR / f"{sym}.csv.gz", usecols=["create_time", "sum_open_interest"])
    oi["ts"] = pd.to_datetime(oi.create_time, utc=True).astype("int64") // 1_000_000
    k["avail"] = k.t + H - 300_000
    k = pd.merge_asof(k.sort_values("avail"), oi.sort_values("ts")[["ts", "sum_open_interest"]],
                      left_on="avail", right_on="ts", direction="backward", tolerance=900_000)
    k = k.rename(columns={"sum_open_interest": "oi"}).sort_values("t").reset_index(drop=True)
    k["doi"] = k.oi / k.oi.shift(4) - 1
    k["dp"] = k.c / k.c.shift(4) - 1
    for col in ("doi", "dp"):
        r = k[col].rolling(720, min_periods=500)
        k[f"z_{col}"] = ((k[col] - r.mean().shift(1)) / r.std().shift(1))
    tr = np.maximum(k.h - k.l, np.maximum((k.h - k.c.shift()).abs(), (k.l - k.c.shift()).abs()))
    k["atr"] = tr.rolling(14).mean()
    return k


def simulate(sym, zoi, hold):
    k, fr = bars(sym), e23.funding(sym)
    t, o, h, l, c = (k[x].to_numpy() for x in ("t", "o", "h", "l", "c"))
    zo, zp, dp, atr = k.z_doi.to_numpy(), k.z_dp.to_numpy(), k.dp.to_numpy(), k.atr.to_numpy()
    ft, f = fr.fundingTime.to_numpy(), fr.fundingRate.to_numpy()
    trades, i = [], 800
    while i < len(t) - hold - 1:
        if t[i] >= OI_END:
            break
        if np.isfinite(zo[i]) and np.isfinite(zp[i]) and zo[i] <= zoi and abs(zp[i]) >= 2 and np.isfinite(atr[i]):
            side = 1 if dp[i] < 0 else -1
            e_i = i + 1
            entry = o[e_i] * (1 + side * e23.SLIP)
            stop = entry - side * 2 * atr[i]
            exit_px, x_i = None, e_i + hold - 1
            for m in range(e_i, e_i + hold):
                if (side > 0 and l[m] <= stop) or (side < 0 and h[m] >= stop):
                    gap = (side > 0 and o[m] < stop) or (side < 0 and o[m] > stop)
                    exit_px, x_i = (o[m] if gap else stop), m
                    break
            if exit_px is None:
                exit_px = c[x_i]
            exit_px *= (1 - side * e23.SLIP)
            paid = f[(ft > t[e_i]) & (ft <= t[x_i] + H)].sum()
            ret = side * (exit_px / entry - 1) - side * paid - 2 * e23.FEE
            trades.append({"symbol": sym, "t_in": int(t[e_i]), "side": side, "ret": ret,
                           "R": ret / (2 * atr[i] / entry), "stopped": x_i < e_i + hold - 1, "funding": -side * paid})
            i = x_i + 1
            continue
        i += 1
    return trades


def main():
    rows, primary = [], None
    for name, zoi, hold in (("V1_z2.5_12h", -2.5, 12), ("V2_z2.5_4h", -2.5, 4), ("V3_z3_12h", -3.0, 12)):
        d = pd.DataFrame([x for s in SYMBOLS for x in simulate(s, zoi, hold)])
        d.to_csv(e23.CACHE / f"E24_{name}_trades.csv", index=False)
        for win, g in (("DEV", d[d.t_in < HOLD0]), ("HOLDOUT", d[d.t_in >= HOLD0])):
            rows.append({"variant": name, "window": win, **e23.summarize(g)})
        if name.startswith("V1"):
            primary = d
    r = pd.DataFrame(rows)
    r.to_csv(e23.OUT / "E24_oi_flush.csv", index=False)
    pd.set_option("display.width", 220)
    print(r.to_string(index=False))
    sd, sh = e23.summarize(primary[primary.t_in < HOLD0]), e23.summarize(primary[primary.t_in >= HOLD0])
    ok = (sd["n"] >= 100 and sd["mean_bp"] >= 10 and (sd["t"] or 0) >= 2 and int(sd["symbols_pos"].split("/")[0]) >= 4
          and sh["mean_bp"] > 0 and sh["mean_bp"] >= 0.5 * sd["mean_bp"])
    print("PRIMARY", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
