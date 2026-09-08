#!/usr/bin/env python3
"""Verify the frozen C-33 pre-resume baseline against the untouched ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.audit_c33_collection import audit
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from audit_c33_collection import audit


AUDIT_FIELDS = (
    "candidate",
    "verdict",
    "activation_boundary",
    "record_counts",
    "session_count",
    "active_session_count",
    "latest_record_ms",
    "eligible_completed_bucket_count",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_preflight(
    snapshot_path: Path,
    manifest_path: Path,
    events_path: Path,
    *,
    audit_fn: Callable[[Path, Path], dict[str, Any]] = audit,
) -> dict[str, Any]:
    try:
        frozen = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("preflight snapshot is unreadable") from error
    if not isinstance(frozen, dict):
        raise ValueError("preflight snapshot must contain an object")
    if frozen.get("manifest_sha256") != _sha256(manifest_path):
        raise ValueError("activation manifest changed after preflight freeze")
    if frozen.get("events_sha256") != _sha256(events_path):
        raise ValueError("event ledger changed after preflight freeze")

    current = audit_fn(manifest_path, events_path)
    for field in AUDIT_FIELDS:
        if frozen.get(field) != current.get(field):
            raise ValueError(f"audited {field} changed after preflight freeze")
    if current["active_session_count"] != 0:
        raise ValueError("collector already has an active session")
    return {
        "candidate": "C-33",
        "verdict": "COLLECTING",
        "status": "PREFLIGHT_VERIFIED",
        "eligible_completed_bucket_count": current["eligible_completed_bucket_count"],
        "latest_record_ms": current["latest_record_ms"],
        "manifest_sha256": frozen["manifest_sha256"],
        "events_sha256": frozen["events_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot", type=Path, default=Path("data/research/c33/resume_preflight_task0214.json")
    )
    parser.add_argument(
        "--activation-manifest", type=Path, default=Path("data/research/c33/activation_manifest.json")
    )
    parser.add_argument("--events", type=Path, default=Path("data/research/c33/events.jsonl"))
    args = parser.parse_args()
    print(json.dumps(verify_preflight(args.snapshot, args.activation_manifest, args.events), sort_keys=True))


if __name__ == "__main__":
    main()
