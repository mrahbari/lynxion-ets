import pytest

from scripts.resolve_c35_outcome import resolve_outcome
from scripts.verify_c35_signal_ledger import verify


def _signal():
    return {
        "kind": "SIGNAL", "candidate": "C-35", "signal_key": "BTCUSDT:1789117200",
        "symbol": "BTCUSDT", "side": "LONG", "decision_time": 1789117200,
        "decision_bar_open": 1789116300, "entry_open_time": 1789117200,
        "exit_open_time": 1789124400, "input_sha256": "a" * 64,
    }


def _outcome():
    candles = [{"open_time": 1789117200 + index * 900, "open": "100"} for index in range(9)]
    return resolve_outcome(_signal(), candles, [], funding_coverage_complete=True)


def test_accepts_empty_and_complete_ledger():
    assert verify([])["integrity"] == "PASS"
    assert verify([_signal(), _outcome()]) == {
        "candidate": "C-35", "integrity": "PASS", "signals": 1,
        "completed_outcomes": 1, "unresolved_signals": 0,
    }


def test_rejects_signal_schedule_or_provenance_tampering():
    with pytest.raises(ValueError, match="schedule"):
        verify([{**_signal(), "exit_open_time": 1789123500}])
    with pytest.raises(ValueError, match="provenance"):
        verify([{**_signal(), "input_sha256": "bad"}])


def test_rejects_outcome_identity_tampering():
    with pytest.raises(ValueError, match="identity mismatch"):
        verify([_signal(), {**_outcome(), "side": "SHORT"}])


def test_rejects_nonfinite_or_unproven_outcome():
    with pytest.raises(ValueError, match="numeric"):
        verify([_signal(), {**_outcome(), "gross_return": float("nan")}])
    with pytest.raises(ValueError, match="completion evidence"):
        verify([_signal(), {**_outcome(), "evidence_sha256": "bad"}])
