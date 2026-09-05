from types import SimpleNamespace

import hashlib

import pandas as pd

from scripts import evaluate_volatility_sweep_c28 as candidate


def row(**overrides):
    values = dict(prior_high=100, prior_low=90, range_threshold=5, true_range=10,
                  open=99, high=105, low=98, close=99, upper_wick_share=6 / 7,
                  lower_wick_share=0)
    values.update(overrides)
    return SimpleNamespace(**values)


def test_signal_side_follows_frozen_rejection_direction():
    assert candidate.signal_side(row()) == "SHORT"
    assert candidate.signal_side(row(open=91, high=92, low=85, close=91,
                                     upper_wick_share=0, lower_wick_share=6 / 7)) == "LONG"
    assert candidate.signal_side(row(true_range=5)) is None


def test_causal_features_exclude_current_extreme_and_range(monkeypatch):
    monkeypatch.setattr(candidate, "EXTREME_LOOKBACK", 2)
    monkeypatch.setattr(candidate, "RANGE_LOOKBACK", 2)
    frame = pd.DataFrame({
        "timestamp": [0, 900, 1800, 2700], "open": [9, 10, 10, 10],
        "high": [10, 11, 12, 100], "low": [8, 9, 9, 0], "close": [9, 10, 11, 50],
    })
    result = candidate.causal_features(frame)
    assert result.loc[3, "prior_high"] == 12
    assert result.loc[3, "prior_low"] == 9
    assert result.loc[3, "range_threshold"] < result.loc[3, "true_range"]


def test_funding_boundaries_are_strict_after_entry_and_inclusive_at_exit(monkeypatch):
    monkeypatch.setattr(candidate, "HOLD_BARS", 1)
    features = pd.DataFrame([
        dict(timestamp=0, open=99, high=105, low=98, close=99, true_range=10,
             prior_high=100, prior_low=90, range_threshold=5,
             upper_wick_share=6 / 7, lower_wick_share=0),
        dict(timestamp=900, open=100, high=101, low=99, close=100, true_range=2,
             prior_high=105, prior_low=90, range_threshold=5,
             upper_wick_share=.5, lower_wick_share=.5),
        dict(timestamp=1800, open=90, high=91, low=89, close=90, true_range=2,
             prior_high=105, prior_low=90, range_threshold=5,
             upper_wick_share=.5, lower_wick_share=.5),
    ])
    funding = pd.DataFrame({"timestamp": [900, 1800, 2700],
                            "funding_rate": [.01, .02, .04]})
    events, _ = candidate.collect_events("BTCUSDT", features, funding, 0, 3600)
    assert len(events) == 1
    assert events[0]["side"] == "SHORT"
    assert events[0]["funding_return"] == .02


def test_empty_metrics_and_report_gate_are_fail_closed():
    assert candidate.metrics([])["expectancy"] is None
    assert candidate.bootstrap([]) == [None, None]


def test_frozen_source_hash_fails_closed(tmp_path):
    source = tmp_path / "source.csv"
    source.write_bytes(b"frozen")
    expected = hashlib.sha256(b"frozen").hexdigest()
    candidate.verify_source(source, expected)
    source.write_bytes(b"changed")
    try:
        candidate.verify_source(source, expected)
    except ValueError as error:
        assert "frozen source hash mismatch" in str(error)
    else:
        raise AssertionError("changed source must fail closed")
