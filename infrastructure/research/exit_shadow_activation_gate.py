"""Pure activation-readiness gate for the frozen prospective exit shadow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.build_exit_shadow_artifact_manifest import build_manifest


def exit_shadow_activation_gate(
    *, root: Path, artifact_manifest: dict[str, Any], proposed_cohort: dict[str, Any],
    fee_schedule: dict[str, Any], safety_evidence: dict[str, Any],
    expected_commit: str,
) -> dict[str, Any]:
    """Return readiness only; never starts a runtime or accesses a broker."""
    gates: dict[str, bool] = {}
    try:
        gates["artifact_manifest"] = build_manifest(root) == artifact_manifest
    except FileNotFoundError:
        gates["artifact_manifest"] = False
    gates["empty_commit_bound_cohort"] = (
        proposed_cohort.get("state") == "NEW"
        and proposed_cohort.get("commit") == expected_commit
        and proposed_cohort.get("historical_import_allowed") is False
        and proposed_cohort.get("event_count") == 0
        and bool(proposed_cohort.get("run_id"))
        and bool(proposed_cohort.get("activation_boundary_utc"))
    )
    gates["fee_schedule"] = (
        fee_schedule.get("eligible") is True
        and len(str(fee_schedule.get("snapshot_sha256") or "")) == 64
    )
    gates["vst_protection"] = (
        safety_evidence.get("mode") == "TESTNET"
        and safety_evidence.get("live_trading") is False
        and safety_evidence.get("runner_count") == 1
        and safety_evidence.get("positions_missing_stop_loss") == []
        and safety_evidence.get("protection_check_read_only") is True
    )
    return {
        "status": "READY_FOR_CONTROLLED_RUNTIME_REVIEW" if all(gates.values()) else "BLOCKED",
        "gates": gates,
        "authorizes_runtime": False,
        "authorizes_broker_mutation": False,
    }
