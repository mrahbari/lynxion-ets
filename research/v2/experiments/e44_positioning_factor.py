"""E44 — cross-sectional POSITIONING factors from Binance metrics (PRE-REGISTERED 2026-11-25, before the data is read).

New information family (never used in E1-E43): account / top-trader long-short ratios from the free Binance daily
`metrics` archive (data/lake/binance_um/metrics_1h, built by data/binance_um_daily.py). Single-symbol open interest was
rejected in E20/E24 and is not re-tested here.

Hypotheses (two factors only, directions fixed now):
  F_RETAIL  contrarian to crowded retail: signal = -mean over the last 3 days of log(all-account long/short ratio)
  F_TOP     follow top traders' positions: signal = +mean over the last 3 days of log(top-trader position ratio)
Daily value for row D = last hourly value whose bucket ended <= D (known at D). Missing metrics -> not eligible.
Machinery: frozen V1 (live-like universe AND metrics available, 20 %/20 %, gross 1, weekly, lib.backtest costs,
funding cash flows). All 7 weekly phases, paired, results averaged over phases.
Windows: DEV 2020-09-01..2023-12-31 and TEST 2024-01-01..2026-10-31 (read once for this family; the market period
itself was seen in other studies, so the evidence is weaker than a clean holdout).
Rules:
  standalone PASS: DEV phase-mean net Sharpe >= 0.75 AND TEST phase-mean net Sharpe > 0.4 AND >= 6/7 TEST phases > 0.
  4th-factor CANDIDATE: V1 + factor (equal weight, 4 centred ranks) beats V1 by annual net delta > 0 in BOTH windows
  with >= 6/7 phases positive in both. A candidate is NOT adopted from history: it goes to a prospective shadow period
  next to V1 (operator decision).
Usage: cd research/v2 && python experiments/e44_positioning_factor.py
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
METRICS = pn.LAKE / "metrics_1h"
WINDOWS = {"DEV": ("2020-09-01", "2023-12-31"), "TEST": ("2024-01-01", "2026-10-31")}


def daily_metric(col: str, index: pd.DatetimeIndex) -> pd.DataFrame:
    out = {}
    for f in METRICS.glob("*.parquet"):
        m = pd.read_parquet(f, columns=["t", col]).dropna()
        if m.empty:
            continue
        s = pd.Series(m[col].to_numpy(), index=pd.to_datetime(m.t, unit="ms", utc=True))
        out[f.stem] = s[s > 0].resample("1D", label="right", closed="right").last()   # value known at day end
    return pd.DataFrame(out).reindex(index)


def main():
    p = pn.load_daily(start="2020-06-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    idx = mask.index
    retail = daily_metric("ls_accounts", idx).reindex(columns=mask.columns)
    top = daily_metric("top_ls_positions", idx).reindex(columns=mask.columns)
    m2 = mask & retail.notna() & top.notna()
    f_retail = -np.log(retail).rolling(3, min_periods=2).mean()
    f_top = np.log(top).rolling(3, min_periods=2).mean()
    fr = pn.forward_returns(p)
    v1 = S.signal(p, m2)
    sigs = {"F_RETAIL": f_retail, "F_TOP": f_top, "V1": v1,
            "V1+RETAIL": v1 + S._rk(f_retail, m2), "V1+TOP": v1 + S._rk(f_top, m2)}
    rows = []
    for name, sig in sigs.items():
        w = bt.rank_long_short(sig, m2, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
        for win, (a0, b0) in WINDOWS.items():
            for k in range(7):
                a = pd.Timestamp(a0, tz="UTC") + pd.Timedelta(days=k)
                ww = w[(w.index >= a) & (w.index <= b0)]
                r = bt.run(ww, fr.reindex(ww.index), p, bt.CostModel(), rebalance_every=P["rebalance_every"])
                y = r.net.iloc[:-1]
                rows.append({"signal": name, "window": win, "phase": k, "ann_net": y.mean() * 365,
                             "sharpe": y.mean() / y.std() * np.sqrt(365), "price": r.gross.iloc[:-1].mean() * 365,
                             "carry": r.funding.iloc[:-1].mean() * 365, "cost": r.cost.iloc[:-1].mean() * 365})
    res = pd.DataFrame(rows)
    res.to_csv(ROOT / "docs/v2/reports/E44_positioning_by_phase.csv", index=False)
    pd.set_option("display.width", 200)
    print("eligible names per day (median):", int(m2.sum(1)[m2.sum(1) > 0].median()))
    print(res.groupby(["signal", "window"])[["ann_net", "sharpe", "price", "carry", "cost"]].mean().round(3).to_string())
    g = res.groupby(["signal", "window"])
    for f in ("F_RETAIL", "F_TOP"):
        ok = (g.sharpe.mean()[(f, "DEV")] >= 0.75 and g.sharpe.mean()[(f, "TEST")] > 0.4
              and (res[(res.signal == f) & (res.window == "TEST")].ann_net > 0).sum() >= 6)
        print(f"{f} standalone: {'PASS' if ok else 'FAIL'}")
    piv = res.pivot_table(index=["window", "phase"], columns="signal", values="ann_net")
    for c in ("V1+RETAIL", "V1+TOP"):
        ok = True
        for win in WINDOWS:
            d = piv.loc[win, c] - piv.loc[win, "V1"]
            print(f"{c} vs V1 {win}: {d.mean():+.4f}/yr, phases + {(d > 0).sum()}/7")
            ok &= bool(d.mean() > 0 and (d > 0).sum() >= 6)
        print(f"{c}: {'CANDIDATE (prospective shadow next)' if ok else 'NOT A CANDIDATE'}")


if __name__ == "__main__":
    main()
