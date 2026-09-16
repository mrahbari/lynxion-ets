from scripts.build_exit_shadow_artifact_manifest import build_manifest
from scripts.check_exit_shadow_static_readiness import check, recorded_preflight_blockers


def test_live_manifest_is_reproducible_and_static_gate_is_non_authorizing():
    from scripts.check_exit_shadow_static_readiness import ROOT
    expected = build_manifest(ROOT)
    result = check(ROOT, expected)
    assert result["artifact_manifest"] == "PASS"
    assert result["status"] == "BLOCKED"
    assert result["blockers"] == [
        "RECORDED_RUNNER_COUNT_NOT_ONE",
        "RECORDED_UNEXPECTED_PENDING_ENTRY_REQUIRES_OPERATOR_DECISION",
        "FRESH_SINGLE_RUNNER_READ_ONLY_STOP_VISIBILITY_EVIDENCE_REQUIRED"
    ]
    assert not result["authorizes_runtime"]
    assert not result["authorizes_broker_access"]
    assert not result["authorizes_policy_change"]


def test_artifact_drift_adds_explicit_blocker():
    from scripts.check_exit_shadow_static_readiness import ROOT
    expected = build_manifest(ROOT)
    expected["artifact_set_sha256"] = "0" * 64
    result = check(ROOT, expected)
    assert result["blockers"][0] == "ARTIFACT_MANIFEST_DRIFT"


def test_recorded_preflight_is_context_only_and_malformed_input_is_ignored(tmp_path):
    path = tmp_path / "data/research/exit_shadow"
    path.mkdir(parents=True)
    (path / "safety_preflight-20260915T193424Z.json").write_text("[]")
    assert recorded_preflight_blockers(tmp_path) == []
