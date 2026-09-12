import json

import pytest

from scripts.record_c35_decision import append_decision, read_decisions


def _signal(decision_time=1789117200):
    return {
        "candidate": "C-35", "symbol": "BTCUSDT", "side": "LONG",
        "decision_time": decision_time, "decision_normalized_true_range": 0.006,
        "compression_median": 0.001, "compression_threshold": 0.002,
        "entry_open_time": decision_time, "exit_open_time": decision_time + 7200,
    }


def test_appends_hash_bound_no_signal_decision(tmp_path):
    path = tmp_path / "decisions.jsonl"
    assert append_decision(path, decision_time=1789117200, input_sha256="a" * 64, signal=None)
    row = json.loads(path.read_text())
    assert row["verdict"] == "NO_SIGNAL"
    assert row["selected"] is None


def test_appends_only_selected_signal_fields(tmp_path):
    path = tmp_path / "decisions.jsonl"
    append_decision(path, decision_time=1789117200, input_sha256="b" * 64, signal=_signal())
    row = read_decisions(path)[1789117200]
    assert row["verdict"] == "SIGNAL"
    assert row["selected"]["symbol"] == "BTCUSDT"


def test_duplicate_decision_is_idempotent(tmp_path):
    path = tmp_path / "decisions.jsonl"
    append_decision(path, decision_time=1789117200, input_sha256="a" * 64, signal=None)
    assert not append_decision(path, decision_time=1789117200, input_sha256="a" * 64, signal=None)


def test_rejects_signal_time_mismatch_and_pre_boundary(tmp_path):
    with pytest.raises(ValueError, match="time mismatch"):
        append_decision(
            tmp_path / "decisions.jsonl", decision_time=1789117200,
            input_sha256="a" * 64, signal=_signal(1789120800),
        )
    with pytest.raises(ValueError, match="boundary"):
        append_decision(
            tmp_path / "decisions.jsonl", decision_time=1789084800,
            input_sha256="a" * 64, signal=None,
        )


def test_read_rejects_tampered_hash_or_verdict_payload(tmp_path):
    path = tmp_path / "decisions.jsonl"
    append_decision(path, decision_time=1789117200, input_sha256="a" * 64, signal=None)
    row = json.loads(path.read_text())
    row["input_sha256"] = "bad"
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="provenance"):
        read_decisions(path)

    row["input_sha256"] = "a" * 64
    row["selected"] = _signal()["symbol"]
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="no-signal"):
        read_decisions(path)


def test_read_rejects_selected_signal_schedule_tampering(tmp_path):
    path = tmp_path / "decisions.jsonl"
    append_decision(path, decision_time=1789117200, input_sha256="a" * 64, signal=_signal())
    row = json.loads(path.read_text())
    row["selected"]["exit_open_time"] -= 900
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="selected signal"):
        read_decisions(path)
