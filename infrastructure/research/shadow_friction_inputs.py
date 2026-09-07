"""Pure funding and slippage admission for the preregistered exit shadow."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any


def _utc(value: Any, label: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{label} must be UTC")
    return parsed


def _finite(value: Any, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{label} missing")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} invalid")
    return result


def admit_funding_window(
    snapshot: dict[str, Any], *, symbol: str, is_long: bool,
    entry_time_utc: str, exit_time_utc: str,
) -> dict[str, Any]:
    """Admit complete settlement coverage and side-signed funding price return."""
    try:
        entry = _utc(entry_time_utc, "entry time")
        exit_time = _utc(exit_time_utc, "exit time")
        coverage_start = _utc(snapshot.get("coverage_start_utc"), "coverage start")
        coverage_end = _utc(snapshot.get("coverage_end_utc"), "coverage end")
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        return {"eligible": False, "exclusion_reason": str(exc)}
    if exit_time <= entry:
        return {"eligible": False, "exclusion_reason": "exit must follow entry"}
    normalized = symbol.upper().replace("-", "").replace("/", "").replace("_", "")
    actual_symbol = str(snapshot.get("symbol") or "").upper().replace("-", "").replace("/", "").replace("_", "")
    if actual_symbol != normalized:
        return {"eligible": False, "exclusion_reason": "funding symbol mismatch"}
    if str(snapshot.get("exchange", "")).upper() != "BINGX" or str(snapshot.get("market", "")).upper() != "PERPETUAL":
        return {"eligible": False, "exclusion_reason": "funding venue/market mismatch"}
    if not snapshot.get("source"):
        return {"eligible": False, "exclusion_reason": "funding provenance incomplete"}
    if coverage_start > entry or coverage_end < exit_time:
        return {"eligible": False, "exclusion_reason": "funding coverage is incomplete"}
    settlements = snapshot.get("settlements")
    if not isinstance(settlements, list):
        return {"eligible": False, "exclusion_reason": "funding settlements missing"}

    total = 0.0
    admitted = 0
    seen: set[str] = set()
    try:
        for row in settlements:
            settlement_id = str(row.get("settlement_id") or "")
            if not settlement_id or settlement_id in seen:
                raise ValueError("funding settlement identity missing or duplicated")
            seen.add(settlement_id)
            stamp = _utc(row.get("timestamp_utc"), "funding settlement time")
            rate = _finite(row.get("funding_rate"), "funding rate")
            if entry < stamp < exit_time:
                total += -rate if is_long else rate
                admitted += 1
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        return {"eligible": False, "exclusion_reason": str(exc)}
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "eligible": True,
        "exclusion_reason": None,
        "funding_price_return": total,
        "settlement_count": admitted,
        "snapshot_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def frozen_slippage_contract(
    *, primary_round_trip_price_pct: float,
    stress_round_trip_price_pct: float,
    candidate_remaining_exit_price_pct: float,
) -> dict[str, float]:
    """Require the exact preregistered primary, stress, and floor reserves."""
    values = {
        "primary_round_trip_price_pct": primary_round_trip_price_pct,
        "stress_round_trip_price_pct": stress_round_trip_price_pct,
        "candidate_remaining_exit_price_pct": candidate_remaining_exit_price_pct,
    }
    if any(not math.isfinite(value) for value in values.values()):
        raise ValueError("slippage inputs must be finite")
    if values != {
        "primary_round_trip_price_pct": 0.10,
        "stress_round_trip_price_pct": 0.20,
        "candidate_remaining_exit_price_pct": 0.10,
    }:
        raise ValueError("slippage inputs differ from preregistration")
    return values
