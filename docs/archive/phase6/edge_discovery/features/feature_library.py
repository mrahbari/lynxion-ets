"""Lookahead-safe feature primitives for Phase-6 signal hypotheses (Step 3).

Every feature value at bar t uses ONLY data with index <= t (rolling/shift over
past bars, or the current close which is known at t's close). The harness aligns
signal[t] with a forward label starting strictly after t, so using close[t] is
correct (decision taken at the close of t). NO future bars are read anywhere.

No SL/TP, no trading logic — feature math only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def past_return(close: pd.Series, k: int) -> pd.Series:
    """Return over the past k bars ending at t (uses close[t-k..t])."""
    return close.pct_change(k)


def realized_vol(close: pd.Series, n: int) -> pd.Series:
    return close.pct_change().rolling(n).std()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder RSI using only past bars."""
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    roll_up = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    roll_dn = dn.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = roll_up / roll_dn.replace(0.0, np.nan)
    return 100 - 100 / (1 + rs)


def range_position(df: pd.DataFrame, n: int) -> pd.Series:
    """Where close sits in the past-n high/low range, in [0,1] (uses <= t)."""
    lo = df["low"].rolling(n).min()
    hi = df["high"].rolling(n).max()
    return (df["close"] - lo) / (hi - lo).replace(0.0, np.nan)


def volume_zscore(volume: pd.Series, n: int) -> pd.Series:
    m = volume.rolling(n).mean()
    s = volume.rolling(n).std()
    return (volume - m) / s.replace(0.0, np.nan)


def cross_sectional_demean(series_by_symbol: dict[str, pd.Series]) -> dict[str, pd.Series]:
    """For each timestamp, subtract the cross-sectional mean across symbols.
    Uses only contemporaneous (<= t) values, aligned on the common index."""
    mat = pd.DataFrame(series_by_symbol)
    demeaned = mat.sub(mat.mean(axis=1), axis=0)
    return {c: demeaned[c] for c in demeaned.columns}
