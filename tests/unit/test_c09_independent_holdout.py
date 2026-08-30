import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_c09_independent_holdout.py"
    spec = importlib.util.spec_from_file_location("edge_c09", path)
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded


def panel(days=230):
    evaluator = module(); count = days * 96 + 100; index = pd.Index([item * 900 for item in range(count)], name="timestamp")
    close = pd.DataFrame({symbol: 100 + np.arange(count) * (offset + 1) / 10000
                          for offset, symbol in enumerate(evaluator.SYMBOLS)}, index=index)
    return close, close + 0.25


def test_future_mutation_cannot_change_earlier_features():
    evaluator = module(); close, _ = panel(); baseline = evaluator.causal_features(close)
    changed = close.copy(); changed.iloc[20000, 1] *= 10; mutated = evaluator.causal_features(changed)
    pd.testing.assert_frame_equal(baseline.iloc[:20000], mutated.iloc[:20000])


def test_current_spread_is_excluded_from_threshold():
    evaluator = module(); close, _ = panel(); position = 200 * 96
    baseline = evaluator.causal_features(close); changed = close.copy(); changed.iloc[position, 1] *= 10
    mutated = evaluator.causal_features(changed)
    assert baseline.iloc[position]["threshold"] == mutated.iloc[position]["threshold"]


def triggered_panel():
    close, opened = panel(); position = 200 * 96
    close.iloc[position, close.columns.get_loc("BTCUSDT")] *= 1.05
    close.iloc[position, close.columns.get_loc("ETHUSDT")] *= 1.25
    close.iloc[position, close.columns.get_loc("ADAUSDT")] *= 0.85
    return close, opened


def test_trade_is_long_only_next_open_with_24_hour_exit():
    evaluator = module(); close, opened = triggered_panel(); trades, _ = evaluator.collect_trades(close, opened)
    trade = trades[0]; position = close.index.get_loc(trade["decision_timestamp"])
    assert trade["entry_timestamp"] == close.index[position + 1]
    assert trade["exit_timestamp"] == close.index[position + 97]


def test_nonpositive_btc_regime_emits_no_trade():
    evaluator = module(); close, opened = triggered_panel(); position = 200 * 96
    close.iloc[position, close.columns.get_loc("BTCUSDT")] *= 0.5
    trades, _ = evaluator.collect_trades(close, opened)
    assert all(trade["decision_timestamp"] != close.index[position] for trade in trades)


def test_cost_is_applied():
    evaluator = module(); trades = [{"gross_return": 0.01}, {"gross_return": -0.01}]
    assert evaluator.metrics(trades, 0.003)["expectancy"] == pytest.approx(-0.003)
