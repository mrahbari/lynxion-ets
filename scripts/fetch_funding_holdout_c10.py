#!/usr/bin/env python3
"""Fetch frozen C-10 BTC/ETH Binance Futures funding history."""

from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests


ENDPOINT = "https://fapi.binance.com/fapi/v1/fundingRate"
SYMBOLS = ("BTCUSDT", "ETHUSDT")
START = "2020-01-01T00:00:00+00:00"
END = "2022-12-31T23:59:59+00:00"


def epoch_ms(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(timezone.utc).timestamp() * 1000)


def fetch_symbol(symbol: str, start_ms: int, end_ms: int, get: Callable[..., Any] = requests.get,
                 pause: float = 0.12) -> list[dict[str, Any]]:
    cursor = start_ms; rows: dict[int, dict[str, Any]] = {}
    while cursor <= end_ms:
        response = get(ENDPOINT, params={"symbol": symbol, "startTime": cursor, "endTime": end_ms, "limit": 1000}, timeout=30)
        response.raise_for_status(); payload = response.json()
        if not isinstance(payload, list):
            raise ValueError(f"{symbol}: malformed response")
        if not payload:
            break
        previous = None
        for row in payload:
            if not isinstance(row, dict) or "fundingTime" not in row or "fundingRate" not in row:
                raise ValueError(f"{symbol}: malformed funding row")
            timestamp = int(row["fundingTime"])
            if previous is not None and timestamp <= previous:
                raise ValueError(f"{symbol}: non-increasing API page")
            previous = timestamp
            if start_ms <= timestamp <= end_ms:
                rows[timestamp] = row
        next_cursor = int(payload[-1]["fundingTime"]) + 1
        if next_cursor <= cursor:
            raise ValueError(f"{symbol}: pagination did not advance")
        cursor = next_cursor
        if len(payload) < 1000:
            break
        if pause:
            time.sleep(pause)
    return [rows[key] for key in sorted(rows)]


def validate(rows: list[dict[str, Any]], start_ms: int, end_ms: int) -> dict[str, Any]:
    timestamps = [int(row["fundingTime"]) for row in rows]
    invalid_rate = sum(not (-0.1 <= float(row["fundingRate"]) <= 0.1) for row in rows)
    out_of_range = sum(not start_ms <= timestamp <= end_ms for timestamp in timestamps)
    return {"rows": len(rows), "first_timestamp": timestamps[0] // 1000 if timestamps else None,
            "last_timestamp": timestamps[-1] // 1000 if timestamps else None,
            "duplicate_count": len(timestamps) - len(set(timestamps)), "invalid_rate_count": invalid_rate,
            "out_of_range_count": out_of_range}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["timestamp", "funding_rate"])
        for row in rows:
            writer.writerow([int(row["fundingTime"]) // 1000, row["fundingRate"]])
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output_dir: Path, pause: float = 0.12) -> dict[str, Any]:
    start_ms, end_ms = epoch_ms(START), epoch_ms(END)
    manifest = {"task": "TASK-0099", "endpoint": ENDPOINT, "requested_start": START,
                "requested_end": END, "symbols": {}}
    for symbol in SYMBOLS:
        rows = fetch_symbol(symbol, start_ms, end_ms, pause=pause); checks = validate(rows, start_ms, end_ms)
        checks["sha256"] = write_csv(output_dir / f"{symbol}.csv", rows)
        manifest["symbols"][symbol] = checks
        print(f"{symbol}: {checks['rows']} funding observations", flush=True)
    violations = sum(checks[key] for checks in manifest["symbols"].values()
                     for key in ("duplicate_count", "invalid_rate_count", "out_of_range_count"))
    manifest["gate"] = {"integrity_violations": violations,
                        "verdict": "KEEP" if violations == 0 and all(item["rows"] >= 1000 for item in manifest["symbols"].values()) else "REJECT"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(Path("data/research/c10/funding")), indent=2, sort_keys=True))
