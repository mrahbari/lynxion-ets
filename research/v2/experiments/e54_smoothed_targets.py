"""E54 — Smoothed XS-COMBO-V1 targets: cost reduction on F1 (PRE-REGISTERED 2026-11-27; REPO_STUDY section 6).

Source idea: EWM smoothing of target weights to cut turnover (Gautam-Kanna/crypto-momentum-reversal, `port.ewm`).
Rule (one fixed half-step, no grid): the weekly target is 0.5 x V1 target(t) + 0.5 x V1 target(t - 7 days).
Everything else frozen V1 (live-like universe, 20 %/20 %, weekly, lib.backtest costs, funding, drift); 7 phases paired.
Windows: DEV 2020-01..2024-12, TEST 2025-01..2026-10 (the second has been read before -> a pass leads only to a
prospective shadow, never to direct adoption).
PASS: phase-mean net Sharpe higher than V1 in BOTH windows AND mean turnover cut >= 25 % in both.
Usage: cd research/v2 && python experiments/e54_smoothed_targets.py
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


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    fr = pn.forward_returns(p)
    w = bt.rank_long_short(S.signal(p, mask), mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
    ws = 0.5 * w + 0.5 * w.shift(P["rebalance_every"]).fillna(0.0)
    rows = []
    for win, (a0, b0) in WINDOWS.items():
        for k in range(7):
            a = pd.Timestamp(a0, tz="UTC") + pd.Timedelta(days=k)
            for name, W in (("V1", w), ("SMOOTH", ws)):
                ww = W[(W.index >= a) & (W.index <= b0)]
                r = bt.run(ww, fr.reindex(ww.index), p, bt.CostModel(), rebalance_every=P["rebalance_every"])
                y = r.net.iloc[:-1]
                eq = (1 + y).cumprod()
                rows.append({"window": win, "phase": k, "book": name, "ann": y.mean() * 365,
                             "sharpe": y.mean() / y.std() * np.sqrt(365), "cost": r.cost.iloc[:-1].mean() * 365,
                             "turnover": r.turnover.iloc[:-1].mean() * 365, "gross": r.gross_exposure.iloc[:-1].mean(),
                             "price": r.gross.iloc[:-1].mean() * 365, "funding": r.funding.iloc[:-1].mean() * 365,
                             "mdd": float((eq / eq.cummax() - 1).min())})
    res = pd.DataFrame(rows)
    res.to_csv(ROOT / "docs/v2/reports/E54_smoothed_targets_by_phase.csv", index=False)
    g = res.groupby(["window", "book"]).mean(numeric_only=True).drop(columns="phase").round(4)
    pd.set_option("display.width", 200)
    print(g.to_string())
    ok = True
    for win in WINDOWS:
        v, s = g.loc[(win, "V1")], g.loc[(win, "SMOOTH")]
        cut = 1 - s.turnover / v.turnover
        sh = res.pivot_table(index=["window", "phase"], columns="book", values="sharpe").loc[win]
        print(f"{win}: Sharpe {v.sharpe:.3f} -> {s.sharpe:.3f} (phases better {int((sh.SMOOTH > sh.V1).sum())}/7), turnover cut {cut:.1%}")
        ok &= bool(s.sharpe > v.sharpe and cut >= 0.25)
    print("E54", "PASS -> prospective shadow" if ok else "FAIL")


if __name__ == "__main__":
    main()
