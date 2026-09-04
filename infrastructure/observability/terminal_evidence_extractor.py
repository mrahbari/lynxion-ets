"""Pure terminal-order evidence admission; intentionally disconnected from runtime."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Dict, Iterable, Optional


def _first(order: Dict[str, Any], names: Iterable[str]) -> Any:
    for name in names:
        value = order.get(name)
        if value not in (None, ""):
            return value
    return None


def _finite(value: Any, *, positive: bool = False) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or (positive and numeric <= 0):
        return None
    return numeric


def _exchange_time(value: Any) -> Optional[str]:
    epoch = _finite(value, positive=True)
    if epoch is None:
        return None
    if epoch >= 1_000_000_000_000:
        epoch /= 1000.0
    try:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _normalized_symbol(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.upper().replace("-", "").replace("/", "").replace("_", "").strip()


def extract_terminal_evidence(order: Dict[str, Any], identity: Dict[str, Any]) -> Dict[str, Any]:
    """Return admitted evidence without mutating inputs or filling unknown values."""
    if not isinstance(order, dict) or not isinstance(identity, dict):
        return {"eligible": False, "exclusion_reason": "inputs must be objects"}

    order_id = _first(order, ("orderId", "order_id"))
    if order_id in (None, "", "UNKNOWN"):
        return {"eligible": False, "exclusion_reason": "terminal order id unavailable"}
    side = str(_first(order, ("positionSide", "position_side")) or "").upper()
    if side not in ("LONG", "SHORT"):
        return {"eligible": False, "exclusion_reason": "explicit terminal position side unavailable"}
    order_symbol = _normalized_symbol(_first(order, ("symbol", "s")))
    identity_symbol = _normalized_symbol(identity.get("symbol"))
    if order_symbol is None or identity_symbol is None or order_symbol != identity_symbol:
        return {"eligible": False, "exclusion_reason": "terminal symbol does not match identity"}
    if side != identity.get("side"):
        return {"eligible": False, "exclusion_reason": "terminal side does not match identity"}
    if identity.get("lifecycle_state") != "OPEN":
        return {"eligible": False, "exclusion_reason": "identity is not open"}

    fill_price = _finite(_first(order, ("avgPrice", "avgFillPrice")), positive=True)
    fill_quantity = _finite(_first(order, ("executedQty", "cumQty")), positive=True)
    realized_pnl = _finite(_first(order, ("realizedProfit", "profit")))
    fees = _finite(_first(order, ("commission", "fee", "tradingFee")))
    fill_time_utc = _exchange_time(_first(order, ("updateTime", "time")))
    trigger_price = _finite(_first(order, ("stopPrice", "triggerPrice")), positive=True)
    trigger_basis_raw = _first(order, ("workingType",))
    trigger_basis = str(trigger_basis_raw) if trigger_basis_raw is not None else None
    exit_order_type_raw = _first(order, ("type", "orderType"))
    exit_order_type = str(exit_order_type_raw) if exit_order_type_raw is not None else None

    required = {
        "fill_price": fill_price,
        "fill_quantity": fill_quantity,
        "realized_pnl": realized_pnl,
        "fees": fees,
        "fill_time_utc": fill_time_utc,
    }
    missing_fields = sorted(key for key, value in required.items() if value is None)
    return {
        "eligible": True,
        "exclusion_reason": None,
        "terminal_evidence_complete": not missing_fields,
        "missing_fields": missing_fields,
        "record_id": identity.get("record_id"),
        "position_key": identity.get("position_key"),
        "observer_run_id": identity.get("observer_run_id"),
        "symbol": identity_symbol,
        "side": side,
        "entry_price": identity.get("entry_price"),
        "exchange_leverage": identity.get("exchange_leverage"),
        "terminal_order_id": str(order_id),
        "exit_order_type": exit_order_type,
        "fill_price": fill_price,
        "fill_quantity": fill_quantity,
        "realized_pnl": realized_pnl,
        "fees": fees,
        "fill_time_utc": fill_time_utc,
        "trigger_price": trigger_price,
        "trigger_basis": trigger_basis,
    }
