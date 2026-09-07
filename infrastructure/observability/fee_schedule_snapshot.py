"""Pure fail-closed admission for pre-activation broker fee schedules."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any


def _utc(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must be UTC")
    return parsed


def _nonnegative_number(value: Any) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError("fee rate missing")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("fee rate must be finite and nonnegative")
    return result


def admit_exit_fee_schedule(
    snapshot: dict[str, Any], *, activation_utc: str, exchange: str, market: str
) -> dict[str, Any]:
    """Admit one immutable, contemporaneous taker-fee schedule snapshot."""
    if not isinstance(snapshot, dict):
        return {"eligible": False, "exclusion_reason": "snapshot must be an object"}
    try:
        activation = _utc(activation_utc)
        captured = _utc(snapshot.get("captured_at_utc"))
        effective = _utc(snapshot.get("effective_at_utc"))
        taker_rate = _nonnegative_number(snapshot.get("taker_fee_rate"))
    except (TypeError, ValueError, OverflowError) as exc:
        return {"eligible": False, "exclusion_reason": str(exc)}

    required = {
        "exchange": exchange.upper(),
        "market": market.upper(),
        "account_tier": snapshot.get("account_tier"),
        "source": snapshot.get("source"),
    }
    if str(snapshot.get("exchange", "")).upper() != required["exchange"]:
        return {"eligible": False, "exclusion_reason": "exchange mismatch"}
    if str(snapshot.get("market", "")).upper() != required["market"]:
        return {"eligible": False, "exclusion_reason": "market mismatch"}
    if not required["account_tier"] or not required["source"]:
        return {"eligible": False, "exclusion_reason": "schedule provenance incomplete"}
    if captured > activation or effective > activation:
        return {"eligible": False, "exclusion_reason": "schedule is post-activation"}
    if captured < effective:
        return {"eligible": False, "exclusion_reason": "schedule captured before effective time"}

    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "eligible": True,
        "exclusion_reason": None,
        "expected_exit_fee_price_pct": taker_rate * 100.0,
        "account_tier": str(required["account_tier"]),
        "source": str(required["source"]),
        "snapshot_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
