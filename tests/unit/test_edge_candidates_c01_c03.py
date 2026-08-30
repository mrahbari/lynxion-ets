import importlib.util
from pathlib import Path

import pandas as pd


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_edge_candidates_c01_c03.py"
    spec = importlib.util.spec_from_file_location("edge_c01_c03", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def candles(count=240, frequency=900):
    close = [100 + index * 0.1 for index in range(count)]
    return pd.DataFrame({
        "timestamp": [index * frequency for index in range(count)],
        "open": close, "high": [value + 1 for value in close],
        "low": [value - 1 for value in close], "close": close, "volume": [10] * count,
    })


def test_shifted_hourly_features_do_not_change_when_current_hour_close_changes():
    evaluator = module()
    frame15 = candles(240, 900)
    frame1h = candles(60, 3600)
    baseline = evaluator.causal_features(frame15, frame1h)
    mutated = frame1h.copy()
    mutated.loc[30, "close"] *= 10
    changed = evaluator.causal_features(frame15, mutated)

    decision_time = int(frame1h.loc[30, "timestamp"])
    before_next_hour = baseline["timestamp"] < decision_time + 3600
    pd.testing.assert_series_equal(
        baseline.loc[before_next_hour, "ema20_1h"].reset_index(drop=True),
        changed.loc[before_next_hour, "ema20_1h"].reset_index(drop=True),
    )


def test_path_simulator_uses_next_open_and_sl_priority_on_dual_touch():
    evaluator = module()
    frame = pd.DataFrame([
        {"open": 100, "high": 101, "low": 99, "close": 100},
        {"open": 101, "high": 106, "low": 94, "close": 102},
    ])
    signals = [{"signal_index": 0, "entry_index": 1, "side": "BUY", "stop": 95, "take_profit": 105}]

    trades, unresolved = evaluator.simulate_fold(frame, signals, 0, 2)

    assert unresolved == 0
    assert trades[0]["entry_price"] == 101
    assert trades[0]["exit_reason"] == "SL"
    assert trades[0]["exit_price"] == 95


def test_position_state_ignores_overlapping_signals_until_first_exit():
    evaluator = module()
    frame = pd.DataFrame([
        {"open": 100, "high": 101, "low": 99, "close": 100},
        {"open": 100, "high": 102, "low": 99, "close": 101},
        {"open": 101, "high": 102, "low": 100, "close": 101},
        {"open": 101, "high": 106, "low": 100, "close": 105},
    ])
    signals = [
        {"signal_index": 0, "entry_index": 1, "side": "BUY", "stop": 95, "take_profit": 105},
        {"signal_index": 1, "entry_index": 2, "side": "BUY", "stop": 95, "take_profit": 105},
    ]

    trades, _ = evaluator.simulate_fold(frame, signals, 0, 4)

    assert len(trades) == 1


def test_unresolved_position_blocks_all_later_signals_in_fold():
    evaluator = module()
    frame = pd.DataFrame([
        {"open": 100, "high": 101, "low": 99, "close": 100},
        {"open": 100, "high": 101, "low": 99, "close": 100},
        {"open": 100, "high": 106, "low": 99, "close": 105},
    ])
    signals = [
        {"signal_index": 0, "entry_index": 1, "side": "BUY", "stop": 90, "take_profit": 110},
        {"signal_index": 1, "entry_index": 2, "side": "BUY", "stop": 95, "take_profit": 105},
    ]

    trades, unresolved = evaluator.simulate_fold(frame, signals, 0, 3)

    assert trades == []
    assert unresolved == 1
