"""Validation for the Phase-6 predictive-power harness (research/edge_discovery/measurement/).

Run locally (tests/ is gitignored):
    .venv/bin/python3 -m pytest tests/unit/test_edge_discovery_measurement.py -q
"""
import os
import sys

import numpy as np
import pandas as pd

HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "research", "edge_discovery", "measurement")
sys.path.insert(0, HARNESS)

import forward_labels as fl          # noqa: E402
import predictive_power as pp        # noqa: E402
import cv                            # noqa: E402
import multiple_testing as mt        # noqa: E402
import harness as H                  # noqa: E402


# ---------- forward labels: no lookahead ----------
def test_forward_labels_no_lookahead():
    close = pd.Series(np.exp(np.cumsum(np.full(50, 0.01))))
    f = fl.forward_log_returns(close, [3])
    assert f["fwd_3"].iloc[-3:].isna().all()          # last h are NaN (no future)
    assert np.isclose(f["fwd_3"].iloc[0], np.log(close.iloc[3] / close.iloc[0]))


def test_vol_normalized_uses_backward_vol():
    close = pd.Series(np.exp(np.cumsum(np.random.RandomState(0).normal(0, 0.01, 300))))
    v = fl.vol_normalized_forward_returns(close, [1, 5])
    assert v["fwd_5"].iloc[-5:].isna().all()


# ---------- IC + HAC ----------
def test_ic_perfect_and_random():
    rng = np.random.RandomState(1)
    y = pd.Series(rng.normal(size=2000))
    assert pp.information_coefficient(y, y, 1)["ic"] > 0.99            # perfect
    noise = pd.Series(rng.normal(size=2000))
    r = pp.information_coefficient(noise, y, 1)
    assert abs(r["ic"]) < 0.1 and r["p_value"] > 0.05                  # no edge


def test_hac_lag_tracks_horizon():
    rng = np.random.RandomState(2)
    s = pd.Series(rng.normal(size=1000)); y = pd.Series(rng.normal(size=1000))
    assert pp.information_coefficient(s, y, horizon=10)["hac_lag"] == 10


# ---------- decile ----------
def test_decile_monotonic_for_linear_signal():
    rng = np.random.RandomState(3)
    s = pd.Series(rng.normal(size=3000))
    y = s + pd.Series(rng.normal(0, 0.5, 3000))      # y increases with s
    d = pp.decile_analysis(s, y)
    assert d["monotonicity"] > 0.9 and d["spread"] > 0


# ---------- multiple testing ----------
def test_benjamini_hochberg_basic():
    rej, adj = mt.benjamini_hochberg([0.001, 0.2, 0.04, 0.8], alpha=0.05)
    assert rej[0] and not rej[3]
    assert (adj >= np.array([0.001, 0.2, 0.04, 0.8]) - 1e-9).all()
    assert mt.benjamini_hochberg([0.9, 0.8, 0.95], 0.05)[0].sum() == 0


def test_expected_max_sharpe_increases_with_trials():
    assert mt.expected_max_sharpe(100) > mt.expected_max_sharpe(5) > 0


# ---------- purged/embargoed CV: leakage-proof ----------
def test_walk_forward_no_leakage():
    splits = cv.purged_walk_forward(1000, n_splits=5, embargo=15)
    assert len(splits) >= 4
    cv.assert_no_leakage(splits, embargo=15, walk_forward=True)
    for tr, te in splits:
        assert tr.max() < te.min()                    # train strictly in the past
        assert te.min() - tr.max() - 1 >= 15          # embargo respected


def test_kfold_embargo_band():
    splits = cv.purged_kfold(500, k=5, embargo=10)
    cv.assert_no_leakage(splits, embargo=10, walk_forward=False)


# ---------- end-to-end: detect real edge, reject noise ----------
def _make_market(n, beta, seed):
    """close where next-bar return depends on signal s[t] (real edge when beta>0)."""
    rng = np.random.RandomState(seed)
    s = rng.normal(size=n)
    fwd_ret = beta * s + rng.normal(0, 1.0, n)        # r[t -> t+1] driven by s[t]
    close = pd.Series(100 * np.exp(np.cumsum(np.r_[0.0, fwd_ret[:-1]])))
    return pd.Series(s), close


def test_end_to_end_promotes_real_edge():
    sigs, closes = {}, {}
    for i, sym in enumerate(["BTC", "ETH", "SOL"]):
        s, c = _make_market(3000, beta=0.30, seed=10 + i)
        sigs[sym], closes[sym] = s, c
    res = H.evaluate_across_symbols(sigs, closes, horizons=[1, 5], n_trials=6)
    assert res["overall_verdict"] == "PROMOTE", res["symbol_verdicts"]
    assert res["cross_symbol_sign_agreement"] is True


def test_end_to_end_rejects_noise():
    sigs, closes = {}, {}
    for i, sym in enumerate(["BTC", "ETH", "SOL"]):
        s, c = _make_market(3000, beta=0.0, seed=100 + i)   # no edge
        sigs[sym], closes[sym] = s, c
    res = H.evaluate_across_symbols(sigs, closes, horizons=[1, 5], n_trials=6)
    assert res["overall_verdict"] == "ARCHIVE", res["symbol_verdicts"]


def test_regime_conditional_ic_present():
    s, c = _make_market(2000, beta=0.25, seed=7)
    regime = pd.Series(np.where(np.arange(2000) % 2 == 0, "lo", "hi"))
    out = H.evaluate_signal(s, c, horizons=[1], regime=regime)
    assert set(out["regime_ic"].keys()) == {"lo", "hi"}


def test_edge_ledger_roundtrip(tmp_path):
    s, c = _make_market(1500, beta=0.3, seed=5)
    res = H.evaluate_across_symbols({"BTC": s}, {"BTC": c}, horizons=[1], n_trials=2)
    led = H.EdgeLedger(); led.record("demo_signal", "test_class", res)
    p = led.save(str(tmp_path / "edge_ledger.json"))
    assert os.path.exists(p)
