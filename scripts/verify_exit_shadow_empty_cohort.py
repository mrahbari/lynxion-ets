#!/usr/bin/env python3
"""Verify a new commit-bound exit-shadow cohort without opening outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def verify(manifest: dict[str, Any], root: Path, *, check_git: bool = True) -> dict[str, Any]:
    if (
        manifest.get("state") != "NEW"
        or manifest.get("historical_import_allowed") is not False
        or manifest.get("event_count") != 0
        or not manifest.get("run_id")
        or not manifest.get("activation_boundary_utc")
    ):
        raise ValueError("exit-shadow cohort is not new and empty")
    events = root / str(manifest.get("events_path") or "")
    if not events.is_file() or events.stat().st_size != 0:
        raise ValueError("exit-shadow event ledger is missing or nonempty")
    if hashlib.sha256(events.read_bytes()).hexdigest() != manifest.get("events_sha256"):
        raise ValueError("exit-shadow empty ledger hash mismatch")
    commit = str(manifest.get("commit") or "")
    if len(commit) != 40:
        raise ValueError("exit-shadow cohort commit is invalid")
    if check_git:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root, check=False, capture_output=True,
        )
        if result.returncode:
            raise ValueError("exit-shadow cohort commit is not an ancestor of HEAD")
    return {
        "candidate": "EXIT-SHADOW-PLUS12-LOCK5",
        "cohort": "NEW_EMPTY_COMMIT_BOUND",
        "run_id": manifest["run_id"],
        "event_count": 0,
        "authorizes_runtime": False,
        "authorizes_broker_access": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/research/exit_shadow/cohort-20260912T164632Z/manifest.json"),
    )
    args = parser.parse_args()
    manifest = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    print(json.dumps(verify(manifest, ROOT), sort_keys=True))


if __name__ == "__main__":
    main()
