#!/usr/bin/env python3
"""Read-only TASK-0151 forward-exit cohort gate auditor."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.observability.exit_event_ledger import ExitEventLedger
from infrastructure.observability.position_identity_snapshot import PositionIdentitySnapshot


DEFAULT_ROOT = Path("data/observability/forward_exit")


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must be UTC")
    return parsed


def audit(root: Path | str = DEFAULT_ROOT) -> dict[str, Any]:
    root = Path(root)
    violations = Counter()
    manifest: dict[str, Any] = {}
    identities: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    try:
        manifest = json.loads((root / "activation.json").read_text(encoding="utf-8"))
        required = {"schema_version", "run_id", "activation_boundary_utc", "commit", "historical_import_allowed"}
        if not required <= set(manifest) or manifest.get("schema_version") != 1:
            raise ValueError("activation manifest is invalid")
        if manifest.get("historical_import_allowed") is not False:
            violations["historical_import_allowed"] += 1
        boundary = _utc(manifest["activation_boundary_utc"])
    except Exception:
        violations["manifest_invalid"] += 1
        boundary = datetime.max.replace(tzinfo=timezone.utc)

    snapshot_path = root / "position_identities.json"
    try:
        PositionIdentitySnapshot(snapshot_path).validate_file()
        if snapshot_path.exists():
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            identities = list(payload["records"].values())
    except Exception:
        violations["snapshot_corrupt"] += 1

    known_ids: set[str] = set()
    previous_time: datetime | None = None
    for path in sorted((root / "events").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                event_time = _utc(event.get("event_time_utc"))
                ExitEventLedger.validate_event(event, known_ids)
                if event["event_id"] in known_ids:
                    violations["duplicate_event_ids"] += 1
                if previous_time is not None and event_time < previous_time:
                    violations["event_time_regressions"] += 1
                if event_time <= boundary:
                    violations["pre_boundary_events"] += 1
                if manifest and event.get("run_id") != manifest.get("run_id"):
                    violations["foreign_run_events"] += 1
                known_ids.add(event["event_id"])
                previous_time = event_time
                events.append(event)
            except Exception as error:
                message = str(error)
                if "causal_event_id" in message:
                    violations["unknown_causal_references"] += 1
                elif "sensitive" in message:
                    violations["sensitive_field_violations"] += 1
                else:
                    violations["corrupt_events"] += 1

    completed = [item for item in identities if item.get("lifecycle_state") in {
        "CLOSURE_OBSERVED", "TERMINAL_EVIDENCE_COMPLETE"
    }]
    sides = Counter(item.get("side") for item in completed)
    symbols = Counter(item.get("symbol") for item in completed)
    event_types = Counter(item.get("event_type") for item in events)
    report = {
        "schema_version": 1,
        "manifest": {
            key: manifest.get(key) for key in (
                "run_id", "activation_boundary_utc", "commit", "historical_import_allowed"
            )
        },
        "counts": {
            "identities": len(identities),
            "completed_identities": len(completed),
            "events": len(events),
            "event_types": dict(sorted(event_types.items())),
            "completed_by_symbol": dict(sorted(symbols.items())),
            "completed_by_side": dict(sorted(sides.items())),
        },
        "violations": dict(sorted(violations.items())),
        "verdict": "DATA_INVALID" if sum(violations.values()) else "COLLECTING",
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    print(json.dumps(audit(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
