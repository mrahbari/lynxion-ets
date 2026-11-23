"""E15 — XS-COMBO rank as a filter for the single-symbol strategies (roadmap E9-2).

Why: XS-COMBO-V1 is the only measured edge (holdout SR 1.39 Binance). If its daily cross-sectional score says
where money flows (carry, illiquidity, taker buying), single-symbol trades in the same direction may do better
than trades against it. Unlike the watcher states (E12, E14), this input has proven standalone information.

Pre-registered before running (2026-11-23); nothing changed after seeing results.
  Trades: E9 trades (8 strategies, 10 perps, net of fees, R units).
  Score: frozen XS-COMBO-V1 composite signal, percentile rank within its eligible universe on completed day D,
    usable from D + 25 h (decision 00:00 UTC on D+1 + 1 h execution lag, same as live). Matched backward-asof.
    Symbol not in the universe that day -> state "out".
  States vs trade side: aligned (BUY & rank >= 0.5, or SELL & rank < 0.5) / opposed;
    strict: extreme_aligned (BUY & rank >= 0.8, or SELL & rank <= 0.2) / other.
  DEV (2025-11-01..2026-06-30) cell pass, per strategy x state (same as E12): n >= 100, mean R >= +0.05,
    PF >= 1.2, both time halves > 0, >= 6/10 symbols positive. HOLDOUT (2026-07-01..10-31) read only for DEV
    passes: mean R > 0, PF >= 1.1.
  Reported, no pass/fail: pooled lift (state mean R - strategy mean R) with t-stat, DEV and holdout.

Usage: python research/v2/experiments/e15_xs_rank_filter.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import e9_strategy_backtest as e9  # noqa: E402
import e12_watcher_role_filters as e12  # noqa: E402
from lib import panel as pn  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

OUT = e9.OUT
DEV0, HOLD0, H = e12.DEV0, e12.HOLD0, e12.H


def xs_rank() -> pd.DataFrame:
    P = S.PARAMS
    p = pn.load_daily(start="2025-08-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    rk = S.signal(p, mask).where(mask).rank(axis=1, pct=True)
    long = rk.stack(dropna=False).rename("rank").reset_index()
    long.columns = ["date", "symbol", "rank"]
    long["avail_t"] = (long.date.astype("int64") // 1_000_000 + 25 * H).astype(np.int64)
    return long


def stats(g: pd.DataFrame) -> dict:
    return e12.stats(g)


def lift(d: pd.DataFrame, col: str) -> pd.DataFrame:
    d = d.assign(l=d.R - d.groupby("strategy").R.transform("mean"))
    g = d.groupby(col).l.agg(["size", "mean", "std"])
    return pd.DataFrame({"n": g["size"], "lift_R": g["mean"].round(3),
                         "t": (g["mean"] / (g["std"] / np.sqrt(g["size"]))).round(2)})


def main() -> None:
    tr = pd.read_csv(OUT / "E9_strategy_backtest_trades.csv")
    rk = xs_rank()
    out = []
    for sym, g in tr.groupby("symbol"):
        r = rk[rk.symbol == sym].sort_values("avail_t")[["avail_t", "rank"]]
        out.append(pd.merge_asof(g.sort_values("t_in"), r, left_on="t_in", right_on="avail_t", direction="backward"))
    d = pd.concat(out)
    buy = d.side == "BUY"
    d["xs"] = np.where(d["rank"].isna(), "out", np.where(buy == (d["rank"] >= 0.5), "aligned", "opposed"))
    ext = (buy & (d["rank"] >= 0.8)) | (~buy & (d["rank"] <= 0.2))
    d["xs_strict"] = np.where(d["rank"].isna(), "out", np.where(ext, "extreme_aligned", "other"))
    dev, hold = d[(d.t_in >= DEV0) & (d.t_in < HOLD0)], d[d.t_in >= HOLD0]
    rows = []
    for strat, g in dev.groupby("strategy"):
        base = g.R.mean()
        for filt in ("xs", "xs_strict"):
            for state, gg in g.groupby(filt):
                s = stats(gg)
                s.update(strategy=strat, filter=filt, state=state, lift_R=round(gg.R.mean() - base, 3))
                s["dev_pass"] = bool(s["n"] >= 100 and s["mean_R"] >= 0.05 and s["PF"] >= 1.2 and s["h1_R"] > 0
                                     and s["h2_R"] > 0 and s["symbols_positive"] >= 6)
                hh = hold[(hold.strategy == strat) & (hold[filt] == state)]
                if s["dev_pass"]:
                    hs = stats(hh) if len(hh) > 1 else {"n": len(hh)}
                    s.update({f"holdout_{k}": v for k, v in hs.items()})
                    s["holdout_pass"] = bool(len(hh) > 1 and hs["mean_R"] > 0 and hs["PF"] >= 1.1)
                rows.append(s)
    r = pd.DataFrame(rows)
    cols = ["strategy", "filter", "state", "n", "mean_R", "lift_R", "PF", "h1_R", "h2_R", "symbols_positive", "dev_pass"]
    r = r[cols + [c for c in r.columns if c not in cols]]
    r.to_csv(OUT / "E15_xs_rank_filter.csv", index=False)
    pooled = []
    for name, part in (("DEV", dev), ("HOLDOUT", hold)):
        for filt in ("xs", "xs_strict"):
            pooled.append(lift(part, filt).reset_index().rename(columns={filt: "state"}).assign(period=name, filter=filt))
    pooled = pd.concat(pooled)[["period", "filter", "state", "n", "lift_R", "t"]]
    pooled.to_csv(OUT / "E15_xs_rank_filter_pooled.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(f"trades: DEV {len(dev)}, HOLDOUT {len(hold)}; matched rank: {d['rank'].notna().mean():.2%}")
    print(f"cells: {len(r)}; DEV passes: {int(r.dev_pass.sum())}")
    print(r.to_string(index=False))
    print(pooled.to_string(index=False))


if __name__ == "__main__":
    main()
