import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_daily_relative_strength_c08.py"
    spec = importlib.util.spec_from_file_location("edge_c08", path)
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded


def panel(days=220):
    evaluator = module(); count = days * 96 + 100
    index = pd.Index([item * 900 for item in range(count)], name="timestamp")
    close = pd.DataFrame({symbol: 100 + np.arange(count) * (offset + 1) / 10000
                          for offset, symbol in enumerate(evaluator.SYMBOLS)}, index=index)
    return close, close + 0.25


def test_future_mutation_does_not_change_earlier_relative_features():
    evaluator = module(); close, _ = panel(); baseline = evaluator.causal_features(close)
    changed = close.copy(); changed.iloc[20000, 1] *= 10; mutated = evaluator.causal_features(changed)
    pd.testing.assert_frame_equal(baseline.iloc[:20000], mutated.iloc[:20000])


def test_current_spread_is_excluded_from_daily_threshold():
    evaluator = module(); close, _ = panel(); baseline = evaluator.causal_features(close)
    position = 200 * 96; changed = close.copy(); changed.iloc[position, 1] *= 10
    mutated = evaluator.causal_features(changed)
    assert baseline.iloc[position]["threshold"] == mutated.iloc[position]["threshold"]


def triggered_panel():
    close, opened = panel(230); position = 200 * 96
    close.iloc[position, close.columns.get_loc("ETHUSDT")] *= 1.2
    close.iloc[position, close.columns.get_loc("ADAUSDT")] *= 0.8
    return close, opened


def test_pair_uses_next_open_and_24_hour_horizon():
    evaluator = module(); close, opened = triggered_panel(); pairs, _ = evaluator.collect_pairs(close, opened)
    pair = pairs[0]; position = close.index.get_loc(pair["decision_timestamp"])
    assert pair["entry_timestamp"] == close.index[position + 1]
    assert pair["exit_timestamp"] == close.index[position + 97]


def test_pair_selects_distinct_long_and_short_extremes():
    evaluator = module(); close, opened = triggered_panel(); pairs, _ = evaluator.collect_pairs(close, opened)
    assert {leg["side"] for leg in pairs[0]["legs"]} == {"LONG", "SHORT"}
    assert len({leg["symbol"] for leg in pairs[0]["legs"]}) == 2


def test_pair_cost_is_applied_per_leg():
    evaluator = module(); pairs = [{"pair_gross_return": 0.01}, {"pair_gross_return": -0.01}]
    assert evaluator.pair_metrics(pairs, 0.003)["expectancy"] == pytest.approx(-0.003)
