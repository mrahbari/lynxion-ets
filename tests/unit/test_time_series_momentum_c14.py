import importlib.util
from pathlib import Path

import pandas as pd


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_time_series_momentum_c14.py"
    spec = importlib.util.spec_from_file_location("edge_c14", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def bars(days=240):
    timestamps = [day * 86400 + bar * 900 for day in range(days) for bar in range(96)]
    prices = [100 + timestamp / 86400 for timestamp in timestamps]
    return pd.DataFrame({"timestamp": timestamps, "open": prices, "close": prices}).set_index("timestamp")


def test_daily_signal_uses_only_completed_day_and_180_prior_closes():
    evaluator = module()
    decisions = evaluator.monthly_decisions(bars())
    first = decisions.iloc[0]
    assert first["decision_timestamp"] % 86400 == 0
    assert first["momentum"] > 0


def test_entry_is_exact_first_open_after_decision_and_exit_is_28_days_later():
    evaluator = module()
    trades, _ = evaluator.collect_trades("BTCUSDT", bars())
    trade = trades[0]
    assert trade["entry_timestamp"] == trade["decision_timestamp"]
    assert trade["exit_timestamp"] - trade["entry_timestamp"] == 28 * 86400


def test_future_mutation_does_not_change_prior_signal():
    evaluator = module()
    original = bars()
    baseline = evaluator.monthly_decisions(original)
    cutoff = int(baseline.iloc[0]["decision_timestamp"])
    changed = original.copy()
    changed.loc[changed.index >= cutoff, "close"] *= 10
    revised = evaluator.monthly_decisions(changed)
    assert baseline.iloc[0]["momentum"] == revised.iloc[0]["momentum"]


def test_cost_is_subtracted_once_per_round_trip():
    evaluator = module()
    assert evaluator.metrics([{"gross_return": 0.01}], 0.003)["expectancy"] == 0.007
