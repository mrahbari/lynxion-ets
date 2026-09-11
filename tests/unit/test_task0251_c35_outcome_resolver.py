import json

import pytest

from scripts.record_c35_signal import append_outcome, append_signal
from scripts.resolve_c35_outcome import resolve_outcome


def _signal(side="LONG"):
    return {
        "kind": "SIGNAL", "candidate": "C-35", "signal_key": "BTCUSDT:1789117200",
        "symbol": "BTCUSDT", "side": side, "decision_time": 1789117200,
        "decision_bar_open": 1789116300, "entry_open_time": 1789117200,
        "exit_open_time": 1789124400, "decision_normalized_true_range": 0.006,
        "compression_median": 0.001, "compression_threshold": 0.002,
    }


def _candles(entry=100.0, exit=102.0):
    rows = []
    for index in range(9):
        price = entry if index < 8 else exit
        rows.append({"open_time": 1789117200 + index * 900, "open": str(price)})
    return rows


def test_resolves_long_with_strict_funding_boundary_and_costs():
    funding = [
        {"funding_time": 1789117200, "funding_rate": 0.1},
        {"funding_time": 1789120800, "funding_rate": 0.001},
    ]
    outcome = resolve_outcome(_signal(), _candles(), funding, funding_coverage_complete=True)
    assert outcome["funding_settlement_count"] == 1
    assert outcome["funding_return"] == -0.001
    assert outcome["net_return_primary_0_30pct"] == pytest.approx(0.016)


def test_resolves_short_direction_and_funding_sign():
    outcome = resolve_outcome(
        _signal("SHORT"), _candles(100, 98),
        [{"funding_time": 1789120800, "funding_rate": 0.001}],
        funding_coverage_complete=True,
    )
    assert outcome["gross_return"] == pytest.approx(100 / 98 - 1)
    assert outcome["funding_return"] == 0.001


def test_rejects_gap_and_incomplete_funding():
    with pytest.raises(ValueError, match="candle interval"):
        resolve_outcome(_signal(), _candles()[:-1], [], funding_coverage_complete=True)
    with pytest.raises(ValueError, match="funding coverage"):
        resolve_outcome(_signal(), _candles(), [], funding_coverage_complete=False)


def test_append_outcome_requires_signal_and_is_idempotent(tmp_path):
    path = tmp_path / "signals.jsonl"
    outcome = resolve_outcome(_signal(), _candles(), [], funding_coverage_complete=True)
    with pytest.raises(ValueError, match="preceding signal"):
        append_outcome(path, outcome)
    signal = _signal()
    signal.pop("kind")
    signal.pop("signal_key")
    append_signal(path, signal, input_sha256="a" * 64)
    assert append_outcome(path, outcome)
    assert not append_outcome(path, outcome)
    assert [json.loads(line)["kind"] for line in path.read_text().splitlines()] == ["SIGNAL", "OUTCOME"]
