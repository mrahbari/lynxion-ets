"""E14 — meta-labeling (Lopez de Prado, AFML ch. 3; Joubert 2022): the standard form of Fusion/Engine.

Question: can a secondary model that sees ALL watcher states at entry (what Fusion was designed to fuse) decide
which of the platform strategies' trades to take, well enough to turn them profitable?
Primary model = each strategy's own entry (direction + SL/TP, unchanged). Secondary model = P(trade wins | states).

Pre-registered before running (2026-11-23); nothing below is changed after seeing results.
  Trades: E9 trades (8 strategies, 10 perps, live-equivalent execution, net of fees, R units).
  Label: win = R > 0.
  Features (causal: from 1h bars CLOSED before the entry bar opens; same concept re-implementations as E12),
  all signed by trade side where direction matters:
    vol_ratio (std 6h / std 168h of 1h log returns), t1 * side, t4 * side (20-bar log-close t-stat, 1h and 4h),
    funding * side, r24 * side (symbol 24h return), btc_r24 * side (market pulse), sl_pct, hour-of-day (sin, cos),
    strategy one-hot.
  Models: (A) logistic regression (standardised, C = 1.0, inherently calibrated); (B) HistGradientBoosting
    (max_depth 3, 200 iterations, learning rate 0.05, min_samples_leaf 200) + isotonic calibration on the CV
    out-of-fold scores. No tuning beyond these fixed settings.
  DEV (2025-11-01..2026-06-30): purged 5-fold CV in time order; training trades whose [t_in, t_out] overlaps the
    test fold's span are dropped, plus a 24 h embargo after the fold. Out-of-fold probabilities give the DEV
    estimate. Threshold = keep the top q of trades by probability, q in {0.1, 0.2, 0.3, 0.5}; the q with the best
    DEV out-of-fold mean R is chosen (ties -> larger q). The threshold value is the DEV probability quantile.
  HOLDOUT (2026-07-01..10-31): model refit on all DEV, applied once to holdout with the DEV threshold.
  PASS (per model): DEV OOF filtered mean R >= +0.05 and PF >= 1.1; HOLDOUT filtered n >= 200, mean R > 0,
    PF >= 1.1, and lift (filtered - unfiltered holdout mean R) >= +0.05 R.
  Reported only (no pass/fail): OOF AUC, per-strategy holdout breakdown, bet sizing size = 2p - 1 (AFML 10.1,
    clipped at 0) mean R per unit risk.
  Decision: PASS -> refactor Fusion/Engine into this filter (same interfaces). FAIL -> keep interfaces, bypass.

Usage: python research/v2/experiments/e14_meta_labeling.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402
import e12_watcher_role_filters as e12  # noqa: E402

OUT = e9.OUT
DEV0, HOLD0, H = e12.DEV0, e12.HOLD0, e12.H
QS = (0.1, 0.2, 0.3, 0.5)
EMBARGO = 24 * H


def features(tr: pd.DataFrame) -> pd.DataFrame:
    out = []
    btc = e12.states("BTCUSDT")[["close_t", "r24"]].rename(columns={"r24": "btc_r24"})
    for sym, g in tr.groupby("symbol"):
        st = e12.states(sym)
        g = pd.merge_asof(g.sort_values("t_in"), st, left_on="t_in", right_on="close_t", direction="backward")
        g = pd.merge_asof(g.drop(columns="close_t"), btc, left_on="t_in", right_on="close_t", direction="backward")
        out.append(g)
    d = pd.concat(out).sort_values("t_in").reset_index(drop=True)
    s = np.where(d.side == "BUY", 1.0, -1.0)
    hr = (d.t_in // H) % 24
    X = pd.DataFrame({"vol_ratio": d.ratio, "t1": d.t1 * s, "t4": d.t4 * s, "funding": d.rate * s * 1e4,
                      "r24": d.r24 * s, "btc_r24": d.btc_r24 * s, "sl_pct": d.sl_pct,
                      "hsin": np.sin(2 * np.pi * hr / 24), "hcos": np.cos(2 * np.pi * hr / 24)})
    X = pd.concat([X, pd.get_dummies(d.strategy, prefix="s", dtype=float)], axis=1)
    keep = X.notna().all(axis=1)
    return d[keep].reset_index(drop=True), X[keep].reset_index(drop=True)


def models():
    return {"logit": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)),
            "gbm": lambda: HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.05,
                                                          min_samples_leaf=200, random_state=0)}


def purged_oof(make, X: pd.DataFrame, y: np.ndarray, d: pd.DataFrame, k: int = 5) -> np.ndarray:
    oof = np.full(len(y), np.nan)
    for idx in np.array_split(np.arange(len(y)), k):
        lo, hi = d.t_in.iloc[idx].min(), d.t_out.iloc[idx].max()
        train = ~((d.t_out >= lo) & (d.t_in <= hi + EMBARGO)).to_numpy()
        train[idx] = False
        m = make().fit(X[train], y[train])
        oof[idx] = m.predict_proba(X.iloc[idx])[:, 1]
    return oof


def stats(r: pd.Series) -> dict:
    w, lo = r[r > 0].sum(), -r[r < 0].sum()
    return {"n": int(len(r)), "mean_R": round(float(r.mean()), 3) if len(r) else np.nan,
            "PF": round(float(w / lo), 2) if lo else np.inf}


def main() -> None:
    tr = pd.read_csv(OUT / "E9_strategy_backtest_trades.csv")
    d, X = features(tr)
    y = (d.R > 0).astype(int).to_numpy()
    dev = (d.t_in >= DEV0) & (d.t_in < HOLD0)
    hold = d.t_in >= HOLD0
    dD, XD, yD = d[dev].reset_index(drop=True), X[dev].reset_index(drop=True), y[dev.to_numpy()]
    dH, XH = d[hold].reset_index(drop=True), X[hold].reset_index(drop=True)
    print(f"trades with features: DEV {len(dD)} (win {yD.mean():.3f}, mean R {dD.R.mean():.3f}) | "
          f"HOLDOUT {len(dH)} (mean R {dH.R.mean():.3f})")
    rows, per_strat = [], []
    for name, make in models().items():
        oof = purged_oof(make, XD, yD, dD)
        cal = None
        if name == "gbm":
            cal = IsotonicRegression(out_of_bounds="clip").fit(oof, yD)
            oof = cal.predict(oof)
        auc = roc_auc_score(yD, oof)
        grid = []
        for q in QS:
            thr = float(np.quantile(oof, 1 - q))
            grid.append((q, thr, stats(dD.R[oof >= thr])))
        best = max(grid, key=lambda g: (g[2]["mean_R"], g[0]))
        q, thr, sd = best
        m = make().fit(XD, yD)
        ph = m.predict_proba(XH)[:, 1]
        if cal is not None:
            ph = cal.predict(ph)
        sel = ph >= thr
        sh, base = stats(dH.R[sel]), stats(dH.R)
        lift = round(sh["mean_R"] - base["mean_R"], 3) if sh["n"] else np.nan
        size = np.clip(2 * ph - 1, 0, None)
        sized = float((size * dH.R).sum() / size.sum()) if size.sum() > 0 else np.nan
        dev_pass = bool(sd["mean_R"] >= 0.05 and sd["PF"] >= 1.1)
        hold_pass = bool(sh["n"] >= 200 and sh["mean_R"] > 0 and sh["PF"] >= 1.1 and lift >= 0.05)
        rows.append({"model": name, "dev_oof_auc": round(auc, 3), "q": q, "threshold": round(thr, 4),
                     **{f"dev_{k}": v for k, v in sd.items()},
                     "dev_grid": "; ".join(f"q{g[0]}: {g[2]['mean_R']}/{g[2]['PF']}" for g in grid),
                     "hold_auc": round(roc_auc_score((dH.R > 0).astype(int), ph), 3),
                     "hold_base_mean_R": base["mean_R"], **{f"hold_{k}": v for k, v in sh.items()},
                     "hold_lift_R": lift, "hold_sized_R_per_unit": round(sized, 3),
                     "dev_pass": dev_pass, "pass": dev_pass and hold_pass})
        for st, g in dH.assign(sel=sel).groupby("strategy"):
            per_strat.append({"model": name, "strategy": st, "base_n": len(g), "base_mean_R": round(g.R.mean(), 3),
                              **{f"sel_{k}": v for k, v in stats(g.R[g.sel]).items()}})
    r = pd.DataFrame(rows)
    p = pd.DataFrame(per_strat)
    r.to_csv(OUT / "E14_meta_labeling.csv", index=False)
    p.to_csv(OUT / "E14_meta_labeling_per_strategy.csv", index=False)
    pd.set_option("display.width", 250)
    print(r.T.to_string())
    print(p.to_string(index=False))


if __name__ == "__main__":
    main()
