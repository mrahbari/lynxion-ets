#!/usr/bin/env python3
"""Fail-closed integrity check before the first C-35 public collection."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BOUNDARY = 1789087244
EXPECTED_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"]


def verify_manifest(manifest: dict[str, Any], root: Path, *, check_git: bool = True) -> dict[str, Any]:
    if manifest.get("candidate") != "C-35" or manifest.get("boundary_epoch") != EXPECTED_BOUNDARY:
        raise ValueError("C-35 identity or boundary mismatch")
    if manifest.get("universe") != EXPECTED_UNIVERSE:
        raise ValueError("C-35 universe mismatch")
    if manifest.get("network_contract") != "PUBLIC_UNAUTHENTICATED_BINANCE_USDM_KLINES_ONLY":
        raise ValueError("C-35 network contract mismatch")
    for role in ("protocol", "collector", "evaluator"):
        path = root / str(manifest.get(f"{role}_path") or "")
        if not path.is_file():
            raise ValueError(f"missing {role} file")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != manifest.get(f"{role}_sha256"):
            raise ValueError(f"{role} hash mismatch")
    if check_git:
        commit = str(manifest.get("prepared_against_commit") or "")
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if result.returncode:
            raise ValueError("prepared commit is not an ancestor of HEAD")
    return {"candidate": "C-35", "boundary_epoch": EXPECTED_BOUNDARY, "integrity": "PASS"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="data/research/c35/activation_manifest.json")
    args = parser.parse_args()
    manifest = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    print(json.dumps(verify_manifest(manifest, ROOT), sort_keys=True))


if __name__ == "__main__":
    main()
