"""E31 — cross-sectional short-term reversal, market-neutral, daily (roadmap R6, 2026-11-24).

Source: short-term reversal effect in crypto cross-section (four-factor crypto asset pricing model, 2025;
pervasive short-horizon reversal, matched cross-market measurement, 2026). Distinct from Codex C-06 (extreme
movers only): here the whole liquid universe is ranked.
Pre-registered (committed before any run). XS-COMBO-V1 panel, universe mask and cost model.
  signal = -(log return of the last completed day); long bottom 20 %, short top 20 %, gross 1.0, dollar-neutral,
  rebalanced DAILY (the effect is short-horizon). Costs = the XS-COMBO cost model (fees, spread, impact).
  DEV 2020-01-01..2024-12-31; HOLDOUT 2025-01-01..2026-10-31 (read once).
  PASS: net Sharpe >= 0.75 on DEV and > 0.4 on HOLDOUT, both 2025 and 2026 positive.
  Reported: gross Sharpe (to separate signal from cost), turnover.
Usage: cd research/v2 && python experiments/e31_xs_short_term_reversal.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn, stats as st  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

P = S.PARAMS
WINDOWS = {"DEV": ("2020-01-01", "2024-12-31"), "HOLDOUT": ("2025-01-01", "2026-10-31")}


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    fr = pn.forward_returns(p)
    sig = -np.log(p["close"]).diff()
    rows = []
    for win, (a, b) in WINDOWS.items():
        w = bt.rank_long_short(sig, mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
        w = w[(w.index >= a) & (w.index <= b)]
        r = bt.run(w, fr.reindex(w.index), p, bt.CostModel(cost_mult=1.0), rebalance_every=1)
        y = r.net.dropna().iloc[:-1]
        rows.append({"window": win, "net_sharpe": round(st.sharpe(y), 2), "gross_sharpe": round(st.sharpe(r.gross.loc[y.index]), 2),
                     "ann_net": round(float(y.mean() * 365), 3), "ann_cost": round(float(-r.cost.loc[y.index].mean() * 365), 3),
                     "turnover_per_day": round(float(r.turnover.loc[y.index].mean()), 2),
                     "by_year": {str(k): round(st.sharpe(g), 2) for k, g in y.groupby(y.index.year)}})
    t = pd.DataFrame(rows)
    t.to_csv(Path(__file__).resolve().parents[3] / "docs/v2/reports/E31_xs_short_term_reversal.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    print(t.to_string(index=False))
    g = t.set_index("window")
    ok = (g.loc["DEV", "net_sharpe"] >= 0.75 and g.loc["HOLDOUT", "net_sharpe"] > 0.4
          and all(v > 0 for v in g.loc["HOLDOUT", "by_year"].values()))
    print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
