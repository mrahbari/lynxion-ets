#!/usr/bin/env python3
"""Resolve fail-closed forward cohort metadata without writing or starting runtime."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


REQUIRED = {
    "schema_version", "run_id", "activation_boundary_utc", "commit",
    "historical_import_allowed",
}


class ActivationCommitMismatch(ValueError):
    """Existing cohort belongs to a different immutable source revision."""


def _utc(value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError("activation boundary must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("activation boundary must be UTC")


def resolve(root: Path | str, head_commit: str, new_run_id: str,
            new_boundary_utc: str) -> dict[str, Any]:
    root = Path(root)
    manifest_path = root / "activation.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("activation manifest is unreadable or malformed") from error
        if not isinstance(manifest, dict) or set(manifest) != REQUIRED:
            raise ValueError("activation manifest schema is invalid")
        if manifest["schema_version"] != 1 or manifest["historical_import_allowed"] is not False:
            raise ValueError("activation manifest safety fields are invalid")
        if not all(isinstance(manifest[key], str) and manifest[key].strip()
                   for key in ("run_id", "commit")):
            raise ValueError("activation manifest identity is invalid")
        _utc(manifest["activation_boundary_utc"])
        if manifest["commit"] != head_commit:
            raise ActivationCommitMismatch(
                "activation manifest commit differs from HEAD; use a new empty cohort root"
            )
        return {"state": "CONTINUE", **manifest}

    if root.exists() and any(root.iterdir()):
        raise ValueError("new cohort root is not empty")
    if not head_commit.strip() or not new_run_id.strip():
        raise ValueError("new cohort identity is invalid")
    _utc(new_boundary_utc)
    return {
        "state": "NEW", "schema_version": 1, "run_id": new_run_id,
        "activation_boundary_utc": new_boundary_utc, "commit": head_commit,
        "historical_import_allowed": False,
    }


def resolve_launch(root: Path | str, head_commit: str, new_run_id: str,
                   new_boundary_utc: str, *, auto_rotate_commit_mismatch: bool = False
                   ) -> dict[str, Any]:
    """Resolve launch metadata and safely rotate only a default commit-mismatched cohort."""

    root = Path(root)
    try:
        metadata = resolve(root, head_commit, new_run_id, new_boundary_utc)
    except ActivationCommitMismatch:
        if not auto_rotate_commit_mismatch:
            raise
        root = root / "cohorts" / f"auto-{head_commit[:12]}"
        metadata = resolve(root, head_commit, new_run_id, new_boundary_utc)
    return {"root": str(root), **metadata}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--new-run-id", required=True)
    parser.add_argument("--new-boundary-utc", required=True)
    parser.add_argument("--auto-rotate-commit-mismatch", action="store_true")
    args = parser.parse_args()
    print(json.dumps(resolve_launch(
        args.root, args.head, args.new_run_id, args.new_boundary_utc,
        auto_rotate_commit_mismatch=args.auto_rotate_commit_mismatch,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
