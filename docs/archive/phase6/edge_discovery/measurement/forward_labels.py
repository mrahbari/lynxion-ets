"""Forward-return labelling engine (Phase-6 harness, Step 1).

Produces forward-looking return LABELS for measuring signal predictive power.
The label is intentionally future-looking (that is what a signal must predict);
the NO-LOOKAHEAD obligation is on the *signal* (features <= t), which the harness
enforces by aligning signal[t] with a label that starts strictly after t.

No SL/TP, no trading simulation — pure price-path labels.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def forward_log_returns(close: pd.Series, horizons: list[int]) -> pd.DataFrame:
    """Forward log return over each horizon h: r_h[t] = log(close[t+h]/close[t]).

    The last h rows of column h are NaN (no future data) — this is the structural
    guarantee against using a label that does not exist yet.
    """
    close = close.astype(float)
    logc = np.log(close)
    out = {h: logc.shift(-h) - logc for h in horizons}
    df = pd.DataFrame(out, index=close.index)
    df.columns = [f"fwd_{h}" for h in horizons]
    return df


def realized_vol(close: pd.Series, window: int) -> pd.Series:
    """Backward-looking realised vol of 1-bar log returns (uses data <= t only)."""
    r = np.log(close.astype(float)).diff()
    return r.rolling(window).std()


def vol_normalized_forward_returns(
    close: pd.Series, horizons: list[int], vol_window: int | None = None
) -> pd.DataFrame:
    """Forward returns divided by a BACKWARD-looking vol estimate scaled to horizon.

    Vol uses only data up to t (no leakage); the forward return uses future. The
    ratio makes IC comparable across symbols/regimes with different volatility.
    """
    fwd = forward_log_returns(close, horizons)
    out = {}
    for h in horizons:
        w = vol_window or max(5 * h, 20)
        vol_h = realized_vol(close, w) * np.sqrt(h)
        out[f"fwd_{h}"] = fwd[f"fwd_{h}"] / vol_h.replace(0.0, np.nan)
    return pd.DataFrame(out, index=close.index)
