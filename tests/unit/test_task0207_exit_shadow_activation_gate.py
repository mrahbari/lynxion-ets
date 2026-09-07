from pathlib import Path

from infrastructure.research.exit_shadow_activation_gate import exit_shadow_activation_gate
from scripts.build_exit_shadow_artifact_manifest import build_manifest


ROOT = Path(__file__).resolve().parents[2]


def cohort(**updates):
    value = {
        "state": "NEW", "commit": "abc", "historical_import_allowed": False,
        "event_count": 0, "run_id": "run-new",
        "activation_boundary_utc": "2026-09-07T00:00:00+00:00",
    }
    value.update(updates)
    return value


def fee(**updates):
    value = {"eligible": True, "snapshot_sha256": "a" * 64}
    value.update(updates)
    return value


def safety(**updates):
    value = {
        "mode": "TESTNET", "live_trading": False, "runner_count": 1,
        "positions_missing_stop_loss": [], "protection_check_read_only": True,
    }
    value.update(updates)
    return value


def gate(**updates):
    values = {
        "root": ROOT, "artifact_manifest": build_manifest(ROOT),
        "proposed_cohort": cohort(), "fee_schedule": fee(),
        "safety_evidence": safety(), "expected_commit": "abc",
    }
    values.update(updates)
    return exit_shadow_activation_gate(**values)


def test_all_evidence_is_readiness_not_runtime_authority():
    result = gate()
    assert result["status"] == "READY_FOR_CONTROLLED_RUNTIME_REVIEW"
    assert result["authorizes_runtime"] is False
    assert result["authorizes_broker_mutation"] is False


def test_missing_stops_or_live_mode_blocks():
    result = gate(safety_evidence=safety(positions_missing_stop_loss=["SOLUSDT"]))
    assert result["status"] == "BLOCKED"
    assert result["gates"]["vst_protection"] is False
    assert gate(safety_evidence=safety(live_trading=True))["status"] == "BLOCKED"


def test_nonempty_or_mismatched_cohort_blocks():
    assert gate(proposed_cohort=cohort(event_count=1))["status"] == "BLOCKED"
    assert gate(proposed_cohort=cohort(commit="other"))["status"] == "BLOCKED"


def test_fee_or_artifact_drift_blocks():
    assert gate(fee_schedule=fee(eligible=False))["status"] == "BLOCKED"
    manifest = build_manifest(ROOT)
    manifest["artifact_set_sha256"] = "0" * 64
    assert gate(artifact_manifest=manifest)["status"] == "BLOCKED"
