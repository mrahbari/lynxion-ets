#!/usr/bin/env python3
"""Fail-closed verification of an append-only C-33 collector resume."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.collect_c33_liquidation_events import SYMBOLS
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from collect_c33_liquidation_events import SYMBOLS


MIN_HEARTBEATS_AFTER_FIRST_INTERVAL = 5
MIN_KLINES_AFTER_FIRST_INTERVAL = 5 * len(SYMBOLS)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("audit snapshot must contain an object")
    return value


def verify_resume(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Verify the first complete interval after the documented resume sequence."""
    for label, snapshot in (("before", before), ("after", after)):
        if snapshot.get("candidate") != "C-33" or snapshot.get("verdict") != "COLLECTING":
            raise ValueError(f"{label} snapshot is not an admitted C-33 audit")
        if not isinstance(snapshot.get("record_counts"), dict):
            raise ValueError(f"{label} record counts are missing")
        for field in (
            "activation_boundary",
            "session_count",
            "active_session_count",
            "latest_record_ms",
            "eligible_completed_bucket_count",
        ):
            value = snapshot.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{label} {field} is invalid")

    if before["activation_boundary"] != after["activation_boundary"]:
        raise ValueError("activation boundary changed across resume")
    if before["active_session_count"] != 0:
        raise ValueError("pre-resume audit must have zero active sessions")
    if after["active_session_count"] != 1:
        raise ValueError("post-resume audit must have exactly one active session")
    if after["session_count"] != before["session_count"] + 1:
        raise ValueError("resume must add exactly one session")
    if after["latest_record_ms"] <= before["latest_record_ms"]:
        raise ValueError("post-resume records must be strictly newer")
    if after["eligible_completed_bucket_count"] < before["eligible_completed_bucket_count"]:
        raise ValueError("eligible bucket count regressed")

    before_counts = before["record_counts"]
    after_counts = after["record_counts"]
    for record_type in set(before_counts) | set(after_counts):
        old = before_counts.get(record_type, 0)
        new = after_counts.get(record_type, 0)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (old, new)):
            raise ValueError("record counts must be non-negative integers")
        if new < old:
            raise ValueError(f"{record_type} record count regressed")

    increments = {
        record_type: after_counts.get(record_type, 0) - before_counts.get(record_type, 0)
        for record_type in set(before_counts) | set(after_counts)
    }
    if increments.get("session", 0) != 1:
        raise ValueError("resume must append exactly one STARTED session record")
    if increments.get("heartbeat", 0) < MIN_HEARTBEATS_AFTER_FIRST_INTERVAL:
        raise ValueError("first complete interval lacks five new heartbeats")
    if increments.get("kline_close", 0) < MIN_KLINES_AFTER_FIRST_INTERVAL:
        raise ValueError("first complete interval lacks the full symbol-minute kline set")

    return {
        "candidate": "C-33",
        "verdict": "COLLECTING",
        "status": "RESUME_VERIFIED",
        "activation_boundary": after["activation_boundary"],
        "active_session_count": 1,
        "session_count": after["session_count"],
        "eligible_completed_bucket_count": after["eligible_completed_bucket_count"],
        "record_count_increments": dict(sorted(increments.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_resume(_load(args.before), _load(args.after)), sort_keys=True))


if __name__ == "__main__":
    main()
