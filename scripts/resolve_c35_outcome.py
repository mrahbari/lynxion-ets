#!/usr/bin/env python3
"""Resolve one C-35 virtual outcome from complete public evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any


INTERVAL_SECONDS = 900


def resolve_outcome(
    signal: dict[str, Any],
    candles: list[dict[str, Any]],
    funding: list[dict[str, Any]],
    *,
    funding_coverage_complete: bool,
) -> dict[str, Any]:
    if signal.get("candidate") != "C-35" or signal.get("side") not in {"LONG", "SHORT"}:
        raise ValueError("invalid C-35 signal")
    entry_time = int(signal["entry_open_time"])
    exit_time = int(signal["exit_open_time"])
    if exit_time != entry_time + 8 * INTERVAL_SECONDS:
        raise ValueError("invalid C-35 outcome horizon")
    relevant = sorted(
        (row for row in candles if entry_time <= int(row.get("open_time", -1)) <= exit_time),
        key=lambda row: int(row["open_time"]),
    )
    expected = list(range(entry_time, exit_time + INTERVAL_SECONDS, INTERVAL_SECONDS))
    if [int(row["open_time"]) for row in relevant] != expected:
        raise ValueError("incomplete C-35 entry-to-exit candle interval")
    entry_price = float(relevant[0]["open"])
    exit_price = float(relevant[-1]["open"])
    if entry_price <= 0 or exit_price <= 0:
        raise ValueError("invalid C-35 fill price")
    if not funding_coverage_complete:
        raise ValueError("incomplete C-35 funding coverage")
    settlements = sorted(
        (row for row in funding if entry_time < int(row.get("funding_time", -1)) <= exit_time),
        key=lambda row: int(row["funding_time"]),
    )
    rates = [float(row["funding_rate"]) for row in settlements]
    gross_return = exit_price / entry_price - 1 if signal["side"] == "LONG" else entry_price / exit_price - 1
    funding_return = -sum(rates) if signal["side"] == "LONG" else sum(rates)
    evidence = {"candles": relevant, "funding": settlements}
    evidence_hash = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "kind": "OUTCOME",
        "candidate": "C-35",
        "signal_key": signal["signal_key"],
        "symbol": signal["symbol"],
        "side": signal["side"],
        "entry_open_time": entry_time,
        "exit_open_time": exit_time,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "gross_return": gross_return,
        "funding_return": funding_return,
        "net_return_primary_0_30pct": gross_return + funding_return - 0.003,
        "net_return_sensitivity_0_20pct": gross_return + funding_return - 0.002,
        "net_return_stress_0_50pct": gross_return + funding_return - 0.005,
        "funding_settlement_count": len(settlements),
        "evidence_sha256": evidence_hash,
        "status": "COMPLETE",
    }
