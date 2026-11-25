"""E40 — XS-COMBO-V1 factor ablation: incremental value of each ranking factor (PRE-REGISTERED, 2026-11-25).

Question: does each of the three frozen factors (21-day funding carry, 30-day Amihud illiquidity, 7-day taker
imbalance) add measurable value, net of costs, beyond the others? Evidence only: no live change, no new combination
is selected or promoted, no parameter / weight / lookback / rebalance-day search.

Variants (frozen definitions and parameters from strategies/xs_combo_v1.py; equal-weight sum of centred ranks):
  A = carry            B = carry + illiq            C = carry + taker            D = carry + illiq + taker (= V1, live)
Everything else identical to the frozen baseline: live-like universe (non-perpetual symbols excluded), long top 20 % /
short bottom 20 %, gross 1, weekly rebalance, lib.backtest cost model (fee + ADV half-spread + sqrt impact), funding
cash flows, drift between rebalances.
Phases: all 7 weekly rebalance offsets, every comparison PAIRED within a phase; no phase is selected.
Windows: DEV 2020-01..2024-12 (the window the combination was designed on -> increments there are biased upward)
  and HOLDOUT_USED 2025-01..2026-10 (seen once for V1 and in E30-E32/E38/E39). Both are EXPLORATORY evidence.
Predefined comparisons (5 per window, Holm over all 10):
  illiq | carry        = B - A        taker | carry        = C - A        full vs carry-only = D - A
  illiq | carry+taker  = D - C        taker | carry+illiq  = D - B
  Test statistic: phase-averaged daily net-return difference, summed into non-overlapping weeks, t on weekly sums.
Supported incremental value (per factor, both conditional comparisons of that factor): annual delta > 0 in BOTH
  windows, delta > 0 in >= 6 of 7 phases in both windows, and Holm p < 0.05 in at least one window with the same sign
  in the other. Anything else: "not supported by evidence" (reported, no replacement proposed).
Reported per variant and phase: net return, Sharpe, price leg, funding carry, cost, turnover, max drawdown, gross.
Usage: cd research/v2 && python experiments/e40_xs_combo_factor_ablation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
P = S.PARAMS
WINDOWS = {"DEV": ("2020-01-01", "2024-12-31"), "HOLDOUT_USED": ("2025-01-01", "2026-10-31")}
COMPARISONS = {"illiq|carry": ("B", "A"), "taker|carry": ("C", "A"), "full_vs_carry": ("D", "A"),
               "illiq|carry+taker": ("D", "C"), "taker|carry+illiq": ("D", "B")}


def holm(p):
    p = np.asarray(p, float)
    order, m, adj, run = np.argsort(p), len(p), np.empty(len(p)), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * p[i]))
        adj[i] = run
    return adj


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    fr = pn.forward_returns(p)
    lr = np.log(p["close"]).diff()
    qv = p["quote_volume"]
    carry = S._rk(-p["funding_past"].rolling(P["funding_window"], min_periods=1).sum(), mask)
    illiq = S._rk((lr.abs() / qv).rolling(P["illiq_window"], min_periods=20).mean(), mask)
    taker = S._rk((p["taker_buy_quote"] / qv - 0.5).rolling(P["taker_window"], min_periods=4).mean(), mask)
    sigs = {"A": carry, "B": carry + illiq, "C": carry + taker, "D": carry + illiq + taker}
    assert np.allclose(sigs["D"].fillna(0).values, S.signal(p, mask).fillna(0).values)   # D is exactly V1
    W = {k: bt.rank_long_short(s, mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"]) for k, s in sigs.items()}

    rows, daily = [], {}
    for win, (a0, b0) in WINDOWS.items():
        for k in range(7):
            a = pd.Timestamp(a0, tz="UTC") + pd.Timedelta(days=k)
            for v, w in W.items():
                ww = w[(w.index >= a) & (w.index <= b0)]
                r = bt.run(ww, fr.reindex(ww.index), p, bt.CostModel(), rebalance_every=P["rebalance_every"])
                y = r.net.iloc[:-1]
                eq = (1 + y).cumprod()
                daily[(win, k, v)] = y
                rows.append({"window": win, "phase": k, "variant": v, "ann_net": y.mean() * 365,
                             "sharpe": y.mean() / y.std() * np.sqrt(365), "price": r.gross.iloc[:-1].mean() * 365,
                             "carry": r.funding.iloc[:-1].mean() * 365, "cost": r.cost.iloc[:-1].mean() * 365,
                             "turnover": r.turnover.iloc[:-1].mean() * 365, "mdd": float((eq / eq.cummax() - 1).min()),
                             "gross": r.gross_exposure.iloc[:-1].mean()})
    res = pd.DataFrame(rows)
    res.to_csv(ROOT / "docs/v2/reports/E40_factor_ablation_by_phase.csv", index=False)
    pd.set_option("display.width", 220)
    summ = res.groupby(["window", "variant"])[["ann_net", "sharpe", "price", "carry", "cost", "turnover", "mdd"]].agg(
        ["mean", "min", "max"]).round(3)
    print(summ.to_string())

    cmp_rows = []
    for win in WINDOWS:
        for name, (x, y) in COMPARISONS.items():
            per = [float(daily[(win, k, x)].mean() - daily[(win, k, y)].reindex(daily[(win, k, x)].index).mean()) * 365
                   for k in range(7)]
            diff = pd.concat([(daily[(win, k, x)] - daily[(win, k, y)]) for k in range(7)], axis=1).mean(1).dropna()
            wk = diff.groupby(np.arange(len(diff)) // 7).sum()
            tv = wk.mean() / (wk.std(ddof=1) / np.sqrt(len(wk)))
            cmp_rows.append({"window": win, "comparison": name, "delta_ann": round(float(np.mean(per)), 4),
                             "delta_min": round(min(per), 4), "delta_max": round(max(per), 4),
                             "phases_pos": int(sum(d > 0 for d in per)), "t_weekly": round(float(tv), 2),
                             "p": float(2 * tdist.sf(abs(tv), len(wk) - 1))})
    c = pd.DataFrame(cmp_rows)
    c["p_holm"] = holm(c.p).round(4)
    c.to_csv(ROOT / "docs/v2/reports/E40_factor_ablation_comparisons.csv", index=False)
    print(c.drop(columns="p").to_string(index=False))

    for factor, names in {"illiq": ["illiq|carry", "illiq|carry+taker"], "taker": ["taker|carry", "taker|carry+illiq"]}.items():
        ok = True
        for n in names:
            g = c[c.comparison == n].set_index("window")
            same_sign = (np.sign(g.t_weekly) == np.sign(g.delta_ann)).all()
            ok &= bool((g.delta_ann > 0).all() and (g.phases_pos >= 6).all() and (g.p_holm < 0.05).any() and same_sign)
        print(f"{factor}: incremental value {'SUPPORTED' if ok else 'NOT SUPPORTED by evidence'}")


if __name__ == "__main__":
    main()
