import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_delta_neutral_funding_c23.py"
    spec = importlib.util.spec_from_file_location("edge_c23", path)
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded


def test_threshold_excludes_current_rate(tmp_path):
    m = module(); path = tmp_path / "funding.csv"
    frame = pd.DataFrame({"timestamp": range(200), "funding_rate": [0.001] * 200}); frame.to_csv(path, index=False)
    baseline = m.causal_funding(path); frame.loc[180, "funding_rate"] = 1.0; frame.to_csv(path, index=False)
    changed = m.causal_funding(path)
    assert baseline.loc[180, "threshold"] == changed.loc[180, "threshold"]


def fixture():
    m = module(); rates = [0.001] * 180 + [0.01, 0.004, 0.001]
    funding = pd.DataFrame({"timestamp": [i * 28800 for i in range(len(rates))], "funding_rate": rates,
                            "threshold": [float("nan")] * 180 + [0.001] * 3,
                            "next_timestamp": [i * 28800 for i in range(1, len(rates))] + [float("nan")],
                            "next_rate": rates[1:] + [float("nan")]})
    times = range(0, len(rates) * 28800 + 1800, 900)
    spot = pd.Series(100.0, index=list(times)); perp = pd.Series(100.0, index=list(times))
    return m, funding, spot, perp


def test_exact_next_open_and_next_settlement_exit():
    m, funding, spot, perp = fixture(); trades, _ = m.symbol_events("BTCUSDT", funding, spot, perp, 0, 10**10)
    trade = trades[0]
    assert trade["entry_timestamp"] == trade["signal_timestamp"] + 900
    assert trade["exit_timestamp"] == trade["next_settlement"] + 900


def test_short_receives_next_positive_funding_and_capital_normalizes():
    m, funding, spot, perp = fixture(); spot.loc[funding.loc[181, "timestamp"] + 900] = 102
    trades, _ = m.symbol_events("BTCUSDT", funding, spot, perp, 0, 10**10)
    trade = trades[0]
    assert trade["spot_return"] == pytest.approx(0.02)
    assert trade["funding_return"] == pytest.approx(0.004 / 2)
    assert trade["gross_return"] == pytest.approx((0.02 + 0.0 + 0.004) / 2)


def test_missing_exact_bar_rejects_event():
    m, funding, spot, perp = fixture(); spot = spot.drop(funding.loc[180, "timestamp"] + 900)
    trades, census = m.symbol_events("BTCUSDT", funding, spot, perp, 0, 10**10)
    assert len(trades) == 1 and census["missing_exact_price"] == 1


def test_overlap_and_cost_are_enforced():
    m, funding, spot, perp = fixture()
    funding.loc[180, "next_timestamp"] = funding.loc[182, "timestamp"]
    trades, census = m.symbol_events("BTCUSDT", funding, spot, perp, 0, 10**10)
    assert census["overlap_rejected"] == 1
    assert m.metrics([{"gross_return": 0.01}], 0.002)["expectancy"] == pytest.approx(0.008)
