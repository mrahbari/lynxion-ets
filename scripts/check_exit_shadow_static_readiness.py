#!/usr/bin/env python3
"""Report repository-only exit-shadow activation prerequisites without broker access."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from scripts.build_exit_shadow_artifact_manifest import build_manifest
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from build_exit_shadow_artifact_manifest import build_manifest


ROOT = Path(__file__).resolve().parents[1]


def check(root: Path, expected: dict[str, Any]) -> dict[str, Any]:
    actual = build_manifest(root)
    artifact_ok = actual == expected
    blockers = []
    if not artifact_ok:
        blockers.append("ARTIFACT_MANIFEST_DRIFT")
    blockers.extend((
        "NEW_EMPTY_COMMIT_BOUND_COHORT_REQUIRED",
        "AUTHORITATIVE_PRE_ACTIVATION_BINGX_FEE_SNAPSHOT_REQUIRED",
        "FRESH_SINGLE_RUNNER_READ_ONLY_STOP_VISIBILITY_EVIDENCE_REQUIRED",
    ))
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
