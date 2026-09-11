#!/usr/bin/env python3
"""Verify C-35 public funding records and their successful-query coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, UNIVERSE
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from evaluate_c35_compression_release import BOUNDARY_EPOCH, UNIVERSE


def verify(funding: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> dict[str, Any]:
    if {row.get("symbol") for row in coverage} != set(UNIVERSE):
        raise ValueError("funding coverage missing frozen-universe symbol")
    coverage_keys = set()
    max_covered_ms = {}
    for row in coverage:
        if row.get("candidate") != "C-35" or row.get("status") != "COMPLETE_PUBLIC_RESPONSE":
            raise ValueError("invalid funding coverage receipt")
        symbol = row["symbol"]
        start, end = int(row["requested_start_ms"]), int(row["requested_end_ms"])
        digest = str(row.get("source_sha256") or "")
        if start > (BOUNDARY_EPOCH + 1) * 1000 or end < start or len(digest) != 64:
            raise ValueError("invalid funding coverage boundary or hash")
        key = (symbol, start, end, digest)
        if key in coverage_keys:
            raise ValueError("duplicate funding coverage receipt")
        coverage_keys.add(key)
        max_covered_ms[symbol] = max(max_covered_ms.get(symbol, 0), end)

    funding_keys = set()
    per_symbol = {symbol: 0 for symbol in UNIVERSE}
    for row in funding:
        symbol = row.get("symbol")
        timestamp = int(row.get("funding_time", -1))
        digest = str(row.get("source_sha256") or "")
        key = (symbol, timestamp)
        if symbol not in UNIVERSE or row.get("candidate") != "C-35" or timestamp <= BOUNDARY_EPOCH:
            raise ValueError("invalid funding identity or prospective boundary")
        if key in funding_keys:
            raise ValueError("duplicate funding settlement")
        funding_keys.add(key)
        matching = [receipt for receipt in coverage if
                    receipt["symbol"] == symbol and receipt["source_sha256"] == digest and
                    int(receipt["requested_start_ms"]) <= timestamp * 1000 <= int(receipt["requested_end_ms"])]
        if not matching:
            raise ValueError("funding settlement lacks source coverage")
        float(row["funding_rate"])
        per_symbol[symbol] += 1
    return {
        "candidate": "C-35",
        "funding_records": len(funding),
        "coverage_receipts": len(coverage),
        "records_per_symbol": per_symbol,
        "covered_through_ms": min(max_covered_ms.values()),
        "integrity": "PASS",
    }


def _read(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data/research/c35")
    args = parser.parse_args()
    root = Path(args.root)
    print(json.dumps(verify(_read(root / "funding.jsonl"), _read(root / "funding_coverage.jsonl")), sort_keys=True))


if __name__ == "__main__":
    main()
