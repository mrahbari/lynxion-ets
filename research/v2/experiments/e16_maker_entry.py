"""E16 — maker (post-only limit) entries vs market entries on the platform strategies' trades (roadmap E8-1).

Question: does entering with a post-only limit instead of MARKET raise PnL once missed fills and adverse
selection (winners run away without filling) are counted?

Pre-registered before running (2026-11-23); nothing changed after seeing results.
  Trades: E9 trades (market entry at the open P0 of bar t+1, 2 bp slippage, 0.05 % taker; R = ret / sl_pct).
  Limit: post-only at P0, placed at t_in. Fill (conservative queue): BUY fills in the first 1m bar inside
    [t_in, t_in + W) whose low <= P0 x (1 - 1 bp); SELL: high >= P0 x (1 + 1 bp). Fill time = end of that bar.
  Filled trade: same exit as E9 (SL/TP levels are absolute; price passes P0 before reaching the SL, so an SL
    cannot precede the fill). Exit before the fill time (TP/trail ran away) -> missed. Filled ret = E9 ret +
    0.0005 (no 2 bp entry slippage, maker 0.02 % instead of taker 0.05 %).
  Variants: W in {5, 15} min; (cancel) unfilled -> no trade (R 0);
    (fallback) unfilled -> MARKET at the open P_W of the 1m bar at t_in + W: ret = E9 ret - side x (P_W - P0)/P0
    (approximation: same exit; if the E9 exit came before t_in + W the trade is counted as missed).
  Metric: total R per signal (missed = 0), i.e. PnL. Also reported: fill rate, mean E9 R of filled vs
    missed (adverse selection), edge-neutral gain = (maker - market) per signal after removing each period's
    base mean R from the missed trades (what the change would be worth for a zero-edge strategy).
  PASS: a variant beats MARKET by >= +0.02 R per signal on BOTH DEV and HOLDOUT, and its edge-neutral gain
    is > 0 on both (so the gain is not just "skipping losing trades").

Usage: python research/v2/experiments/e16_maker_entry.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402
import e12_watcher_role_filters as e12  # noqa: E402

OUT = e9.OUT
DEV0, HOLD0 = e12.DEV0, e12.HOLD0
M = 60_000
GAIN = 0.0005
TOL = 1e-4


def simulate(g: pd.DataFrame, k: pd.DataFrame, w_min: int) -> pd.DataFrame:
    t, lo, hi, op = k.t.to_numpy(), k.l.to_numpy(), k.h.to_numpy(), k.o.to_numpy()
    rows = []
    for tr in g.itertuples(index=False):
        i0 = np.searchsorted(t, tr.t_in)
        i1 = np.searchsorted(t, tr.t_in + w_min * M)
        if i0 >= len(t) or t[i0] != tr.t_in:
            rows.append((np.nan, np.nan, np.nan))
            continue
        p0 = op[i0]
        buy = tr.side == "BUY"
        hit = (lo[i0:i1] <= p0 * (1 - TOL)) if buy else (hi[i0:i1] >= p0 * (1 + TOL))
        fill_t = t[i0 + int(np.argmax(hit))] + M if hit.any() else np.nan
        pw = op[i1] if i1 < len(op) else np.nan
        rows.append((fill_t, p0, pw))
    f = pd.DataFrame(rows, columns=["fill_t", "p0", "pw"], index=g.index)
    return g.join(f)


def evaluate(d: pd.DataFrame) -> dict:
    sgn = np.where(d.side == "BUY", 1.0, -1.0)
    filled = d.fill_t.notna() & (d.t_out >= d.fill_t)
    r_fill = (d.ret + GAIN) / d.sl_pct
    cancel = np.where(filled, r_fill, 0.0)
    late = d.t_out < d.t_in + d.W * M
    fb_ret = d.ret - sgn * (d.pw - d.p0) / d.p0
    fallback = np.where(filled, r_fill, np.where(late | d.pw.isna(), 0.0, fb_ret / d.sl_pct))
    base = d.R.mean()
    neutral_cancel = np.where(filled, r_fill - d.R, -(d.R - base))
    neutral_fb = np.where(filled, r_fill - d.R, np.where(late | d.pw.isna(), -(d.R - base),
                                                         fb_ret / d.sl_pct - d.R))
    return {"n": len(d), "fill_rate": round(float(filled.mean()), 3),
            "market_R": round(float(d.R.mean()), 4),
            "cancel_R": round(float(cancel.mean()), 4), "fallback_R": round(float(fallback.mean()), 4),
            "cancel_gain": round(float(cancel.mean() - d.R.mean()), 4),
            "fallback_gain": round(float(fallback.mean() - d.R.mean()), 4),
            "cancel_neutral_gain": round(float(neutral_cancel.mean()), 4),
            "fallback_neutral_gain": round(float(neutral_fb.mean()), 4),
            "filled_E9_R": round(float(d.R[filled].mean()), 3), "missed_E9_R": round(float(d.R[~filled].mean()), 3),
            "missed_win_rate": round(float((d.R[~filled] > 0).mean()), 3),
            "filled_win_rate": round(float((d.R[filled] > 0).mean()), 3)}


def main() -> None:
    tr = pd.read_csv(OUT / "E9_strategy_backtest_trades.csv")
    sims = []
    for sym, g in tr.groupby("symbol"):
        k = e9.klines(sym, "1m").sort_values("t").reset_index(drop=True)
        for w in (5, 15):
            sims.append(simulate(g, k, w).assign(W=w))
    d = pd.concat(sims)
    d = d[d.p0.notna()]
    rows = []
    for w in (5, 15):
        for name, part in (("DEV", d[(d.W == w) & (d.t_in >= DEV0) & (d.t_in < HOLD0)]),
                           ("HOLDOUT", d[(d.W == w) & (d.t_in >= HOLD0)])):
            rows.append({"W_min": w, "period": name, **evaluate(part)})
    r = pd.DataFrame(rows)
    for v in ("cancel", "fallback"):
        for w in (5, 15):
            x = r[r.W_min == w]
            ok = bool((x[f"{v}_gain"] >= 0.02).all() and (x[f"{v}_neutral_gain"] > 0).all())
            r.loc[r.W_min == w, f"{v}_pass"] = ok
    per = []
    for (w, st), g in d[d.t_in >= HOLD0].groupby(["W", "strategy"]):
        per.append({"W_min": w, "strategy": st, **evaluate(g)})
    r.to_csv(OUT / "E16_maker_entry.csv", index=False)
    pd.DataFrame(per).to_csv(OUT / "E16_maker_entry_per_strategy_holdout.csv", index=False)
    pd.set_option("display.width", 250)
    print(r.T.to_string())
    print(pd.DataFrame(per)[["W_min", "strategy", "n", "fill_rate", "market_R", "cancel_R", "fallback_R",
                             "cancel_neutral_gain", "fallback_neutral_gain"]].to_string(index=False))


if __name__ == "__main__":
    main()
