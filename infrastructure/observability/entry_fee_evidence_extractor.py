"""Pure admission of authoritative filled-entry commission evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _symbol(value: Any) -> str:
    return str(value or "").upper().replace("-", "").replace("/", "").replace("_", "")


def _epoch_ms(value: Any) -> int | None:
    numeric = _number(value)
    return int(numeric) if numeric is not None and numeric > 0 else None


def extract_entry_fee_evidence(
    orders: list[dict[str, Any]], identity: dict[str, Any]
) -> dict[str, Any]:
    """Return one uniquely linked filled entry fee or an explicit exclusion reason."""
    if not isinstance(orders, list) or not isinstance(identity, dict):
        return {"eligible": False, "exclusion_reason": "inputs must be list/object"}
    side = identity.get("side")
    symbol = _symbol(identity.get("symbol"))
    entry_price = _number(identity.get("entry_price"))
    quantity = _number(identity.get("quantity"))
    position_id = identity.get("exchange_position_id")
    first_observed = identity.get("first_observed_utc")
    try:
        observed = datetime.fromisoformat(str(first_observed).replace("Z", "+00:00"))
        if observed.tzinfo is None or observed.utcoffset() != timezone.utc.utcoffset(observed):
            raise ValueError("observation time must be UTC")
        observed_ms = int(observed.timestamp() * 1000)
    except (TypeError, ValueError):
        return {"eligible": False, "exclusion_reason": "identity observation time invalid"}
    if side not in ("LONG", "SHORT") or not symbol or not entry_price or not quantity:
        return {"eligible": False, "exclusion_reason": "identity fields incomplete"}

    matches = []
    for order in orders:
        if not isinstance(order, dict) or str(order.get("status", "")).upper() != "FILLED":
            continue
        if order.get("reduceOnly") not in (False, "false", "FALSE"):
            continue
        if _symbol(order.get("symbol")) != symbol:
            continue
        if str(order.get("positionSide", "")).upper() != side:
            continue
        order_price = _number(order.get("avgPrice"))
        order_quantity = _number(order.get("executedQty") or order.get("origQty"))
        order_ms = _epoch_ms(order.get("time"))
        if not order_price or not order_quantity or order_ms is None or order_ms > observed_ms:
            continue
        if not math.isclose(order_price, entry_price, rel_tol=1e-9, abs_tol=1e-12):
            continue
        if not math.isclose(order_quantity, quantity, rel_tol=1e-9, abs_tol=1e-12):
            continue
        order_position_id = order.get("positionID") or order.get("positionId")
        if position_id not in (None, "") and str(order_position_id) != str(position_id):
            continue
        commission = _number(order.get("commission"))
        order_id = order.get("orderId")
        if commission is None or order_id in (None, ""):
            continue
        matches.append((order, commission, order_price, order_quantity, order_ms))

    if len(matches) != 1:
        reason = "entry order unavailable" if not matches else "entry order linkage ambiguous"
        return {"eligible": False, "exclusion_reason": reason, "candidate_count": len(matches)}
    order, commission, order_price, order_quantity, order_ms = matches[0]
    return {
        "eligible": True,
        "exclusion_reason": None,
        "match_mode": "POSITION_ID" if position_id not in (None, "") else "UNIQUE_ATTRIBUTES",
        "entry_order_id": str(order["orderId"]),
        "entry_position_id": str(order.get("positionID") or order.get("positionId") or ""),
        "entry_fill_time_utc": datetime.fromtimestamp(
            order_ms / 1000.0, tz=timezone.utc
        ).isoformat(),
        "signed_entry_commission": commission,
        "entry_fee_price_pct": abs(commission) / (order_price * order_quantity) * 100.0,
    }
