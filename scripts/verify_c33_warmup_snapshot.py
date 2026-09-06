#!/usr/bin/env python3
"""Verify a committed C-33 warmup artifact without reading live source data."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

try:
    from scripts.collect_c33_liquidation_events import SYMBOLS
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from collect_c33_liquidation_events import SYMBOLS


TOP_LEVEL_FIELDS = {
    "schema_version", "candidate", "verdict", "activation_boundary", "source_sha256",
    "source_record_counts", "eligible_bucket_count", "rows",
}
ROW_FIELDS = {
    "bucket_start_ms", "bucket_end_ms", "symbol", "observed_buy_count",
    "observed_buy_notional", "observed_sell_count", "observed_sell_notional",
}
SOURCE_COUNT_FIELDS = {"heartbeat", "kline_close", "liquidation", "session"}


class InvalidC33WarmupSnapshot(ValueError):
    """A materialized C-33 warmup snapshot is invalid."""


def _nonnegative_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidC33WarmupSnapshot(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise InvalidC33WarmupSnapshot(f"{field} must be finite and non-negative")
    return result


def verify(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidC33WarmupSnapshot("snapshot is unreadable or malformed") from error
    if not isinstance(payload, dict) or set(payload) != TOP_LEVEL_FIELDS:
        raise InvalidC33WarmupSnapshot("snapshot top-level schema is invalid")
    if payload["schema_version"] != 1 or payload["candidate"] != "C-33" or payload["verdict"] != "COLLECTING":
        raise InvalidC33WarmupSnapshot("snapshot identity or verdict is invalid")
    if not isinstance(payload["activation_boundary"], int) or payload["activation_boundary"] <= 0:
        raise InvalidC33WarmupSnapshot("activation boundary is invalid")
    if not isinstance(payload["source_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", payload["source_sha256"]):
        raise InvalidC33WarmupSnapshot("source SHA-256 is invalid")
    counts = payload["source_record_counts"]
    if not isinstance(counts, dict) or set(counts) != SOURCE_COUNT_FIELDS:
        raise InvalidC33WarmupSnapshot("source record-count schema is invalid")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts.values()):
        raise InvalidC33WarmupSnapshot("source record counts must be non-negative integers")
    bucket_count = payload["eligible_bucket_count"]
    rows = payload["rows"]
    if isinstance(bucket_count, bool) or not isinstance(bucket_count, int) or bucket_count < 0:
        raise InvalidC33WarmupSnapshot("eligible bucket count is invalid")
    if not isinstance(rows, list) or len(rows) != bucket_count * len(SYMBOLS):
        raise InvalidC33WarmupSnapshot("row count does not equal bucket count times frozen universe")

    groups: dict[int, set[str]] = {}
    seen: set[tuple[int, str]] = set()
    previous_key: tuple[int, int] | None = None
    eligible_snapshots = 0
    eligible_notional = 0.0
    symbol_order = {symbol: index for index, symbol in enumerate(SYMBOLS)}
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_FIELDS:
            raise InvalidC33WarmupSnapshot("bucket-row schema is invalid")
        start, end, symbol = row["bucket_start_ms"], row["bucket_end_ms"], row["symbol"]
        if not isinstance(start, int) or start % 300_000 or end != start + 300_000:
            raise InvalidC33WarmupSnapshot("bucket boundary is invalid")
        if symbol not in SYMBOLS:
            raise InvalidC33WarmupSnapshot("row symbol is outside the frozen universe")
        key = (start, symbol)
        if key in seen:
            raise InvalidC33WarmupSnapshot("duplicate bucket-symbol row")
        seen.add(key)
        groups.setdefault(start, set()).add(symbol)
        sort_key = (start, symbol_order[symbol])
        if previous_key is not None and sort_key <= previous_key:
            raise InvalidC33WarmupSnapshot("bucket rows are not in canonical order")
        previous_key = sort_key
        for side in ("buy", "sell"):
            count = row[f"observed_{side}_count"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise InvalidC33WarmupSnapshot("observed count must be a non-negative integer")
            notional = _nonnegative_number(row[f"observed_{side}_notional"], "observed notional")
            if count == 0 and notional != 0:
                raise InvalidC33WarmupSnapshot("zero observed count must have zero notional")
            if count > 0 and notional <= 0:
                raise InvalidC33WarmupSnapshot("positive observed count must have positive notional")
            eligible_snapshots += count
            eligible_notional += notional
    if any(symbols != set(SYMBOLS) for symbols in groups.values()):
        raise InvalidC33WarmupSnapshot("bucket does not contain the exact frozen universe")
    if eligible_snapshots > counts["liquidation"]:
        raise InvalidC33WarmupSnapshot("eligible liquidation count exceeds source count")
    return {
        "candidate": "C-33",
        "verdict": "COLLECTING",
        "valid": True,
        "eligible_bucket_count": bucket_count,
        "row_count": len(rows),
        "eligible_observed_snapshot_count": eligible_snapshots,
        "eligible_observed_notional": eligible_notional,
        "source_sha256": payload["source_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.snapshot), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
