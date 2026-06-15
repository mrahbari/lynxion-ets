"""Predictive-power metrics (Phase-6 harness, Step 1).

Information Coefficient with Newey-West (HAC) significance, decile-spread
analysis, event-study CAR, and rolling-IC stability. Signal-quality only — no
SL/TP, sizing, cost, or trading simulation anywhere in this module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def _align(a: pd.Series, b: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    df = pd.concat([a.rename("a"), b.rename("b")], axis=1).replace(
        [np.inf, -np.inf], np.nan).dropna()
    return df["a"].to_numpy(float), df["b"].to_numpy(float)


def _newey_west_lrv(g: np.ndarray, lag: int) -> float:
    """Newey-West long-run variance of the mean of g_t (Bartlett kernel)."""
    g = g - g.mean()
    n = len(g)
    if n < 2:
        return float("nan")
    lrv = float(g @ g) / n  # gamma_0
    for l in range(1, min(lag, n - 1) + 1):
        w = 1.0 - l / (lag + 1.0)
        cov = float(g[l:] @ g[:-l]) / n
        lrv += 2.0 * w * cov
    return max(lrv, 1e-12)


def information_coefficient(
    signal: pd.Series, label: pd.Series, horizon: int = 1, hac_lag: int | None = None
) -> dict:
    """Spearman IC with a HAC (Newey-West) t-stat that accounts for the serial
    correlation induced by overlapping forward windows.

    IC == mean(z_s * z_y) where z are standardised ranks (== Spearman). The HAC
    long-run variance of that product series gives a t-stat robust to overlap;
    lag defaults to the horizon (overlap length).
    """
    s, y = _align(signal, label)
    n = len(s)
    base = {"ic": np.nan, "t_stat": np.nan, "p_value": np.nan, "n": n,
            "hac_lag": None, "se": np.nan}
    if n < 10 or np.std(s) == 0 or np.std(y) == 0:
        return base
    rs = stats.rankdata(s)
    ry = stats.rankdata(y)
    zs = (rs - rs.mean()) / rs.std()
    zy = (ry - ry.mean()) / ry.std()
    g = zs * zy
    ic = float(g.mean())  # Spearman correlation
    lag = hac_lag if hac_lag is not None else max(1, int(horizon))
    lrv = _newey_west_lrv(g, lag)
    se = float(np.sqrt(lrv / n))
    t = ic / se if se > 0 else np.nan
    p = float(2 * stats.norm.sf(abs(t))) if np.isfinite(t) else np.nan
    return {"ic": ic, "t_stat": float(t), "p_value": p, "n": n,
            "hac_lag": lag, "se": se}


def decile_analysis(signal: pd.Series, label: pd.Series, n_bins: int = 10) -> dict:
    """Bucket by signal quantile; measure monotonicity and top-minus-bottom spread."""
    s, y = _align(signal, label)
    base = {"bin_means": [], "spread": np.nan, "monotonicity": np.nan,
            "spread_t": np.nan, "spread_p": np.nan, "n_bins": n_bins}
    if len(s) < n_bins * 3:
        return base
    # rank-then-qcut avoids duplicate-edge errors when signal has ties
    ranks = pd.Series(s).rank(method="first")
    bins = pd.qcut(ranks, n_bins, labels=False).to_numpy()
    means = np.array([y[bins == b].mean() for b in range(n_bins)])
    mono, _ = stats.spearmanr(np.arange(n_bins), means)
    top, bot = y[bins == n_bins - 1], y[bins == 0]
    t, p = stats.ttest_ind(top, bot, equal_var=False)
    return {"bin_means": means.tolist(), "spread": float(means[-1] - means[0]),
            "monotonicity": float(mono), "spread_t": float(t),
            "spread_p": float(p), "n_bins": n_bins}


def event_study(event_flags: pd.Series, label: pd.Series) -> dict:
    """CAR of forward return on event bars vs non-event baseline (Welch t-test)."""
    s, y = _align(event_flags.astype(float), label)
    ev, base_ret = y[s > 0], y[s <= 0]
    base = {"n_events": int((s > 0).sum()), "mean_fwd_ret": np.nan,
            "baseline": np.nan, "abnormal": np.nan, "t_stat": np.nan, "p_value": np.nan}
    if len(ev) < 5 or len(base_ret) < 5:
        return base
    t, p = stats.ttest_ind(ev, base_ret, equal_var=False)
    return {"n_events": int(len(ev)), "mean_fwd_ret": float(ev.mean()),
            "baseline": float(base_ret.mean()),
            "abnormal": float(ev.mean() - base_ret.mean()),
            "t_stat": float(t), "p_value": float(p)}


def block_ic(signal: pd.Series, label: pd.Series, n_blocks: int = 6) -> dict:
    """Per-block (non-overlapping, time-ordered) Spearman IC for stability.

    Returns each block's IC and the fraction sharing the full-sample IC sign —
    a non-stationary edge (low sign-consistency) is a reject signal.
    """
    s, y = _align(signal, label)
    base = {"block_ics": [], "sign_consistency": np.nan, "n_blocks": 0}
    if len(s) < n_blocks * 10:
        n_blocks = max(2, len(s) // 10)
    if len(s) < 20:
        return base
    full = stats.spearmanr(s, y).statistic
    ics = []
    for idx in np.array_split(np.arange(len(s)), n_blocks):
        if len(idx) < 5 or np.std(s[idx]) == 0 or np.std(y[idx]) == 0:
            continue
        ics.append(float(stats.spearmanr(s[idx], y[idx]).statistic))
    if not ics:
        return base
    sign = np.sign(full) if full != 0 else 1.0
    consistency = float(np.mean([np.sign(v) == sign for v in ics]))
    return {"block_ics": ics, "sign_consistency": consistency, "n_blocks": len(ics)}
