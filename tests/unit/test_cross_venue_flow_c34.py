import pandas as pd
import pytest

from scripts.evaluate_cross_venue_flow_c34 import (
    BAR_SECONDS, DECISION_SECONDS, HOLD_BARS, WARMUP, bootstrap, causal_features, collect, verify,
)


def flow(rows):
    return pd.DataFrame(rows, columns=["timestamp", "quote_volume", "taker_buy_quote_volume"]).set_index("timestamp")


def test_features_use_exact_completed_windows_and_prior_thresholds():
    decisions = WARMUP + 2
    timestamps = range(0, decisions * DECISION_SECONDS, BAR_SECONDS)
    spot = flow([(ts, 100.0, 60.0 if ts < (decisions - 2) * DECISION_SECONDS else 90.0) for ts in timestamps])
    futures = flow([(ts, 100.0, 40.0) for ts in timestamps])
    features = causal_features(spot, futures)
    final = features.iloc[-1]
    assert final.spot_score == pytest.approx(0.8)
    assert final.futures_score == pytest.approx(-0.2)
    assert final.spot_threshold == pytest.approx(0.2)
    assert final.divergence_threshold == pytest.approx(0.4)


def test_future_flow_mutation_does_not_change_prior_feature():
    timestamps = range(0, (WARMUP + 3) * DECISION_SECONDS, BAR_SECONDS)
    spot = flow([(ts, 100.0, 55.0) for ts in timestamps])
    futures = flow([(ts, 100.0, 45.0) for ts in timestamps])
    before = causal_features(spot, futures)
    target = int(before.index[-2])
    spot.loc[spot.index > target, "taker_buy_quote_volume"] = 99.0
    after = causal_features(spot, futures)
    pd.testing.assert_series_equal(before.loc[target], after.loc[target])


def test_collect_enters_at_decision_open_exits_96_bars_later_and_applies_funding():
    timestamp = 1_704_067_200
    features = pd.DataFrame([{
        "decision_timestamp": timestamp, "spot_score": 0.8, "futures_score": -0.2,
        "divergence": 1.0, "spot_threshold": 0.5, "divergence_threshold": 0.7,
    }]).set_index("decision_timestamp")
    price = pd.DataFrame({"timestamp": [timestamp + i * BAR_SECONDS for i in range(HOLD_BARS + 1)],
                          "open": [100.0] * HOLD_BARS + [110.0]}).set_index("timestamp")
    funding = pd.DataFrame({"timestamp": [timestamp, timestamp + 28_800], "funding_rate": [0.9, 0.001]})
    events, census = collect("BTCUSDT", features, price, funding, timestamp, timestamp + 1)
    assert census["signals"] == 1
    assert events[0]["entry_timestamp"] == timestamp
    assert events[0]["exit_timestamp"] == timestamp + HOLD_BARS * BAR_SECONDS
    assert events[0]["side"] == "LONG"
    assert events[0]["funding_return"] == pytest.approx(-0.001)
    assert events[0]["gross_return"] == pytest.approx(0.099)


def test_same_sign_flow_is_not_a_signal():
    timestamp = 1_704_067_200
    features = pd.DataFrame([{
        "decision_timestamp": timestamp, "spot_score": 0.8, "futures_score": 0.2,
        "divergence": 0.6, "spot_threshold": 0.5, "divergence_threshold": 0.5,
    }]).set_index("decision_timestamp")
    price = pd.DataFrame({"timestamp": [], "open": []}).set_index("timestamp")
    funding = pd.DataFrame({"timestamp": [], "funding_rate": []})
    events, census = collect("BTCUSDT", features, price, funding, timestamp, timestamp + 1)
    assert events == []
    assert census["opposition_rejected"] == 1


def test_equal_threshold_and_incomplete_path_fail_closed():
    timestamp = 1_704_067_200
    features = pd.DataFrame([{
        "decision_timestamp": timestamp, "spot_score": 0.8, "futures_score": -0.2,
        "divergence": 1.0, "spot_threshold": 0.8, "divergence_threshold": 0.7,
    }]).set_index("decision_timestamp")
    empty_price = pd.DataFrame({"timestamp": [], "open": []}).set_index("timestamp")
    funding = pd.DataFrame({"timestamp": [], "funding_rate": []})
    events, census = collect("BTCUSDT", features, empty_price, funding, timestamp, timestamp + 1)
    assert events == []
    assert census["spot_threshold_rejected"] == 1

    features.loc[timestamp, "spot_threshold"] = 0.
    events, census = collect("BTCUSDT", features, empty_price, funding, timestamp, timestamp + 1)
    assert events == []
    assert census["signals"] == 1
    assert census["missing_path"] == 1


def test_full_file_hash_mismatch_fails_before_parsing(tmp_path):
    path = tmp_path / "source.csv.gz"
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify(path, "0" * 64)


def test_bootstrap_clusters_same_utc_day(monkeypatch):
    events = [{"entry_timestamp": 0, "gross_return": 0.01},
              {"entry_timestamp": 900, "gross_return": 0.02},
              {"entry_timestamp": 86_400, "gross_return": -0.01}]
    result = bootstrap(events)
    assert len(result) == 2
    assert result[0] <= result[1]
