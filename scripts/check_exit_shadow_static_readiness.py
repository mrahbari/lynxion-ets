#!/usr/bin/env python3
"""Report repository-only exit-shadow activation prerequisites without broker access."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from scripts.build_exit_shadow_artifact_manifest import build_manifest
    from scripts.verify_exit_shadow_empty_cohort import verify as verify_cohort
    from scripts.verify_exit_shadow_fee_snapshot import verify as verify_fee
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from build_exit_shadow_artifact_manifest import build_manifest
    from verify_exit_shadow_empty_cohort import verify as verify_cohort
    from verify_exit_shadow_fee_snapshot import verify as verify_fee


ROOT = Path(__file__).resolve().parents[1]
COHORT_MANIFEST = Path("data/research/exit_shadow/cohort-20260912T164632Z/manifest.json")
FEE_SNAPSHOT = Path(
    "data/research/exit_shadow/bingx_perpetual_fee_snapshot-20260912T164438Z.json"
)


def check(root: Path, expected: dict[str, Any]) -> dict[str, Any]:
    actual = build_manifest(root)
    artifact_ok = actual == expected
    blockers = []
    if not artifact_ok:
        blockers.append("ARTIFACT_MANIFEST_DRIFT")
    try:
        cohort = json.loads((root / COHORT_MANIFEST).read_text(encoding="utf-8"))
        verify_cohort(cohort, root)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        blockers.append("NEW_EMPTY_COMMIT_BOUND_COHORT_REQUIRED")
    try:
        fee = json.loads((root / FEE_SNAPSHOT).read_text(encoding="utf-8"))
        verify_fee(fee)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        blockers.append("AUTHORITATIVE_PRE_ACTIVATION_BINGX_FEE_SNAPSHOT_REQUIRED")
    blockers.append("FRESH_SINGLE_RUNNER_READ_ONLY_STOP_VISIBILITY_EVIDENCE_REQUIRED")
    return {
        "candidate": "EXIT-SHADOW-PLUS12-LOCK5",
        "status": "BLOCKED" if blockers else "READY_FOR_CONTROLLED_RUNTIME_REVIEW",
        "artifact_manifest": "PASS" if artifact_ok else "FAIL",
        "blockers": blockers,
        "authorizes_runtime": False,
        "authorizes_broker_access": False,
        "authorizes_policy_change": False,
    }


def main() -> None:
    expected = json.loads((ROOT / "data/research/exit_shadow/artifact_manifest.json").read_text())
    print(json.dumps(check(ROOT, expected), sort_keys=True))


if __name__ == "__main__":
    main()
