#!/usr/bin/env python3
"""Fail closed before opening C-35 aggregate economics."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "candidate": "C-35",
    "status": "PREPARED_NOT_ACTIVATED",
    "aggregate_economics_opened": False,
    "bootstrap_seed": 350035,
    "bootstrap_samples": 10_000,
    "minimum_positions": 240,
    "minimum_positions_per_side": 80,
    "minimum_utc_weeks": 8,
}


def verify(manifest: dict[str, Any], root: Path, *, check_git: bool = True) -> dict[str, Any]:
    for field, expected in EXPECTED.items():
        if manifest.get(field) != expected:
            raise ValueError(f"C-35 aggregate activation {field} mismatch")
    for role in ("protocol", "math", "evaluator", "unseal_gate"):
        path = root / str(manifest.get(f"{role}_path") or "")
        if not path.is_file():
            raise ValueError(f"missing aggregate {role}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != manifest.get(f"{role}_sha256"):
            raise ValueError(f"aggregate {role} hash mismatch")
    if check_git:
        commit = str(manifest.get("prepared_against_commit") or "")
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root, check=False, capture_output=True,
        )
        if result.returncode:
            raise ValueError("aggregate prepared commit is not an ancestor of HEAD")
    return {"candidate": "C-35", "aggregate_activation_integrity": "PASS", "economics": "SEALED"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="data/research/c35/aggregate_activation_manifest.json")
    args = parser.parse_args()
    manifest = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    print(json.dumps(verify(manifest, ROOT), sort_keys=True))


if __name__ == "__main__":
    main()
