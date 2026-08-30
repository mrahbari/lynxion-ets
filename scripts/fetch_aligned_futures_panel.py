#!/usr/bin/env python3
"""Fetch the frozen TASK-0094 Binance Futures panel into an isolated research store."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests


ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"
INTERVAL = "15m"
INTERVAL_MS = 15 * 60 * 1000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT")
START = "2023-01-01T00:00:00+00:00"
END = "2026-08-29T23:45:00+00:00"


def epoch_ms(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(timezone.utc).timestamp() * 1000)


def fetch_symbol(
    symbol: str,
    start_ms: int,
    end_ms: int,
    get: Callable[..., Any] = requests.get,
    pause: float = 0.12,
) -> list[list[Any]]:
    cursor = start_ms
    by_timestamp: dict[int, list[Any]] = {}
    while cursor <= end_ms:
        response = get(ENDPOINT, params={
            "symbol": symbol, "interval": INTERVAL, "startTime": cursor,
            "endTime": end_ms + INTERVAL_MS - 1, "limit": 1500,
        }, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError(f"{symbol}: malformed response")
        if not payload:
            break
        previous = None
        for row in payload:
            if not isinstance(row, list) or len(row) < 7:
                raise ValueError(f"{symbol}: malformed kline")
            opened, closed = int(row[0]), int(row[6])
            if previous is not None and opened <= previous:
                raise ValueError(f"{symbol}: non-increasing API page")
            previous = opened
            if start_ms <= opened <= end_ms and closed <= end_ms + INTERVAL_MS - 1:
                by_timestamp[opened] = row
        next_cursor = int(payload[-1][0]) + INTERVAL_MS
        if next_cursor <= cursor:
            raise ValueError(f"{symbol}: pagination did not advance")
        cursor = next_cursor
        if len(payload) < 1500:
            break
        if pause:
            time.sleep(pause)
    return [by_timestamp[key] for key in sorted(by_timestamp)]


def validate(rows: list[list[Any]], start_ms: int, end_ms: int) -> dict[str, Any]:
    timestamps = [int(row[0]) for row in rows]
    duplicate_count = len(timestamps) - len(set(timestamps))
    missing_count = sum(max(0, (right - left) // INTERVAL_MS - 1) for left, right in zip(timestamps, timestamps[1:]))
    nonpositive = 0
    ohlc_violations = 0
    out_of_range = 0
    for row in rows:
        opened = int(row[0])
        open_price, high, low, close, volume = map(float, row[1:6])
        if min(open_price, high, low, close) <= 0 or volume < 0:
            nonpositive += 1
        if high < max(open_price, close, low) or low > min(open_price, close, high):
            ohlc_violations += 1
        if not start_ms <= opened <= end_ms:
            out_of_range += 1
    return {
        "rows": len(rows), "first_timestamp": timestamps[0] // 1000 if timestamps else None,
        "last_timestamp": timestamps[-1] // 1000 if timestamps else None,
        "duplicate_count": duplicate_count, "missing_interval_count": missing_count,
        "nonpositive_count": nonpositive, "ohlc_violation_count": ohlc_violations,
        "out_of_range_count": out_of_range,
    }


def write_csv(path: Path, rows: list[list[Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for row in rows:
            writer.writerow([int(row[0]) // 1000, row[1], row[2], row[3], row[4], row[5]])
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_panel(output_dir: Path, pause: float = 0.12, start: str = START, end: str = END,
                task: str = "TASK-0094") -> dict[str, Any]:
    start_ms, end_ms = epoch_ms(start), epoch_ms(end)
    manifest: dict[str, Any] = {
        "task": task, "endpoint": ENDPOINT, "interval": INTERVAL,
        "requested_start": start, "requested_end": end, "symbols": {},
    }
    timestamp_sets = []
    for symbol in SYMBOLS:
        rows = fetch_symbol(symbol, start_ms, end_ms, pause=pause)
        checks = validate(rows, start_ms, end_ms)
        path = output_dir / f"{symbol}.csv"
        checks["sha256"] = write_csv(path, rows)
        manifest["symbols"][symbol] = checks
        timestamp_sets.append({int(row[0]) // 1000 for row in rows})
        print(f"{symbol}: {checks['rows']} rows, missing={checks['missing_interval_count']}", flush=True)
    aligned = set.intersection(*timestamp_sets) if timestamp_sets else set()
    manifest["aligned"] = {
        "rows": len(aligned), "first_timestamp": min(aligned) if aligned else None,
        "last_timestamp": max(aligned) if aligned else None,
    }
    violations = sum(
        checks[key]
        for checks in manifest["symbols"].values()
        for key in ("duplicate_count", "missing_interval_count", "nonpositive_count", "ohlc_violation_count", "out_of_range_count")
    )
    manifest["gate"] = {"integrity_violations": violations, "minimum_aligned_rows": 30_000,
                        "verdict": "KEEP" if len(aligned) >= 30_000 and violations == 0 else "REJECT"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--pause", type=float, default=0.12)
    parser.add_argument("--start", default=START)
    parser.add_argument("--end", default=END)
    parser.add_argument("--task", default="TASK-0094")
    args = parser.parse_args()
    print(json.dumps(build_panel(Path(args.output_dir), args.pause, args.start, args.end, args.task), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
