"""E29 — daily Donchian-ensemble trend with volatility targeting (literature, 2026-11-24).

Source: Zarattini, Pagani, Barbon, "Catching Crypto Trends" (Swiss Finance Institute RP 25-80, 2025): an
ensemble of Donchian-channel trend models over several lookbacks, positions sized to a 25 % annualised
volatility target (allocation capped at 200 %), long-only across liquid crypto assets; reported ~18 % net CAGR
and ~11 % alpha vs BTC (2015-2025), Sharpe ~1.6 on BTC. Independent support: intraday perp returns show no
out-of-sample predictability (two 2026 papers; our E9-E28), while our trend exits only worked in trending
periods (E26, E27) — i.e. trend lives at daily+ horizons. Distinct from Codex C-14/C-15 (single 180-day
momentum with a fixed 28-day hold).

Pre-registered (2026-11-24, committed before any run). No search; values from the paper / textbook.
  Data: Binance USDT-M 1h klines + funding (data/research_cache/e23), resampled to UTC days.
  Universe: BTC ETH SOL XRP DOGE AVAX LINK SUI ADA LTC (each from its listing, >= 300 days of history).
  DEV 2020-01-01..2024-12-31; HOLDOUT 2025-01-01..2026-10-31 (read once).
  Signal per coin and lookback N in {10, 20, 30, 60, 90, 150, 250} days: long after a close above the
    highest close of the previous N days; flat after a close below the lowest close of the previous N/2 days.
    Ensemble signal = mean over lookbacks (0..1). LONG-ONLY (primary); LONG-SHORT mirror reported.
  Sizing: coin weight = signal x min(2, 0.25 / sigma_60d_ann) / n_coins (sigma from daily log returns).
  Timing: weights from day t's close are held over day t+1 (one-day lag; no same-day use).
  Costs: 10 bp per unit of turnover (fees + slippage); funding paid/received at the real Binance rates on the
    held notional (long pays positive funding).
  PASS (long-only): net Sharpe >= 0.8 on DEV AND >= 0.4 on HOLDOUT, AND max drawdown smaller than BTC
    buy-and-hold in both windows. Reported: CAGR, vol, max DD, beta/alpha vs BTC, per-year Sharpe.
  Decision: PASS -> build as a new daily sleeve on VST (shadow first), alongside XS-COMBO.
Usage: python research/v2/experiments/e29_daily_trend_ensemble.py
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
LOOKBACKS = [10, 20, 30, 60, 90, 150, 250]
COST, TARGET, CAP = 0.0010, 0.25, 2.0
DEV = ("2020-01-01", "2024-12-31")
HOLD = ("2025-01-01", "2026-10-31")


def daily(sym):
    k = e23.klines(sym)
    k["d"] = pd.to_datetime(k.t, unit="ms", utc=True).dt.floor("D")
    g = k.groupby("d").agg(c=("c", "last"), n=("c", "size"))
    g = g[g.n == 24].c
    f = e23.funding(sym)
    f["d"] = pd.to_datetime(f.fundingTime, unit="ms", utc=True).dt.floor("D")
    fd = f.groupby("d").fundingRate.sum()
    return g, fd


def signal(c: pd.Series, long_short: bool):
    sigs = []
    for n in LOOKBACKS:
        hi, lo = c.shift(1).rolling(n).max(), c.shift(1).rolling(max(2, n // 2)).min()
        lo_s, hi_s = c.shift(1).rolling(n).min(), c.shift(1).rolling(max(2, n // 2)).max()
        state, out = 0.0, []
        for x, a, b, a2, b2 in zip(c.values, hi.values, lo.values, lo_s.values, hi_s.values):
            if np.isnan(a) or np.isnan(b):
                out.append(np.nan); continue
            if x > a:
                state = 1.0
            elif state > 0 and x < b:
                state = 0.0
            if long_short:
                if x < a2:
                    state = -1.0
                elif state < 0 and x > b2:
                    state = 0.0
            out.append(state)
        sigs.append(pd.Series(out, index=c.index))
    return pd.concat(sigs, axis=1).mean(axis=1)


def run(long_short: bool):
    closes, funds = {}, {}
    for s in SYMS:
        closes[s], funds[s] = daily(s)
    C = pd.DataFrame(closes).sort_index()
    F = pd.DataFrame(funds).reindex(C.index).fillna(0.0)
    R = np.log(C).diff()
    vol = R.rolling(60).std() * np.sqrt(365)
    S = pd.DataFrame({s: signal(C[s].dropna(), long_short) for s in SYMS}).reindex(C.index)
    hist = C.notna().cumsum() >= 300
    W = (S * np.minimum(CAP, TARGET / vol)).where(hist) / len(SYMS)
    W = W.fillna(0.0).shift(1)                       # decided at day t close, held over t+1
    simple = C.pct_change().fillna(0.0)
    gross = (W * simple).sum(axis=1)
    fund = (W * F).sum(axis=1)                       # long (W>0) pays positive funding
    turn = W.diff().abs().sum(axis=1).fillna(0.0)
    net = gross - fund - COST * turn
    return net, gross, turn, C["BTCUSDT"].pct_change().fillna(0.0), W


def stats(r, btc):
    r, btc = r.dropna(), btc.reindex(r.index).fillna(0.0)
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    beq = (1 + btc).cumprod()
    bdd = (beq / beq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else 0.0
    bsh = btc.mean() / btc.std() * np.sqrt(365)
    beta = np.cov(r, btc)[0, 1] / btc.var()
    alpha = (r.mean() - beta * btc.mean()) * 365
    yrs = len(r) / 365
    return {"sharpe": round(sh, 2), "cagr": round(eq.iloc[-1] ** (1 / yrs) - 1, 3), "vol": round(r.std() * np.sqrt(365), 3),
            "max_dd": round(dd, 3), "btc_sharpe": round(bsh, 2), "btc_max_dd": round(bdd, 3),
            "beta": round(beta, 2), "alpha_ann": round(alpha, 3)}


def main():
    rows = []
    for ls in (False, True):
        net, gross, turn, btc, W = run(ls)
        for name, (a, b) in (("DEV", DEV), ("HOLDOUT", HOLD)):
            m = (net.index >= pd.Timestamp(a, tz="UTC")) & (net.index <= pd.Timestamp(b, tz="UTC"))
            st = stats(net[m], btc[m])
            rows.append({"variant": "LONG_SHORT" if ls else "LONG_ONLY", "window": name, **st,
                         "gross_sharpe": stats(gross[m], btc[m])["sharpe"],
                         "turnover_per_yr": round(turn[m].sum() / (m.sum() / 365), 1)})
        if not ls:
            yr = net.groupby(net.index.year).apply(lambda x: round(x.mean() / x.std() * np.sqrt(365), 2) if x.std() > 0 else 0)
            print("LONG_ONLY Sharpe by year:", yr.to_dict())
    r = pd.DataFrame(rows)
    r.to_csv(e23.OUT / "E29_daily_trend_ensemble.csv", index=False)
    pd.set_option("display.width", 250)
    print(r.to_string(index=False))
    lo = r[r.variant == "LONG_ONLY"].set_index("window")
    ok = (lo.loc["DEV", "sharpe"] >= 0.8 and lo.loc["HOLDOUT", "sharpe"] >= 0.4
          and lo.loc["DEV", "max_dd"] > lo.loc["DEV", "btc_max_dd"] and lo.loc["HOLDOUT", "max_dd"] > lo.loc["HOLDOUT", "btc_max_dd"])
    print("LONG_ONLY", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
