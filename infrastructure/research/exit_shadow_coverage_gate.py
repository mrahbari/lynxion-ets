"""Metadata-only minimum coverage gate for prospective paired exit outcomes."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any


FROZEN_MINIMUMS = {
    "paired_positions": 100,
    "activated_positions": 30,
    "utc_weeks": 8,
    "symbols": 5,
    "long_positions": 15,
    "short_positions": 15,
}


def _utc(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("terminal time must be UTC")
    return parsed


def shadow_coverage_gate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Count only preregistered coverage metadata; never inspect economic values."""
    if not isinstance(records, list):
        raise ValueError("coverage records must be a list")
    identities: set[str] = set()
    symbols: set[str] = set()
    weeks: set[tuple[int, int]] = set()
    activated = long_count = short_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("coverage record must be an object")
        if set(record) != {
            "position_key", "symbol", "side", "terminal_time_utc", "candidate_activated",
        }:
            raise ValueError("coverage record schema mismatch")
        key = str(record["position_key"] or "")
        symbol = str(record["symbol"] or "").upper().replace("-", "").replace("/", "").replace("_", "")
        side = record["side"]
        activation = record["candidate_activated"]
        if not key or key in identities:
            raise ValueError("position identity missing or duplicated")
        if not symbol or side not in ("LONG", "SHORT") or not isinstance(activation, bool):
            raise ValueError("coverage metadata invalid")
        stamp = _utc(record["terminal_time_utc"])
        iso = stamp.isocalendar()
        identities.add(key)
        symbols.add(symbol)
        weeks.add((iso.year, iso.week))
        activated += int(activation)
        long_count += int(side == "LONG")
        short_count += int(side == "SHORT")

    counts = {
        "paired_positions": len(identities),
        "activated_positions": activated,
        "utc_weeks": len(weeks),
        "symbols": len(symbols),
        "long_positions": long_count,
        "short_positions": short_count,
    }
    gates = {name: counts[name] >= minimum for name, minimum in FROZEN_MINIMUMS.items()}
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "status": "READY_TO_OPEN_AGGREGATES" if all(gates.values()) else "COLLECTING",
        "counts": counts,
        "minimums": dict(FROZEN_MINIMUMS),
        "gates": gates,
        "membership_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }
