#!/usr/bin/env python3
"""Append public Binance USD-M candles for the preregistered C-35 cohort."""

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
    from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, INTERVAL_SECONDS, UNIVERSE
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from evaluate_c35_compression_release import BOUNDARY_EPOCH, INTERVAL_SECONDS, UNIVERSE


PUBLIC_ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"
WARMUP_BARS = 2898


def parse_public_page(symbol: str, body: bytes, *, now_ms: int) -> list[dict[str, Any]]:
    digest = hashlib.sha256(body).hexdigest()
    payload = json.loads(body)
    if not isinstance(payload, list):
        raise ValueError("public kline payload must be a list")
    records = []
    for row in payload:
        if not isinstance(row, list) or len(row) < 7:
            raise ValueError("malformed public kline row")
        open_ms, close_ms = int(row[0]), int(row[6])
        if open_ms % (INTERVAL_SECONDS * 1000):
            raise ValueError("misaligned 15-minute candle")
        if close_ms >= now_ms:
            continue
        values = [str(row[index]) for index in (1, 2, 3, 4, 5)]
        if any(not value or value.lower() in {"nan", "inf", "-inf"} for value in values):
            raise ValueError("invalid public kline value")
        records.append({
            "candidate": "C-35",
            "symbol": symbol,
            "open_time": open_ms // 1000,
            "close_time": close_ms // 1000,
            "open": values[0],
            "high": values[1],
            "low": values[2],
            "close": values[3],
            "volume": values[4],
            "source_sha256": digest,
            "role": "PROSPECTIVE" if open_ms // 1000 > BOUNDARY_EPOCH else "WARMUP_ONLY",
        })
    return records


def _existing_keys(path: Path) -> set[tuple[str, int]]:
    keys = set()
    if not path.exists():
        return keys
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
            keys.add((str(row["symbol"]), int(row["open_time"])))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid existing C-35 ledger line {number}") from exc
    return keys


def append_page(path: Path, symbol: str, body: bytes, *, now_ms: int) -> int:
    if symbol not in UNIVERSE:
        raise ValueError("symbol outside frozen C-35 universe")
    existing = _existing_keys(path)
    records = [
        row for row in parse_public_page(symbol, body, now_ms=now_ms)
        if (row["symbol"], row["open_time"]) not in existing
    ]
    if not records:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as target:
        for row in records:
            target.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        target.flush()
        os.fsync(target.fileno())
    return len(records)


def fetch_page(symbol: str, start_ms: int, *, timeout: float = 20.0) -> bytes:
    query = urllib.parse.urlencode({
        "symbol": symbol,
        "interval": "15m",
        "limit": 1500,
        "startTime": start_ms,
    })
    request = urllib.request.Request(f"{PUBLIC_ENDPOINT}?{query}", method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def collect(root: Path, *, now_ms: int) -> dict[str, int]:
    ledger = root / "candles.jsonl"
    start_ms = (BOUNDARY_EPOCH - WARMUP_BARS * INTERVAL_SECONDS) * 1000
    counts = {symbol: 0 for symbol in UNIVERSE}
    for symbol in UNIVERSE:
        cursor = start_ms
        while cursor < now_ms:
            body = fetch_page(symbol, cursor)
            rows = parse_public_page(symbol, body, now_ms=now_ms)
            counts[symbol] += append_page(ledger, symbol, body, now_ms=now_ms)
            if not rows:
                break
            next_cursor = (rows[-1]["open_time"] + INTERVAL_SECONDS) * 1000
            if next_cursor <= cursor or len(rows) < 1500:
                break
            cursor = next_cursor
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data/research/c35")
    parser.add_argument("--now-ms", type=int, help="Test-only observation cutoff")
    args = parser.parse_args()
    now_ms = args.now_ms if args.now_ms is not None else int(time.time() * 1000)
    print(json.dumps(collect(Path(args.root), now_ms=now_ms), sort_keys=True))


if __name__ == "__main__":
    main()
