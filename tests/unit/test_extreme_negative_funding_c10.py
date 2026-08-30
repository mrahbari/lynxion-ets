import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_extreme_negative_funding_c10.py"
    spec = importlib.util.spec_from_file_location("edge_c10", path)
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded


def test_rolling_percentile_excludes_current_observation(tmp_path):
    evaluator = module(); path = tmp_path / "funding.csv"
    frame = pd.DataFrame({"timestamp": range(400), "funding_rate": [-0.001] * 400}); frame.to_csv(path, index=False)
    baseline = evaluator.causal_funding(path); frame.loc[365, "funding_rate"] = -0.1; frame.to_csv(path, index=False)
    changed = evaluator.causal_funding(path)
    assert baseline.loc[365, "threshold"] == changed.loc[365, "threshold"]


def fixtures():
    evaluator = module(); funding = pd.DataFrame({
        "timestamp": [item * 28800 for item in range(410)],
        "funding_rate": [-0.001] * 365 + [-0.01] + [-0.001] * 44,
        "threshold": [float("nan")] * 365 + [-0.001] * 45,
    })
    price = pd.DataFrame({"timestamp": [item * 900 for item in range(14000)], "open": [100.0] * 14000}).set_index("timestamp")
    return evaluator, funding, price


def test_entry_is_first_open_after_settlement_and_exit_is_24h_later():
    evaluator, funding, price = fixtures(); trades, _ = evaluator.symbol_trades("BTCUSDT", funding, price)
    trade = trades[0]
    assert trade["entry_timestamp"] > trade["signal_timestamp"]
    assert trade["exit_timestamp"] - trade["entry_timestamp"] == 96 * 900


def test_funding_cashflows_after_entry_are_added_for_long():
    evaluator, funding, price = fixtures(); trades, _ = evaluator.symbol_trades("BTCUSDT", funding, price)
    assert trades[0]["funding_return"] == pytest.approx(0.001 * 3)


def test_overlapping_signals_are_rejected():
    evaluator, funding, price = fixtures(); funding.loc[366, "funding_rate"] = -0.01
    trades, census = evaluator.symbol_trades("BTCUSDT", funding, price)
    assert census["overlap_rejected"] >= 1
    assert all(right["entry_timestamp"] >= left["exit_timestamp"] for left, right in zip(trades, trades[1:]))


def test_cost_is_applied_to_funding_inclusive_return():
    evaluator = module(); trades = [{"gross_return": 0.01}, {"gross_return": -0.01}]
    assert evaluator.metrics(trades, 0.003)["expectancy"] == pytest.approx(-0.003)
