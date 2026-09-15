#!/usr/bin/env python3
"""Report whether the active C-33 cohort crossed a sparse evidence milestone."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.materialize_c33_warmup import materialize
    from scripts.verify_c33_warmup_snapshot import verify
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from materialize_c33_warmup import materialize
    from verify_c33_warmup_snapshot import verify


MILESTONES = (25, 100, 500, 1_000, 2_000, 4_000, 8_000, 8_640)
DEFAULT_PREVIOUS_SNAPSHOT = Path("data/research/c33/warmup_snapshot_task0356.json")


def checkpoint_status(previous_count: int, current_count: int) -> dict[str, Any]:
    if isinstance(previous_count, bool) or isinstance(current_count, bool):
        raise ValueError("bucket counts must be integers")
    if not isinstance(previous_count, int) or not isinstance(current_count, int):
        raise ValueError("bucket counts must be integers")
    if previous_count < 0 or current_count < previous_count:
        raise ValueError("current bucket count cannot precede the verified checkpoint")
    crossed = [value for value in MILESTONES if previous_count < value <= current_count]
    next_milestone = next((value for value in MILESTONES if value > current_count), None)
    return {
        "candidate": "C-33",
        "verdict": "COLLECTING",
        "checkpoint_due": bool(crossed),
        "previous_verified_bucket_count": previous_count,
        "current_eligible_bucket_count": current_count,
        "crossed_milestones": crossed,
        "next_milestone": next_milestone,
    }


def check(previous_snapshot: Path, activation_manifest: Path, events: Path | None = None) -> dict[str, Any]:
    previous = verify(previous_snapshot)
    current = materialize(activation_manifest, events)
    return checkpoint_status(previous["eligible_bucket_count"], current["eligible_bucket_count"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--previous-snapshot",
        type=Path,
        default=DEFAULT_PREVIOUS_SNAPSHOT,
    )
    parser.add_argument(
        "--activation-manifest",
        type=Path,
        default=Path("data/research/c33/activation_manifest.json"),
    )
    parser.add_argument("--events", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.previous_snapshot, args.activation_manifest, args.events), sort_keys=True))


if __name__ == "__main__":
    main()
