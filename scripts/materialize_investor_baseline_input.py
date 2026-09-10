#!/usr/bin/env python3
"""Recover the hash-bound investor baseline input from an append-only journal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "data/research/investor_release/cost_adjusted_baseline_v1.json"
MANIFEST = ROOT / "data/research/investor_release/cost_adjusted_baseline_v1_manifest.json"
JOURNAL = ROOT / "data/trade_journal.csv"
SNAPSHOT = ROOT / "data/research/investor_release/trade_journal_baseline_v1.csv"


def extract_verified_prefix(source: bytes, source_rows: int, expected_sha256: str) -> bytes:
    lines = source.splitlines(keepends=True)
    if len(lines) < source_rows + 1:
        raise ValueError("journal has fewer rows than the frozen artifact")
    prefix = b"".join(lines[: source_rows + 1])
    digest = hashlib.sha256(prefix).hexdigest()
    if digest != expected_sha256:
        raise ValueError(f"frozen journal prefix hash mismatch: {digest}")
    return prefix


def main() -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source_rows = int(artifact["data_quality"]["source_rows"])
    expected = str(manifest["input_sha256"])
    prefix = extract_verified_prefix(JOURNAL.read_bytes(), source_rows, expected)
    if SNAPSHOT.exists() and SNAPSHOT.read_bytes() != prefix:
        raise ValueError("existing frozen snapshot differs from verified prefix")
    SNAPSHOT.write_bytes(prefix)
    print(json.dumps({
        "snapshot": str(SNAPSHOT.relative_to(ROOT)),
        "source_rows": source_rows,
        "sha256": expected,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
