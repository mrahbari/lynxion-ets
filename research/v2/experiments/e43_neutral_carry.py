"""E43 — R20: price-risk-neutral funding carry (PRE-REGISTERED, 2026-11-25). Evidence only, no live change.

Why (E40/E41): carry alone collected +51 %/yr funding in 2025-26 but lost -78 %/yr on price (crowded names kept
rallying). In V1 the illiquidity and taker factors offset that by diversification. Hypothesis: part of the carry book's
price loss is a volatility / beta tilt (high-funding names are high-vol, high-beta). Ranking carry WITHIN volatility or
beta buckets removes the tilt and keeps the funding.

Construction (fixed; frozen V1 machinery otherwise: live-like universe, 20 %/20 %, gross 1, weekly, cost model, funding):
  A      carry only (as E40)
  A_VN   carry ranked within terciles of 30-day daily-return volatility (bucket-wise centred percentile rank)
  A_BN   carry ranked within terciles of 60-day beta to the equal-weight universe return
  D      V1 (carry + illiq + taker)
  D_VN   V1 with its carry component replaced by the vol-neutral carry rank
All 7 weekly phases, paired; windows 2020-01..2024-12 and 2025-01..2026-10 (both EXPLORATORY: the second has been
read many times). Decision by the phase-paired rule below (no p-values).
Comparisons and rule:
  C1 A_VN vs A, C2 A_BN vs A: neutral carry is "better" if annual net delta > 0 in BOTH windows, >= 6/7 phases positive
     in both, and its price-leg loss is smaller in the 2025-26 window.
  C3 D_VN vs D: a replacement CANDIDATE for V1 only if delta > 0 in both windows and >= 6/7 phases in both; even then
     adoption needs a prospective shadow period (operator decision), because the second window is not clean.
Usage: cd research/v2 && python experiments/e43_neutral_carry.py
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
WINDOWS = {"DEV": ("2020-01-01", "2024-12-31"), "HOLDOUT_USED": ("2025-01-01", "2026-10-31")}


def bucket_rank(x: pd.DataFrame, by: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    """Centred percentile rank of x computed separately inside terciles of `by` (per date)."""
    xb = by.where(mask)
    terc = xb.rank(axis=1, pct=True).apply(lambda r: np.ceil(r * 3).clip(1, 3), axis=1)
    out = pd.DataFrame(np.nan, index=x.index, columns=x.columns)
    for b in (1, 2, 3):
        m = mask & (terc == b)
        r = x.where(m).rank(axis=1, pct=True)
        out = out.combine_first(r.sub(r.mean(1), axis=0))
    return out


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    fr = pn.forward_returns(p)
    lr = np.log(p["close"]).diff()
    qv = p["quote_volume"]
    carry_raw = -p["funding_past"].rolling(P["funding_window"], min_periods=1).sum()
    carry = S._rk(carry_raw, mask)
    illiq = S._rk((lr.abs() / qv).rolling(P["illiq_window"], min_periods=20).mean(), mask)
    taker = S._rk((p["taker_buy_quote"] / qv - 0.5).rolling(P["taker_window"], min_periods=4).mean(), mask)
    vol30 = lr.rolling(30, min_periods=20).std()
    mkt = lr.where(mask).mean(1)
    beta60 = lr.rolling(60, min_periods=40).cov(mkt).div(mkt.rolling(60, min_periods=40).var(), axis=0)
    carry_vn = bucket_rank(carry_raw, vol30, mask)
    carry_bn = bucket_rank(carry_raw, beta60, mask)
    sigs = {"A": carry, "A_VN": carry_vn, "A_BN": carry_bn, "D": carry + illiq + taker, "D_VN": carry_vn + illiq + taker}
    assert np.allclose(sigs["D"].fillna(0).values, S.signal(p, mask).fillna(0).values)
    W = {k: bt.rank_long_short(s, mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"]) for k, s in sigs.items()}
    rows = []
    for win, (a0, b0) in WINDOWS.items():
        for k in range(7):
            a = pd.Timestamp(a0, tz="UTC") + pd.Timedelta(days=k)
            for v, w in W.items():
                ww = w[(w.index >= a) & (w.index <= b0)]
                r = bt.run(ww, fr.reindex(ww.index), p, bt.CostModel(), rebalance_every=P["rebalance_every"])
                y = r.net.iloc[:-1]
                eq = (1 + y).cumprod()
                rows.append({"window": win, "phase": k, "variant": v, "ann_net": y.mean() * 365,
                             "sharpe": y.mean() / y.std() * np.sqrt(365), "price": r.gross.iloc[:-1].mean() * 365,
                             "carry": r.funding.iloc[:-1].mean() * 365, "cost": r.cost.iloc[:-1].mean() * 365,
                             "mdd": float((eq / eq.cummax() - 1).min())})
    res = pd.DataFrame(rows)
    res.to_csv(ROOT / "docs/v2/reports/E43_neutral_carry_by_phase.csv", index=False)
    pd.set_option("display.width", 220)
    print(res.groupby(["window", "variant"])[["ann_net", "sharpe", "price", "carry", "cost", "mdd"]].mean().round(3).to_string())
    piv = res.pivot_table(index=["window", "phase"], columns="variant", values="ann_net")
    pr = res.pivot_table(index=["window", "phase"], columns="variant", values="price")
    for name, x, y in (("C1 A_VN vs A", "A_VN", "A"), ("C2 A_BN vs A", "A_BN", "A"), ("C3 D_VN vs D", "D_VN", "D")):
        ok = True
        for win in WINDOWS:
            d = piv.loc[win, x] - piv.loc[win, y]
            print(f"{name} {win}: delta {d.mean():+.4f}/yr, phases + {(d > 0).sum()}/7")
            ok &= bool(d.mean() > 0 and (d > 0).sum() >= 6)
        if name != "C3 D_VN vs D":
            ok &= bool(pr.loc["HOLDOUT_USED", x].mean() > pr.loc["HOLDOUT_USED", y].mean())
        print(f"{name}: {'BETTER' if ok else 'NOT BETTER'}")


if __name__ == "__main__":
    main()
