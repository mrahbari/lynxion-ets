import hashlib

import pytest

from scripts.verify_exit_shadow_empty_cohort import verify


def _manifest(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_bytes(b"")
    return {
        "state": "NEW", "commit": "a" * 40, "historical_import_allowed": False,
        "event_count": 0, "run_id": "run", "activation_boundary_utc": "2026-09-12T15:41:59Z",
        "events_path": "events.jsonl", "events_sha256": hashlib.sha256(b"").hexdigest(),
    }


def test_accepts_new_empty_hash_bound_cohort(tmp_path):
    result = verify(_manifest(tmp_path), tmp_path, check_git=False)
    assert result["cohort"] == "NEW_EMPTY_COMMIT_BOUND"
    assert not result["authorizes_runtime"]


def test_rejects_nonempty_or_historical_import(tmp_path):
    manifest = _manifest(tmp_path)
    (tmp_path / "events.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="nonempty"):
        verify(manifest, tmp_path, check_git=False)
    manifest = _manifest(tmp_path)
    manifest["historical_import_allowed"] = True
    with pytest.raises(ValueError, match="new and empty"):
        verify(manifest, tmp_path, check_git=False)


def test_rejects_empty_ledger_hash_or_commit_drift(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["events_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        verify(manifest, tmp_path, check_git=False)
    manifest = _manifest(tmp_path)
    manifest["commit"] = "bad"
    with pytest.raises(ValueError, match="commit"):
        verify(manifest, tmp_path, check_git=False)
