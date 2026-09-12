from scripts.build_exit_shadow_artifact_manifest import build_manifest
from scripts.check_exit_shadow_static_readiness import check


def test_live_manifest_is_reproducible_and_static_gate_is_non_authorizing():
    from scripts.check_exit_shadow_static_readiness import ROOT
    expected = build_manifest(ROOT)
    result = check(ROOT, expected)
    assert result["artifact_manifest"] == "PASS"
    assert result["status"] == "BLOCKED"
    assert len(result["blockers"]) == 3
    assert not result["authorizes_runtime"]
    assert not result["authorizes_broker_access"]
    assert not result["authorizes_policy_change"]


def test_artifact_drift_adds_explicit_blocker():
    from scripts.check_exit_shadow_static_readiness import ROOT
    expected = build_manifest(ROOT)
    expected["artifact_set_sha256"] = "0" * 64
    result = check(ROOT, expected)
    assert result["blockers"][0] == "ARTIFACT_MANIFEST_DRIFT"
