import json

import pytest

from scripts.record_c35_signal import append_signal


def _signal(decision_time=1789117200, symbol="BTCUSDT"):
    return {
        "candidate": "C-35", "symbol": symbol, "side": "LONG",
        "decision_time": decision_time, "decision_bar_open": decision_time - 900,
        "entry_open_time": decision_time, "exit_open_time": decision_time + 7200,
        "decision_normalized_true_range": 0.006,
        "compression_median": 0.001,
        "compression_threshold": 0.002,
    }


def test_appends_one_virtual_signal_and_deduplicates(tmp_path):
    path = tmp_path / "signals.jsonl"
    assert append_signal(path, _signal(), input_sha256="a" * 64)
    assert not append_signal(path, _signal(), input_sha256="a" * 64)
    assert json.loads(path.read_text())["kind"] == "SIGNAL"


def test_rejects_second_unresolved_portfolio_signal(tmp_path):
    path = tmp_path / "signals.jsonl"
    append_signal(path, _signal(), input_sha256="a" * 64)
    with pytest.raises(ValueError, match="unresolved"):
        append_signal(path, _signal(1789120800, "ETHUSDT"), input_sha256="b" * 64)


def test_allows_new_signal_after_append_only_outcome(tmp_path):
    path = tmp_path / "signals.jsonl"
    first = _signal()
    append_signal(path, first, input_sha256="a" * 64)
    with path.open("a") as target:
        target.write(json.dumps({"kind": "OUTCOME", "signal_key": "BTCUSDT:1789117200"}) + "\n")
    assert append_signal(path, _signal(1789120800, "ETHUSDT"), input_sha256="b" * 64)


def test_rejects_pre_boundary_schedule(tmp_path):
    with pytest.raises(ValueError, match="boundary"):
        append_signal(tmp_path / "signals.jsonl", _signal(1789084800), input_sha256="a" * 64)
