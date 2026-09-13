import json
import subprocess
import sys

import pytest

from scripts.run_c35_hourly import COMMANDS, run_pipeline


def test_pipeline_runs_every_stage_in_frozen_fail_closed_order():
    calls = []
    def runner(command, **kwargs):
        calls.append(command[1:])
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"ok": True}), stderr="")
    result = run_pipeline(runner)
    assert result["pipeline"] == "PASS"
    assert calls == [list(parts) for parts in COMMANDS]
    outcome_index = next(i for i, call in enumerate(calls) if call[0] == "scripts/update_c35_outcomes.py")
    signal_index = next(i for i, call in enumerate(calls) if call[0] == "scripts/update_c35_signals.py")
    assert outcome_index < signal_index


def test_pipeline_stops_at_first_failed_precondition():
    calls = []
    def runner(command, **kwargs):
        calls.append(command[1])
        code = 1 if len(calls) == 2 else 0
        return subprocess.CompletedProcess(command, code, stdout="{}", stderr="integrity drift")
    with pytest.raises(RuntimeError, match="integrity drift"):
        run_pipeline(runner)
    assert len(calls) == 2


def test_pipeline_rejects_non_json_stage_output():
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="not-json", stderr="")
    with pytest.raises(RuntimeError, match="invalid JSON"):
        run_pipeline(runner)


def test_help_does_not_start_pipeline():
    result = subprocess.run(
        [sys.executable, "scripts/run_c35_hourly.py", "--help"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert '"pipeline"' not in result.stdout
