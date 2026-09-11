#!/usr/bin/env python3
"""Fail closed before C-35's first public funding query."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = 1789087244
UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"]


def verify(manifest: dict[str, Any], root: Path, *, check_git: bool = True) -> dict[str, Any]:
    if manifest.get("candidate") != "C-35" or manifest.get("boundary_epoch") != BOUNDARY:
        raise ValueError("funding activation identity or boundary mismatch")
    if manifest.get("universe") != UNIVERSE:
        raise ValueError("funding activation universe mismatch")
    if manifest.get("network_contract") != "PUBLIC_UNAUTHENTICATED_BINANCE_USDM_FUNDING_ONLY":
        raise ValueError("funding activation network contract mismatch")
    for role in ("protocol", "collector", "resolver"):
        path = root / str(manifest.get(f"{role}_path") or "")
        if not path.is_file():
            raise ValueError(f"missing funding {role}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest.get(f"{role}_sha256"):
            raise ValueError(f"funding {role} hash mismatch")
    if check_git:
        commit = str(manifest.get("prepared_against_commit") or "")
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=root,
            check=False, capture_output=True,
        )
        if result.returncode:
            raise ValueError("funding prepared commit is not an ancestor of HEAD")
    return {"candidate": "C-35", "boundary_epoch": BOUNDARY, "funding_integrity": "PASS"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="data/research/c35/funding_activation_manifest.json")
    args = parser.parse_args()
    manifest = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    print(json.dumps(verify(manifest, ROOT), sort_keys=True))


if __name__ == "__main__":
    main()
