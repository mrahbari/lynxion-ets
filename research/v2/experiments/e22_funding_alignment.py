"""E22 — does funding-carry alignment separate the platform setups' trades? (Strategy layer, 2026-11-24)

Why: the only validated edge in the project (XS-COMBO-V1, frozen holdout SR 1.39) is almost entirely
funding (ann. funding +0.40, price -0.004); ~35 price-only technical candidates (Codex register) and
E9/E20/E21 found no net edge. Hypothesis: crowding shows in funding; entries on the side that RECEIVES
funding (short when funding > 0, long when funding < 0) do better than entries against it.

Data: the E9 trade list (unchanged adapters, live-equivalent execution, costs included;
docs/v2/reports/E9_strategy_backtest_trades.csv) + Binance USDT-M funding history (public API).
Funding known at entry = the last settled rate with fundingTime <= t_in (causal).

Pre-registered (2026-11-24, committed before any run):
  aligned  = (side SELL and funding > 0) or (side BUY and funding < 0); against = the opposite; zero excluded.
  Per strategy and pooled: mean net R of aligned vs against.
  PASS (pooled, and reported per strategy): aligned mean net R >= +0.03 AND aligned - against >= 0.05 R,
  on DEV AND on HOLDOUT, with n(aligned) >= 300 in each.
  Decision: PASS -> add a funding-alignment gate to the live platform setups (shadow first, then enforce).
  FAIL -> record; funding stays with the XS-COMBO sleeve and E16-U4.
Usage: python research/v2/experiments/e22_funding_alignment.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402

HOLD0 = int(e9.HOLDOUT_START.timestamp() * 1000)


def funding(sym: str) -> pd.DataFrame:
    f = e9.CACHE / f"{sym}_funding.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows, t, end = [], int(e9.START.timestamp() * 1000), int(e9.END.timestamp() * 1000)
    while t < end:
        u = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&startTime={t}&limit=1000"
        batch = json.loads(urllib.request.urlopen(u, timeout=30).read())
        if not batch:
            break
        rows += batch
        t = batch[-1]["fundingTime"] + 1
        time.sleep(0.2)
    d = pd.DataFrame(rows)[["fundingTime", "fundingRate"]].astype({"fundingTime": "int64", "fundingRate": float})
    d.to_parquet(f)
    return d


def main() -> None:
    tr = pd.read_csv(e9.OUT / "E9_strategy_backtest_trades.csv")
    parts = []
    for sym, g in tr.groupby("symbol"):
        fr = funding(sym).sort_values("fundingTime")
        g = pd.merge_asof(g.sort_values("t_in"), fr, left_on="t_in", right_on="fundingTime", direction="backward")
        parts.append(g)
    d = pd.concat(parts).dropna(subset=["fundingRate"])
    d = d[d.fundingRate != 0]
    d["aligned"] = ((d.side == "SELL") & (d.fundingRate > 0)) | ((d.side == "BUY") & (d.fundingRate < 0))
    d["window"] = np.where(d.t_in >= HOLD0, "HOLDOUT", "DEV")
    rows = []
    for (strat, win), g in list(d.groupby(["strategy", "window"])) + [(("POOLED", w), d[d.window == w]) for w in ("DEV", "HOLDOUT")]:
        a, b = g[g.aligned], g[~g.aligned]
        rows.append({"strategy": strat, "window": win, "n_aligned": len(a), "n_against": len(b),
                     "R_aligned": round(a.R.mean(), 3), "R_against": round(b.R.mean(), 3),
                     "diff": round(a.R.mean() - b.R.mean(), 3), "share_aligned": round(len(a) / len(g), 2)})
    r = pd.DataFrame(rows)
    r.to_csv(e9.OUT / "E22_funding_alignment.csv", index=False)
    pd.set_option("display.width", 200)
    print(r.to_string(index=False))
    p = r[r.strategy == "POOLED"].set_index("window")
    ok = all(p.loc[w, "n_aligned"] >= 300 and p.loc[w, "R_aligned"] >= 0.03 and p.loc[w, "diff"] >= 0.05 for w in ("DEV", "HOLDOUT"))
    print("POOLED", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
