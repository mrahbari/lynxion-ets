import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_oi_confirmed_impulse_c16.py"
    spec = importlib.util.spec_from_file_location("edge_c16", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def fixtures(decisions=220):
    evaluator = module()
    end = decisions * evaluator.DECISION_SECONDS + evaluator.EXIT_SECONDS
    timestamps = list(range(0, end + 1, 900))
    price = pd.DataFrame({"timestamp": timestamps, "open": [100 + t / 1e7 for t in timestamps],
                          "close": [100 + t / 1e7 for t in timestamps]}).set_index("timestamp")
    oi_times = list(range(300, end + 1, 300))
    oi = pd.Series([100 + t / 1e8 for t in oi_times], index=oi_times)
    funding = pd.Series([-0.001] * 1000, index=list(range(28800, 28800 * 1001, 28800)))
    return evaluator, price, oi, funding


def test_features_use_strictly_predecision_price_and_oi():
    evaluator, price, oi, _ = fixtures()
    features = evaluator.causal_features(price, oi)
    timestamp = int(features.index[10])
    baseline = features.loc[timestamp].copy()
    price.loc[timestamp, "close"] *= 10
    oi.loc[timestamp] = oi.iloc[-1] * 10
    changed = evaluator.causal_features(price, oi)
    pd.testing.assert_series_equal(baseline, changed.loc[timestamp])


def test_thresholds_exclude_current_observation():
    evaluator, price, oi, _ = fixtures()
    baseline = evaluator.causal_features(price, oi)
    timestamp = int(baseline.dropna().index[0])
    oi.loc[timestamp - evaluator.OI_LAG_SECONDS] *= 10
    changed = evaluator.causal_features(price, oi)
    assert baseline.loc[timestamp, "oi_threshold"] == changed.loc[timestamp, "oi_threshold"]


def test_entry_exit_and_long_funding_sign():
    evaluator, price, oi, funding = fixtures()
    features = evaluator.causal_features(price, oi)
    first = int(features.dropna().index[0])
    features.loc[first, ["price_return", "oi_return"]] = [0.1, 0.1]
    features.loc[first, ["price_threshold", "oi_threshold"]] = [0.01, 0.01]
    evaluator.causal_features = lambda *args: features
    trades, _ = evaluator.collect_trades("BTCUSDT", price, oi, funding)
    trade = trades[0]
    assert trade["entry_timestamp"] == trade["decision_timestamp"]
    assert trade["exit_timestamp"] - trade["entry_timestamp"] == evaluator.EXIT_SECONDS
    assert trade["funding_return"] > 0


def test_cost_is_applied_to_funding_inclusive_return():
    evaluator = module()
    assert evaluator.metrics([{"gross_return": 0.01}], 0.003)["expectancy"] == pytest.approx(0.007)
