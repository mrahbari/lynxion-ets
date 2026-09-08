import hashlib
import json

import pytest

from scripts.verify_c33_resume_preflight import verify_preflight


def fixture(tmp_path):
    manifest = tmp_path / "manifest.json"
    events = tmp_path / "events.jsonl"
    snapshot = tmp_path / "snapshot.json"
    manifest.write_text("manifest")
    events.write_text("events")
    audited = {
        "candidate": "C-33",
        "verdict": "COLLECTING",
        "activation_boundary": 100,
        "record_counts": {"session": 2},
        "session_count": 1,
        "active_session_count": 0,
        "latest_record_ms": 200_000,
        "eligible_completed_bucket_count": 351,
    }
    frozen = {
        **audited,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "events_sha256": hashlib.sha256(events.read_bytes()).hexdigest(),
    }
    snapshot.write_text(json.dumps(frozen))
    return snapshot, manifest, events, audited


def test_unchanged_stopped_preflight_is_verified(tmp_path):
    snapshot, manifest, events, audited = fixture(tmp_path)
    result = verify_preflight(snapshot, manifest, events, audit_fn=lambda *_: audited)
    assert result["status"] == "PREFLIGHT_VERIFIED"
    assert result["eligible_completed_bucket_count"] == 351


@pytest.mark.parametrize("target", ["manifest", "events"])
def test_any_artifact_byte_change_fails_closed(tmp_path, target):
    snapshot, manifest, events, audited = fixture(tmp_path)
    {"manifest": manifest, "events": events}[target].write_text("changed")
    with pytest.raises(ValueError, match="changed after preflight freeze"):
        verify_preflight(snapshot, manifest, events, audit_fn=lambda *_: audited)


def test_audit_metadata_drift_fails_closed(tmp_path):
    snapshot, manifest, events, audited = fixture(tmp_path)
    changed = {**audited, "eligible_completed_bucket_count": 352}
    with pytest.raises(ValueError, match="eligible_completed_bucket_count changed"):
        verify_preflight(snapshot, manifest, events, audit_fn=lambda *_: changed)


def test_active_session_fails_closed_even_if_snapshot_claims_it(tmp_path):
    snapshot, manifest, events, audited = fixture(tmp_path)
    audited["active_session_count"] = 1
    frozen = json.loads(snapshot.read_text())
    frozen["active_session_count"] = 1
    snapshot.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match="already has an active session"):
        verify_preflight(snapshot, manifest, events, audit_fn=lambda *_: audited)
