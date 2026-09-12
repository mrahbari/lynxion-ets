import subprocess
import sys

import pytest

from scripts.evaluate_c35_compression_release import UNIVERSE
from scripts.update_c35_signals import (
    _decision_times,
    _input_hash,
    evaluate_unrecorded,
    find_first_signal,
    verify_decision_bindings,
)


def _panel():
    return {
        symbol: [
            {"symbol": symbol, "open_time": 1789087500, "close": "1"},
            {"symbol": symbol, "open_time": 1789091100, "close": "2"},
        ] for symbol in UNIVERSE
    }


def test_decisions_require_common_exact_hour_bar():
    panel = _panel()
    assert _decision_times(panel) == [1789088400, 1789092000]
    panel["ADAUSDT"].pop()
    assert _decision_times(panel) == [1789088400]


def test_causal_hash_is_deterministic_and_changes_with_input():
    panel = _panel()
    first = _input_hash(panel, 1789092000)
    assert first == _input_hash(panel, 1789092000)
    panel["BTCUSDT"][0]["close"] = "1.1"
    assert first != _input_hash(panel, 1789092000)


def test_returns_first_ranked_signal_only():
    calls = []
    def evaluator(panel, decision_time, boundary):
        calls.append(decision_time)
        return None if len(calls) == 1 else {
            "candidate": "C-35", "symbol": "BTCUSDT", "decision_time": decision_time,
        }
    signal, digest = find_first_signal(_panel(), evaluator=evaluator)
    assert signal["decision_time"] == 1789092000
    assert len(digest) == 64
    assert calls == [1789088400, 1789092000]


def test_direct_cli_import_path_is_valid():
    result = subprocess.run(
        [sys.executable, "scripts/update_c35_signals.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_unrecorded_evaluation_skips_history_and_stops_at_signal():
    calls = []
    def evaluator(panel, decision_time, boundary):
        calls.append(decision_time)
        return {"candidate": "C-35"} if decision_time == 1789092000 else None
    results = evaluate_unrecorded(_panel(), {1789088400}, evaluator=evaluator)
    assert [item[0] for item in results] == [1789092000]
    assert results[0][1] == {"candidate": "C-35"}
    assert calls == [1789092000]


def test_decision_binding_accepts_exact_causal_panel():
    panel = _panel()
    decision_time = _decision_times(panel)[0]
    result = verify_decision_bindings(panel, {
        decision_time: {"input_sha256": _input_hash(panel, decision_time)},
    })
    assert result["integrity"] == "PASS"


def test_decision_binding_rejects_candle_or_hash_drift():
    panel = _panel()
    decision_time = _decision_times(panel)[-1]
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_decision_bindings(panel, {decision_time: {"input_sha256": "a" * 64}})

    incomplete = {symbol: rows[:-1] for symbol, rows in panel.items()}
    with pytest.raises(ValueError, match="no longer has complete"):
        verify_decision_bindings(incomplete, {
            decision_time: {"input_sha256": _input_hash(panel, decision_time)},
        })
