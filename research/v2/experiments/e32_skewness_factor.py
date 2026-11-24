"""E32 — cross-sectional skewness factor on liquid perps (2026-11-24).

Sources: commodity skewness (Fernandez-Perez, Frijns, Fuertes, Miffre 2018) and cross-asset skewness (Baltas
2019), replicated in github.com/rolling-panda-san/notebooks; lottery / MAX effect in crypto returns. Assets with
positively skewed past returns are over-priced (lottery demand) and underperform. Not tested before here or by
Codex (C-01..C-35).
Pre-registered (committed before any run). XS-COMBO-V1 panel, universe mask, cost model, 20 % long/short,
gross 1.0, dollar-neutral, weekly rebalance (as in the sources: monthly/weekly horizon).
  SKEW: signal = -skewness(daily log returns, 60 d, min 40) -> long the most NEGATIVE skew, short the most
        POSITIVE skew.
  Also reported: COMBO4S = XS-COMBO-V1 + rank(SKEW) (candidate only; HOLDOUT already used once for V1).
  DEV 2020-01-01..2024-12-31; HOLDOUT 2025-01-01..2026-10-31 (read once).
  PASS SKEW: net Sharpe >= 0.75 on DEV and > 0.4 on HOLDOUT, both 2025 and 2026 positive.
Usage: cd research/v2 && python experiments/e32_skewness_factor.py
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
    return {"net_sharpe": round(st.sharpe(y), 2), "gross_sharpe": round(st.sharpe(r.gross.loc[y.index]), 2),
            "ann_net": round(float(y.mean() * 365), 3), "ann_funding": round(float(r.funding.loc[y.index].mean() * 365), 3),
            "by_year": {str(k): round(st.sharpe(g), 2) for k, g in y.groupby(y.index.year)}}


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    fr = pn.forward_returns(p)
    lr = np.log(p["close"]).diff()
    skew = -lr.rolling(60, min_periods=40).skew()
    v1 = S.signal(p, mask)
    rows = []
    for name, sig in (("XS-COMBO-V1", v1), ("SKEW", skew), ("COMBO4S", v1 + S._rk(skew, mask))):
        for win, (a, b) in WINDOWS.items():
            rows.append({"signal": name, "window": win, **evaluate(sig, mask, fr, p, a, b)})
    r = pd.DataFrame(rows)
    r.to_csv(Path(__file__).resolve().parents[3] / "docs/v2/reports/E32_skewness_factor.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    print(r.to_string(index=False))
    g = r.set_index(["signal", "window"])
    ok = (g.loc[("SKEW", "DEV"), "net_sharpe"] >= 0.75 and g.loc[("SKEW", "HOLDOUT"), "net_sharpe"] > 0.4
          and all(v > 0 for v in g.loc[("SKEW", "HOLDOUT"), "by_year"].values()))
    better = all(g.loc[("COMBO4S", w), "net_sharpe"] > g.loc[("XS-COMBO-V1", w), "net_sharpe"] for w in WINDOWS)
    print("SKEW", "PASS" if ok else "FAIL", "| COMBO4S", "BETTER (candidate)" if better else "NOT BETTER")


if __name__ == "__main__":
    main()
