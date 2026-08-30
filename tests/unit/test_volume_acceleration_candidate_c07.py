import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_volume_acceleration_candidate_c07.py"
    spec = importlib.util.spec_from_file_location("edge_c07", path)
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded)
    return loaded


def panel(count=300):
    evaluator = module(); index = pd.Index([item * 900 for item in range(count)], name="timestamp")
    close = pd.DataFrame({symbol: 100 + np.arange(count) * (offset + 1) / 100
                          for offset, symbol in enumerate(evaluator.SYMBOLS)}, index=index)
    volume = pd.DataFrame(100.0, index=index, columns=evaluator.SYMBOLS)
    return close, close + 0.25, volume


def test_features_are_unchanged_before_future_mutation():
    evaluator = module(); close, _, volume = panel()
    baseline = evaluator.causal_features(close, volume)
    changed = close.copy(); changed.iloc[250, 1] *= 10
    mutated = evaluator.causal_features(changed, volume)
    for key in ("momentum", "acceleration", "btc_regime"):
        pd.testing.assert_frame_equal(baseline[key].iloc[:250] if key != "btc_regime" else baseline[key].iloc[:250].to_frame(),
                                      mutated[key].iloc[:250] if key != "btc_regime" else mutated[key].iloc[:250].to_frame())


def test_relative_volume_excludes_current_bar():
    evaluator = module(); close, _, volume = panel()
    baseline = evaluator.causal_features(close, volume)["relative_volume"]
    changed = volume.copy(); changed.iloc[150, 1] = 1000
    mutated = evaluator.causal_features(close, changed)["relative_volume"]
    assert mutated.iloc[150, 1] == pytest.approx(10.0)
    assert baseline.iloc[150, 2] == mutated.iloc[150, 2]


def triggered_panel():
    close, opened, volume = panel(400)
    close.iloc[192:, close.columns.get_loc("ETHUSDT")] *= 1.10
    volume.iloc[192, volume.columns.get_loc("ETHUSDT")] = 300
    return close, opened, volume


def test_trade_enters_next_open_and_exits_sixteen_bars_later():
    evaluator = module(); close, opened, volume = triggered_panel()
    trades, _ = evaluator.collect_trades(close, opened, volume)
    trade = trades[0]; position = close.index.get_loc(trade["decision_timestamp"])
    assert trade["entry_timestamp"] == close.index[position + 1]
    assert trade["exit_timestamp"] == close.index[position + 17]
    assert trade["entry_price"] == opened.iloc[position + 1][trade["symbol"]]


def test_position_state_prevents_duplicate_symbol_overlap():
    evaluator = module(); close, opened, volume = triggered_panel()
    volume.iloc[196, volume.columns.get_loc("ETHUSDT")] = 300
    trades, census = evaluator.collect_trades(close, opened, volume)
    eth = [trade for trade in trades if trade["symbol"] == "ETHUSDT"]
    assert all(right["entry_timestamp"] >= left["exit_timestamp"] for left, right in zip(eth, eth[1:]))
    assert census["duplicate_rejected"] >= 1


def test_cost_is_subtracted_from_gross_return():
    evaluator = module(); trades = [{"gross_return": 0.01}, {"gross_return": -0.01}]
    assert evaluator.metrics(trades, 0.003)["expectancy"] == pytest.approx(-0.003)
