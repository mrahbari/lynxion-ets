"""Multiple-testing controls (Phase-6 harness, Step 1).

Discovery tests many hypotheses, so false positives dominate. Benjamini-Hochberg
FDR control and a Deflated-Sharpe-style expected-max-under-null adjustment. These
gate promotion; default posture is REJECT.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

_EULER = 0.5772156649015329


def benjamini_hochberg(pvalues, alpha: float = 0.05):
    """BH FDR control. Returns (rejected_mask, adjusted_pvalues)."""
    p = np.asarray(pvalues, dtype=float)
    n = len(p)
    if n == 0:
        return np.array([], dtype=bool), np.array([])
    order = np.argsort(p)
    ranked = p[order]
    ranks = np.arange(1, n + 1)
    # adjusted p-values (monotone from the top)
    adj_sorted = np.minimum.accumulate((ranked * n / ranks)[::-1])[::-1]
    adj_sorted = np.clip(adj_sorted, 0, 1)
    adj = np.empty(n)
    adj[order] = adj_sorted
    passed = ranked <= alpha * ranks / n
    rejected = np.zeros(n, dtype=bool)
    if passed.any():
        kmax = np.max(np.where(passed)[0])
        sel = np.zeros(n, dtype=bool)
        sel[: kmax + 1] = True
        rejected[order] = sel
    return rejected, adj


def expected_max_sharpe(n_trials: int) -> float:
    """E[max] of n_trials independent N(0,1) Sharpe estimates (in std units).

    Bailey & López de Prado approximation. Used as the null benchmark a selected
    Sharpe must clear.
    """
    n = max(int(n_trials), 2)
    return ((1 - _EULER) * stats.norm.ppf(1 - 1.0 / n)
            + _EULER * stats.norm.ppf(1 - 1.0 / (n * np.e)))


def deflated_sharpe_ratio(
    sharpe: float, n_trials: int, n_obs: int, skew: float = 0.0, kurt: float = 3.0
) -> float:
    """Probability the true (annualised-unit-agnostic) Sharpe > 0 after accounting
    for selection across n_trials. `sharpe` is per-observation. Returns DSR in
    [0,1]; promote only when DSR is high (e.g. > 0.95)."""
    if n_obs < 3:
        return float("nan")
    sr0 = expected_max_sharpe(n_trials) / np.sqrt(n_obs)
    denom = np.sqrt(max(1e-12, 1 - skew * sharpe + (kurt - 1) / 4.0 * sharpe ** 2))
    z = (sharpe - sr0) * np.sqrt(n_obs - 1) / denom
    return float(stats.norm.cdf(z))
