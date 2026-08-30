import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_market_neutral_candidate_c06.py"
    spec = importlib.util.spec_from_file_location("edge_c06", path)
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded)
    return loaded


def panel(count=3000):
    index = pd.Index([item * 900 for item in range(count)], name="timestamp")
    return pd.DataFrame({symbol: 100 + np.arange(count) * (offset + 1) / 1000
                         for offset, symbol in enumerate(module().SYMBOLS)}, index=index)


def triggered_panel():
    close = panel(3005)
    close.iloc[2900, :3] *= 1.10
    close.iloc[2900, 3:] *= 0.90
    return close


def test_future_close_mutation_cannot_change_earlier_features():
    evaluator = module(); close = panel()
    baseline = evaluator.causal_features(close)
    changed = close.copy(); changed.iloc[2950, 0] *= 10
    mutated = evaluator.causal_features(changed)
    pd.testing.assert_frame_equal(baseline.iloc[:2950], mutated.iloc[:2950])


def test_threshold_excludes_current_dispersion():
    evaluator = module(); close = panel()
    baseline = evaluator.causal_features(close)
    changed = close.copy(); changed.iloc[2900, 0] *= 10
    mutated = evaluator.causal_features(changed)
    assert baseline.iloc[2900]["threshold"] == mutated.iloc[2900]["threshold"]


def test_pair_uses_next_open_and_exits_four_bars_after_entry():
    evaluator = module(); close = triggered_panel(); opened = close + 0.5
    pairs, _ = evaluator.collect_pairs(close, opened)
    pair = pairs[0]
    decision_position = close.index.get_loc(pair["decision_timestamp"])
    assert pair["entry_timestamp"] == close.index[decision_position + 1]
    assert pair["exit_timestamp"] == close.index[decision_position + 5]
    for leg in pair["legs"]:
        assert leg["entry_price"] == opened.iloc[decision_position + 1][leg["symbol"]]


def test_pair_contains_opposite_extreme_legs():
    evaluator = module(); close = triggered_panel(); opened = close + 0.5
    pairs, _ = evaluator.collect_pairs(close, opened)
    assert {leg["side"] for leg in pairs[0]["legs"]} == {"LONG", "SHORT"}
    assert len({leg["symbol"] for leg in pairs[0]["legs"]}) == 2


def test_pair_cost_is_applied_per_leg_equivalently():
    evaluator = module()
    pairs = [{"pair_gross_return": 0.01}, {"pair_gross_return": -0.01}]
    assert evaluator.pair_metrics(pairs, 0.003)["expectancy"] == pytest.approx(-0.003)
