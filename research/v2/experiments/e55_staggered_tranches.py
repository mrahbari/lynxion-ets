"""E55 — Staggered 7-tranche execution of XS-COMBO-V1 (PRE-REGISTERED 2026-11-27; REPO_STUDY section 6).

Source idea: overlapping "desks" (aurelien-gentile/crypto-pairs-trading, six staggered 180-day portfolios averaged).
Design: 7 tranches of 1/7 gross; tranche k rebalances weekly on weekday phase k. The tranche book's daily return is
the mean of the 7 single-phase books (frozen V1 machinery, live-like universe, costs, funding, drift).
Questions and PASS rule (fixed):
  1. Robustness: the cross-phase standard deviation of rolling 182-day net Sharpe (single-phase books) vs the
     tranche book's own rolling Sharpe path. PASS if the tranche Sharpe >= the median single-phase Sharpe in BOTH
     windows (diversification across phases cannot lower the mean, it can only lower the dispersion).
  2. Feasibility at the live book (3,200 USDT gross): share of tranche order deltas below the 6 USDT minimum order
     (orders that would be skipped). PASS if <= 20 % of tranche orders (by count) and <= 5 % of tranche turnover
     (by notional) fall below 6 USDT.
Windows: DEV 2020-01..2024-12, TEST 2025-01..2026-10.
Decision: PASS -> propose switching the live rebalancer to daily tranches (operator decision; live-schedule change).
Usage: cd research/v2 && python experiments/e55_staggered_tranches.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
P = S.PARAMS
WINDOWS = {"DEV": ("2020-01-01", "2024-12-31"), "TEST": ("2025-01-01", "2026-10-31")}
BOOK, MIN_ORDER = 3200.0, 6.0


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    fr = pn.forward_returns(p)
    w = bt.rank_long_short(S.signal(p, mask), mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
    out = {}
    for win, (a0, b0) in WINDOWS.items():
        phases = []
        for k in range(7):
            a = pd.Timestamp(a0, tz="UTC") + pd.Timedelta(days=k)
            ww = w[(w.index >= a) & (w.index <= b0)]
            phases.append(bt.run(ww, fr.reindex(ww.index), p, bt.CostModel(), rebalance_every=P["rebalance_every"]).net.iloc[:-1])
        ph = pd.concat(phases, axis=1).dropna()
        tranche = ph.mean(1)
        sr = lambda y: y.mean() / y.std() * np.sqrt(365)  # noqa: E731
        single = [sr(ph[c]) for c in ph.columns]
        roll = ph.rolling(182).apply(lambda y: y.mean() / y.std() * np.sqrt(365), raw=True)
        roll_t = tranche.rolling(182).apply(lambda y: y.mean() / y.std() * np.sqrt(365), raw=True)
        # feasibility: order deltas per tranche at each phase-k rebalance day (target change x book / 7)
        reb = w.loc[a0:b0]
        d = reb.diff(P["rebalance_every"]).abs() * BOOK / 7
        d = d[d > 0].stack()
        small_n = float((d < MIN_ORDER).mean())
        small_v = float(d[d < MIN_ORDER].sum() / d.sum())
        out[win] = {"tranche_sharpe": round(sr(tranche), 3), "single_median": round(float(np.median(single)), 3),
                    "single_min": round(min(single), 3), "single_max": round(max(single), 3),
                    "rolling_sharpe_dispersion_across_phases": round(float(roll.std(axis=1).mean()), 3),
                    "tranche_rolling_sharpe_std_over_time": round(float(roll_t.std()), 3),
                    "small_orders_share": round(small_n, 3), "small_orders_notional_share": round(small_v, 4)}
        print(win, out[win])
    ok = all(o["tranche_sharpe"] >= o["single_median"] and o["small_orders_share"] <= 0.20
             and o["small_orders_notional_share"] <= 0.05 for o in out.values())
    print("E55", "PASS -> operator decision on daily tranches" if ok else "FAIL")
    pd.DataFrame(out).T.to_csv(ROOT / "docs/v2/reports/E55_staggered_tranches.csv")


if __name__ == "__main__":
    main()
