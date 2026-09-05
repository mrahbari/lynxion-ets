import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.resolve_forward_exit_cohort import resolve


BOUNDARY = "2026-09-05T17:00:00+00:00"


def _manifest(root, commit="abc"):
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1, "run_id": "run-old", "activation_boundary_utc": BOUNDARY,
        "commit": commit, "historical_import_allowed": False,
    }
    (root / "activation.json").write_text(json.dumps(payload))
    return payload


def test_same_commit_continues_exact_frozen_metadata(tmp_path):
    expected = _manifest(tmp_path, "abc")
    result = resolve(tmp_path, "abc", "unused", BOUNDARY)
    assert result == {"state": "CONTINUE", **expected}


def test_commit_mismatch_refuses_old_cohort(tmp_path):
    _manifest(tmp_path, "old")
    with pytest.raises(ValueError, match="differs from HEAD"):
        resolve(tmp_path, "new", "run-new", BOUNDARY)


def test_malformed_manifest_fails_closed(tmp_path):
    (tmp_path / "activation.json").write_text("not-json")
    with pytest.raises(ValueError, match="malformed"):
        resolve(tmp_path, "abc", "run-new", BOUNDARY)


def test_nonempty_new_root_without_manifest_is_rejected(tmp_path):
    (tmp_path / "events").mkdir()
    with pytest.raises(ValueError, match="not empty"):
        resolve(tmp_path, "abc", "run-new", BOUNDARY)


def test_empty_new_root_resolves_actual_head_and_new_metadata_without_writing(tmp_path):
    before = list(tmp_path.iterdir())
    result = resolve(tmp_path, "new-head", "run-new", BOUNDARY)
    assert result == {
        "state": "NEW", "schema_version": 1, "run_id": "run-new",
        "activation_boundary_utc": BOUNDARY, "commit": "new-head",
        "historical_import_allowed": False,
    }
    assert list(tmp_path.iterdir()) == before


def test_wrapper_commit_mismatch_exits_before_runtime_entrypoint(tmp_path):
    project_root = Path(__file__).resolve().parents[2]
    shutil.copy(project_root / "lynxion", tmp_path / "lynxion")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(project_root / "scripts" / "resolve_forward_exit_cohort.py", scripts)
    sentinel = tmp_path / "runtime_started"
    (tmp_path / "run_trading_system.py").write_text(
        f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('started')\n"
    )
    cohort = tmp_path / "old-cohort"
    _manifest(cohort, "old-head")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "pgrep").write_text("#!/bin/sh\nexit 1\n")
    (fake_bin / "git").write_text("#!/bin/sh\necho new-head\n")
    for command in fake_bin.iterdir():
        command.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["LYNXION_FORWARD_EXIT_ROOT_OVERRIDE"] = str(cohort)
    result = subprocess.run(
        ["zsh", "lynxion"], cwd=tmp_path, env=env, text=True,
        capture_output=True, timeout=10,
    )
    assert result.returncode != 0
    assert "commit differs from HEAD" in result.stderr
    assert not sentinel.exists()
