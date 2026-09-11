#!/usr/bin/env python3
"""Verify C-35's append-only public candle evidence before signal evaluation."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, INTERVAL_SECONDS, UNIVERSE
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from evaluate_c35_compression_release import BOUNDARY_EPOCH, INTERVAL_SECONDS, UNIVERSE


def verify_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    by_symbol: dict[str, list[int]] = defaultdict(list)
    keys: set[tuple[str, int]] = set()
    warmup = prospective = 0
    for number, row in enumerate(rows, 1):
        symbol = str(row.get("symbol") or "")
        if symbol not in UNIVERSE:
            raise ValueError(f"line {number}: symbol outside frozen universe")
        open_time = int(row.get("open_time", -1))
        close_time = int(row.get("close_time", -1))
        if open_time % INTERVAL_SECONDS or close_time != open_time + INTERVAL_SECONDS - 1:
            raise ValueError(f"line {number}: invalid candle timing")
        key = (symbol, open_time)
        if key in keys:
            raise ValueError(f"line {number}: duplicate candle key")
        keys.add(key)
        expected_role = "PROSPECTIVE" if open_time > BOUNDARY_EPOCH else "WARMUP_ONLY"
        if row.get("role") != expected_role:
            raise ValueError(f"line {number}: boundary role mismatch")
        digest = str(row.get("source_sha256") or "")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"line {number}: invalid source hash")
        values = {name: float(row.get(name)) for name in ("open", "high", "low", "close", "volume")}
        if not all(math.isfinite(value) and value >= 0 for value in values.values()):
            raise ValueError(f"line {number}: invalid numeric value")
        if min(values["open"], values["close"]) < values["low"] or max(values["open"], values["close"]) > values["high"]:
            raise ValueError(f"line {number}: invalid OHLC ordering")
        by_symbol[symbol].append(open_time)
        prospective += expected_role == "PROSPECTIVE"
        warmup += expected_role == "WARMUP_ONLY"
    if set(by_symbol) != set(UNIVERSE):
        raise ValueError("ledger does not contain the complete frozen universe")
    gaps = 0
    for symbol, timestamps in by_symbol.items():
        ordered = sorted(timestamps)
        symbol_gaps = sum(current - previous != INTERVAL_SECONDS for previous, current in zip(ordered, ordered[1:]))
        if symbol_gaps:
            raise ValueError(f"{symbol}: non-contiguous candle ledger")
        gaps += symbol_gaps
    return {
        "candidate": "C-35",
        "total_records": len(keys),
        "records_per_symbol": {symbol: len(by_symbol[symbol]) for symbol in UNIVERSE},
        "warmup_records": warmup,
        "prospective_records": prospective,
        "duplicate_keys": 0,
        "gaps": gaps,
        "boundary_role_errors": 0,
        "integrity": "PASS",
    }


def verify_path(path: Path) -> dict[str, Any]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {number}: invalid JSON") from exc
    return verify_rows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default="data/research/c35/candles.jsonl")
    args = parser.parse_args()
    print(json.dumps(verify_path(Path(args.ledger)), sort_keys=True))


if __name__ == "__main__":
    main()
