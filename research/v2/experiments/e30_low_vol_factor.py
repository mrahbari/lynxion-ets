"""E30 — cross-sectional low-volatility factor, alone and as a 4th XS-COMBO component (2026-11-24).

Source: low-volatility premium in crypto after 2017 (volatility-sorted portfolios + Fama-MacBeth; "Revisiting the
low-volatility anomaly in cryptocurrency markets", Finance Research Letters 2026); XS-COMBO-V1 does not use it.
Pre-registered (committed before any run). Same panel, universe mask, costs, weekly rebalance and long/short
20 % construction as XS-COMBO-V1 (research/v2/strategies/xs_combo_v1.py, lib/backtest.py).
  LOWVOL: signal = -std(daily log return, 30 d) (long low vol, short high vol).
  COMBO4: XS-COMBO-V1 signal + rank(LOWVOL) (equal weight, 4 components).
  DEV 2020-01-01..2024-12-31 (XS-COMBO-V1 development period); HOLDOUT 2025-01-01..2026-10-31.
  CAVEAT: the HOLDOUT was already used once for XS-COMBO-V1 -> not a clean holdout for COMBO4.
  PASS LOWVOL: net Sharpe >= 0.75 on DEV and > 0.4 on HOLDOUT, both 2025 and 2026 positive.
  COMBO4 better: net Sharpe above XS-COMBO-V1 on DEV AND HOLDOUT -> candidate only; replacing V1 would need
  prospective (live shadow) evidence because of the caveat.
Usage: cd research/v2 && python experiments/e30_low_vol_factor.py
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


def evaluate(sig, mask, fr, p, a, b):
    w = bt.rank_long_short(sig, mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
    w = w[(w.index >= a) & (w.index <= b)]
    r = bt.run(w, fr.reindex(w.index), p, bt.CostModel(cost_mult=1.0), rebalance_every=P["rebalance_every"])
    y = r.net.dropna().iloc[:-1]
    yrs = {str(k): round(st.sharpe(g), 2) for k, g in y.groupby(y.index.year)}
    return {"sharpe": round(st.sharpe(y), 2), "ann_ret": round(float(y.mean() * 365), 3),
            "ann_funding": round(float(r.funding.loc[y.index].mean() * 365), 3), "by_year": yrs}


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    fr = pn.forward_returns(p)
    lr = np.log(p["close"]).diff()
    lowvol = -lr.rolling(30, min_periods=20).std()
    v1 = S.signal(p, mask)
    combo4 = v1 + S._rk(lowvol, mask)
    rows = []
    for name, sig in (("XS-COMBO-V1", v1), ("LOWVOL", lowvol), ("COMBO4", combo4)):
        for win, (a, b) in WINDOWS.items():
            rows.append({"signal": name, "window": win, **evaluate(sig, mask, fr, p, a, b)})
    r = pd.DataFrame(rows)
    out = Path(__file__).resolve().parents[3] / "docs/v2/reports/E30_low_vol_factor.csv"
    r.to_csv(out, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    print(r.to_string(index=False))
    g = r.set_index(["signal", "window"])
    lv_ok = (g.loc[("LOWVOL", "DEV"), "sharpe"] >= 0.75 and g.loc[("LOWVOL", "HOLDOUT"), "sharpe"] > 0.4
             and all(v > 0 for v in g.loc[("LOWVOL", "HOLDOUT"), "by_year"].values()))
    c_better = all(g.loc[("COMBO4", w), "sharpe"] > g.loc[("XS-COMBO-V1", w), "sharpe"] for w in WINDOWS)
    print("LOWVOL", "PASS" if lv_ok else "FAIL", "| COMBO4", "BETTER (candidate)" if c_better else "NOT BETTER")


if __name__ == "__main__":
    main()
