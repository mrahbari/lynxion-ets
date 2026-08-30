import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_cross_sectional_candidate_c05.py"
    spec = importlib.util.spec_from_file_location("edge_c05", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def symbol_csv(path, closes):
    frame = pd.DataFrame({
        "timestamp": [index * 900 for index in range(len(closes))],
        "open": [value + 0.25 for value in closes],
        "close": closes,
        "volume": [1000] * len(closes),
    })
    frame.to_csv(path, index=False)


def test_features_use_only_closed_and_prior_bars(tmp_path):
    evaluator = module()
    path = tmp_path / "AAA-USDT.csv"
    closes = [100 + index for index in range(140)]
    symbol_csv(path, closes)
    baseline = evaluator.prepare_symbol(path)
    closes[120] *= 10
    symbol_csv(path, closes)
    changed = evaluator.prepare_symbol(path)

    cutoff = 120 * 900
    pd.testing.assert_frame_equal(
        baseline.loc[baseline.timestamp < cutoff, ["timestamp", "momentum", "liquidity"]].reset_index(drop=True),
        changed.loc[changed.timestamp < cutoff, ["timestamp", "momentum", "liquidity"]].reset_index(drop=True),
    )


def test_entry_and_exit_are_next_open_and_sixteen_bars_apart(tmp_path):
    evaluator = module()
    path = tmp_path / "AAA-USDT.csv"
    closes = [100 + index for index in range(140)]
    symbol_csv(path, closes)
    row = evaluator.prepare_symbol(path).iloc[0]
    raw = pd.read_csv(path)
    decision_index = int(row.timestamp // 900)

    assert row.entry_open == raw.iloc[decision_index + 1].open
    assert row.exit_open == raw.iloc[decision_index + 17].open
    assert row.exit_timestamp - row.entry_timestamp == 16 * 900


def test_cross_section_selects_three_in_market_direction():
    evaluator = module()
    timestamp = 16 * 900
    rows = []
    for index in range(35):
        rows.append({
            "timestamp": timestamp, "symbol": f"S{index}", "momentum": (index - 10) / 100,
            "liquidity": 1000 - index, "entry_open": 100, "exit_open": 101,
            "entry_timestamp": timestamp + 900, "exit_timestamp": timestamp + 17 * 900,
        })
    selections, census = evaluator.select_batches(pd.DataFrame(rows))

    assert census["decision_timestamps"] == 1
    assert len(selections) == 3
    assert {item["side"] for item in selections} == {"LONG"}
    assert {item["symbol"] for item in selections} == {"S32", "S33", "S34"}


def test_fold_boundary_excludes_crossing_positions():
    evaluator = module()
    selections = []
    for index in range(8):
        selections.append({
            "decision_timestamp": index * 100, "exit_timestamp": index * 100 + 150,
            "gross_return": 0.01, "symbol": "AAA", "side": "LONG",
        })
    accepted, unresolved = evaluator.split_folds(selections)

    assert unresolved > 0
    assert all(item["exit_timestamp"] < ([200, 400, 600, 851][item["fold"] - 1]) for item in accepted)


def test_cost_is_deducted_from_directional_gross_return():
    evaluator = module()
    items = [{"gross_return": 0.01}, {"gross_return": -0.01}]
    result = evaluator.metrics(items, 0.003)

    assert result["expectancy"] == pytest.approx(-0.003)
