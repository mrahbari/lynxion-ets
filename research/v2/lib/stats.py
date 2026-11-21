"""Performance statistics, Deflated Sharpe Ratio and the automatic trial registry."""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

REGISTRY = Path(__file__).resolve().parents[1] / "results" / "trials.jsonl"
ANN = 365.0
EULER = 0.5772156649


def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    if len(x) < 2 or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * math.sqrt(ANN))


def max_dd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def psr(x: pd.Series, sr0_ann: float = 0.0) -> float:
    """Probabilistic Sharpe Ratio (per-period SR, skew/kurtosis adjusted)."""
    x = x.dropna()
    n = len(x)
    if n < 30 or x.std() == 0:
        return float("nan")
    sr = x.mean() / x.std()
    sr0 = sr0_ann / math.sqrt(ANN)
    g3 = float(x.skew()); g4 = float(x.kurt()) + 3.0
    den = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr * sr))
    return float(norm.cdf((sr - sr0) * math.sqrt(n - 1) / den))


def expected_max_sr(n_trials: int, sr_var_ann: float) -> float:
    """Expected maximum annualised Sharpe among n independent null trials (Bailey & LdP)."""
    if n_trials <= 1:
        return 0.0
    s = math.sqrt(max(sr_var_ann, 1e-12))
    return s * ((1 - EULER) * norm.ppf(1 - 1 / n_trials) + EULER * norm.ppf(1 - 1 / (n_trials * math.e)))


def dsr(x: pd.Series, n_trials: int, sr_var_ann: float) -> float:
    return psr(x, expected_max_sr(n_trials, sr_var_ann))


def summary(net: pd.Series, gross: pd.Series | None = None, turnover: pd.Series | None = None) -> dict:
    net = net.dropna()
    yrs = {str(y): round(sharpe(g), 2) for y, g in net.groupby(net.index.year) if len(g) > 60}
    out = {
        "start": str(net.index.min().date()) if len(net) else None,
        "end": str(net.index.max().date()) if len(net) else None,
        "days": int(len(net)),
        "ann_ret": float(net.mean() * ANN),
        "ann_vol": float(net.std() * math.sqrt(ANN)),
        "sharpe": sharpe(net),
        "max_dd": max_dd(net),
        "psr0": psr(net),
        "sharpe_by_year": yrs,
        "pos_years": int(sum(v > 0 for v in yrs.values())),
        "n_years": len(yrs),
    }
    if gross is not None:
        out["sharpe_gross"] = sharpe(gross)
    if turnover is not None:
        out["avg_daily_turnover"] = float(turnover.mean())
    return out


def log_trial(family: str, name: str, params: dict, stats: dict, net: pd.Series) -> dict:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.time(), "family": family, "name": name, "params": params,
           "returns_sha": hashlib.sha256(np.nan_to_num(net.values).tobytes()).hexdigest()[:16], **stats}
    with open(REGISTRY, "a") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
    return rec


def registry() -> pd.DataFrame:
    if not REGISTRY.exists():
        return pd.DataFrame()
    return pd.read_json(REGISTRY, lines=True)


def deflate_all(net_by_name: dict[str, pd.Series], n_trials: int | None = None) -> pd.DataFrame:
    """DSR of each strategy given the total number of trials and the dispersion of their Sharpes."""
    srs = {k: sharpe(v) for k, v in net_by_name.items()}
    vals = np.array([v for v in srs.values() if np.isfinite(v)])
    n = n_trials or len(vals)
    var = float(np.var(vals, ddof=1)) if len(vals) > 1 else 1.0
    sr_star = expected_max_sr(n, var)
    rows = [{"name": k, "sharpe": srs[k], "sr_threshold": sr_star, "dsr": dsr(v, n, var)}
            for k, v in net_by_name.items()]
    return pd.DataFrame(rows).sort_values("dsr", ascending=False)
