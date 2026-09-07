"""Hash-first input binding for the prospective exit-policy shadow evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any

from infrastructure.observability.exit_event_ledger import ExitEventLedger


@dataclass(frozen=True)
class BoundShadowObservation:
    sequence: int
    event_id: str
    event_time_utc: str
    run_id: str
    position_key: str
    symbol: str
    is_long: bool
    quantity: float
    entry_price: float
    mark_price: float
    roe_pct: float
    leverage: float
    reviewed_stop_price: float | None


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must be UTC")
    return parsed


def bind_shadow_observations(
    manifest: dict[str, Any], raw_events: bytes, *, expected_commit: str,
    expected_source_sha256: str,
) -> list[BoundShadowObservation]:
    """Validate one exact post-fix ledger snapshot without calculating outcomes."""
    digest = hashlib.sha256(raw_events).hexdigest()
    if digest != expected_source_sha256:
        raise ValueError("shadow source hash mismatch")
    required = {
        "schema_version", "run_id", "activation_boundary_utc", "commit",
        "historical_import_allowed",
    }
    if set(manifest) != required or manifest.get("schema_version") != 1:
        raise ValueError("shadow activation manifest is invalid")
    if manifest.get("historical_import_allowed") is not False:
        raise ValueError("historical import is forbidden")
    if manifest.get("commit") != expected_commit:
        raise ValueError("shadow activation commit mismatch")
    boundary = _utc(manifest["activation_boundary_utc"])

    known_ids: set[str] = set()
    previous: datetime | None = None
    observations: list[BoundShadowObservation] = []
    for line in raw_events.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        ExitEventLedger.validate_event(event, known_ids)
        if event["event_id"] in known_ids:
            raise ValueError("duplicate shadow event id")
        stamp = _utc(event["event_time_utc"])
        if stamp <= boundary:
            raise ValueError("shadow event is not strictly post-boundary")
        if previous is not None and stamp < previous:
            raise ValueError("shadow events are out of order")
        if event.get("run_id") != manifest["run_id"]:
            raise ValueError("foreign shadow run event")
        known_ids.add(event["event_id"])
        previous = stamp

        if event.get("event_type") != "MANAGER_EVALUATED":
            continue
        thresholds = event.get("manager_thresholds")
        if thresholds != {
            "breakeven_trigger_roe_pct": 6.0,
            "trailing_trigger_roe_pct": 10.0,
            "trailing_distance_price_pct": 0.005,
            "fee_buffer_price_pct": 0.0035,
        }:
            raise ValueError("reviewed policy thresholds differ from preregistration")
        leverage = event.get("exchange_leverage")
        if leverage != 10.0:
            raise ValueError("authoritative 10x leverage is required")
        state = event.get("manager_state_after")
        stop = state.get("current_sl_price") if isinstance(state, dict) else None
        stop = float(stop) if stop not in (None, 0, 0.0) else None
        numeric = (
            event.get("entry_price"), event.get("current_price"), event.get("roe_pct"),
            event.get("quantity"),
        )
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in numeric):
            raise ValueError("shadow observation price/ROE is invalid")
        if event["entry_price"] <= 0 or event["current_price"] <= 0 or event["quantity"] <= 0:
            raise ValueError("shadow observation price/quantity must be positive")
        if event.get("price_source") != "MARK":
            raise ValueError("shadow observation must use mark price")
        observations.append(BoundShadowObservation(
            sequence=len(observations), event_id=event["event_id"],
            event_time_utc=event["event_time_utc"], run_id=event["run_id"],
            position_key=event["position_key"], symbol=event["symbol"],
            is_long=event["side"] == "LONG", quantity=float(event["quantity"]),
            entry_price=float(event["entry_price"]),
            mark_price=float(event["current_price"]), roe_pct=float(event["roe_pct"]),
            leverage=float(leverage), reviewed_stop_price=stop,
        ))
    return observations
