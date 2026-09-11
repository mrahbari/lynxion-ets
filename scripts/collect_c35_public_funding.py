#!/usr/bin/env python3
"""Append public Binance USD-M funding evidence and query coverage for C-35."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, UNIVERSE
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from evaluate_c35_compression_release import BOUNDARY_EPOCH, UNIVERSE


PUBLIC_ENDPOINT = "https://fapi.binance.com/fapi/v1/fundingRate"


def parse_page(symbol: str, body: bytes, *, requested_start_ms: int, requested_end_ms: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if symbol not in UNIVERSE:
        raise ValueError("symbol outside frozen C-35 universe")
    digest = hashlib.sha256(body).hexdigest()
    payload = json.loads(body)
    if not isinstance(payload, list):
        raise ValueError("public funding payload must be a list")
    records = []
    previous = None
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("malformed public funding row")
        funding_ms = int(row.get("fundingTime", -1))
        rate = str(row.get("fundingRate") or "")
        if not (requested_start_ms <= funding_ms <= requested_end_ms) or not rate:
            raise ValueError("funding row outside request or missing rate")
        if previous is not None and funding_ms <= previous:
            raise ValueError("funding rows are not strictly increasing")
        previous = funding_ms
        records.append({
            "candidate": "C-35",
            "symbol": symbol,
            "funding_time": funding_ms // 1000,
            "funding_rate": rate,
            "source_sha256": digest,
        })
    coverage = {
        "candidate": "C-35",
        "symbol": symbol,
        "requested_start_ms": requested_start_ms,
        "requested_end_ms": requested_end_ms,
        "source_sha256": digest,
        "response_records": len(records),
        "status": "COMPLETE_PUBLIC_RESPONSE",
    }
    return records, coverage


def _read_keys(path: Path, fields: tuple[str, ...]) -> set[tuple[Any, ...]]:
    keys = set()
    if not path.exists():
        return keys
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
            keys.add(tuple(row[field] for field in fields))
        except (json.JSONDecodeError, KeyError) as exc:
            raise ValueError(f"invalid existing funding evidence line {number}") from exc
    return keys


def _append(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as target:
        for row in rows:
            target.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        target.flush()
        os.fsync(target.fileno())


def append_page(root: Path, symbol: str, body: bytes, *, requested_start_ms: int, requested_end_ms: int) -> dict[str, int]:
    records, coverage = parse_page(
        symbol, body, requested_start_ms=requested_start_ms, requested_end_ms=requested_end_ms
    )
    funding_path = root / "funding.jsonl"
    coverage_path = root / "funding_coverage.jsonl"
    funding_keys = _read_keys(funding_path, ("symbol", "funding_time"))
    coverage_keys = _read_keys(coverage_path, ("symbol", "requested_start_ms", "requested_end_ms", "source_sha256"))
    new_records = [row for row in records if (row["symbol"], row["funding_time"]) not in funding_keys]
    coverage_key = (symbol, requested_start_ms, requested_end_ms, coverage["source_sha256"])
    new_coverage = [] if coverage_key in coverage_keys else [coverage]
    _append(funding_path, new_records)
    _append(coverage_path, new_coverage)
    return {"funding_records": len(new_records), "coverage_receipts": len(new_coverage)}


def fetch_page(symbol: str, start_ms: int, end_ms: int, *, timeout: float = 20.0) -> bytes:
    query = urllib.parse.urlencode({"symbol": symbol, "startTime": start_ms, "endTime": end_ms, "limit": 1000})
    request = urllib.request.Request(f"{PUBLIC_ENDPOINT}?{query}", method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def collect(root: Path, *, now_ms: int) -> dict[str, dict[str, int]]:
    start_ms = (BOUNDARY_EPOCH + 1) * 1000
    output = {}
    for symbol in UNIVERSE:
        body = fetch_page(symbol, start_ms, now_ms)
        output[symbol] = append_page(
            root, symbol, body, requested_start_ms=start_ms, requested_end_ms=now_ms
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data/research/c35")
    parser.add_argument("--now-ms", type=int)
    args = parser.parse_args()
    now_ms = args.now_ms if args.now_ms is not None else int(time.time() * 1000)
    print(json.dumps(collect(Path(args.root), now_ms=now_ms), sort_keys=True))


if __name__ == "__main__":
    main()
