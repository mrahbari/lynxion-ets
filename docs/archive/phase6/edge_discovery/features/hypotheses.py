"""Pre-registered Phase-6 signal hypotheses (Step 3, first batch).

Each hypothesis is a named, fixed-parameter signal builder. Parameters are chosen
by CONVENTION (round numbers) and FROZEN here — they are NOT tuned to the data
(tuning would be the data-snooping the protocol forbids). The registry size sets
the multiple-testing trial count.

A builder takes prices_by_symbol = {sym: OHLCV DataFrame} and returns
signal_by_symbol = {sym: signal Series} (signal[t] uses data <= t). Higher signal
value ⇒ predicted higher forward return (so reversal signals negate recent moves).
"""
from __future__ import annotations

import numpy as np

import feature_library as F


def _per_symbol(fn):
    """Wrap a single-symbol builder into the {sym: signal} interface."""
    def build(prices):
        return {s: fn(df) for s, df in prices.items()}
    return build


# ---- per-symbol hypotheses (fixed, conventional params) ----
def _reversal(k):
    return _per_symbol(lambda df: -F.past_return(df["close"], k))

def _momentum(k):
    return _per_symbol(lambda df: F.past_return(df["close"], k))

def _rsi_reversal(n):
    return _per_symbol(lambda df: -(F.rsi(df["close"], n) - 50.0))

def _range_revert(n):
    return _per_symbol(lambda df: -(F.range_position(df, n) - 0.5))

def _vol_scaled_reversal(k, vn):
    return _per_symbol(lambda df: -F.past_return(df["close"], k)
                       / F.realized_vol(df["close"], vn).replace(0, float("nan")))

def _volume_spike_reversal(n):
    def fn(df):
        import numpy as np
        return -np.sign(df["close"].pct_change()) * F.volume_zscore(df["volume"], n)
    return _per_symbol(fn)


# ---- cross-sectional hypotheses (relative-value, the blueprint's favoured class) ----
def _xs_reversal(k):
    def build(prices):
        rets = {s: F.past_return(df["close"], k) for s, df in prices.items()}
        return {s: -v for s, v in F.cross_sectional_demean(rets).items()}
    return build

def _xs_momentum(k):
    def build(prices):
        rets = {s: F.past_return(df["close"], k) for s, df in prices.items()}
        return F.cross_sectional_demean(rets)
    return build


# Pre-registered registry (name, hypothesis_class, builder). FROZEN.
REGISTRY = [
    ("reversal_5",            "statistical_reversion", _reversal(5)),
    ("reversal_20",           "statistical_reversion", _reversal(20)),
    ("momentum_20",           "momentum",              _momentum(20)),
    ("momentum_96",           "momentum",              _momentum(96)),
    ("rsi14_reversal",        "statistical_reversion", _rsi_reversal(14)),
    ("range48_revert",        "statistical_reversion", _range_revert(48)),
    ("vol_scaled_reversal_20", "statistical_reversion", _vol_scaled_reversal(20, 96)),
    ("volume_spike_reversal_48", "flow_proxy",         _volume_spike_reversal(48)),
    ("xs_reversal_20",        "cross_sectional",       _xs_reversal(20)),
    ("xs_momentum_96",        "cross_sectional",       _xs_momentum(96)),
]


# ---- Batch 2 (Step 4): pursue the batch-1 lead — short-horizon reversion was
# BH-significant cross-symbol but failed monotonicity, i.e. the edge lives at the
# EXTREMES. These emphasise the tails (zero in the middle), a new hypothesis FORM
# (not a param tweak). NOTE: batch-2 is IN-SAMPLE-MOTIVATED (derived from batch-1
# on the same data) → evidence is weaker; treated with cumulative multiple-testing
# correction and flagged as needing true out-of-sample confirmation.
def _extreme(series, center, thr):
    dev = series - center
    return -np.sign(dev) * (dev.abs() - thr).clip(lower=0)   # 0 in the middle band

def _rsi_extreme(n, thr):
    return _per_symbol(lambda df: _extreme(F.rsi(df["close"], n), 50.0, thr))

def _range_extreme(n, thr):
    return _per_symbol(lambda df: _extreme(F.range_position(df, n), 0.5, thr))


REGISTRY_BATCH2 = [
    ("rsi14_extreme_revert",   "statistical_reversion_extreme", _rsi_extreme(14, 20.0)),
    ("range48_extreme_revert", "statistical_reversion_extreme", _range_extreme(48, 0.30)),
    ("xs_reversal_5",          "cross_sectional",               _xs_reversal(5)),
]
