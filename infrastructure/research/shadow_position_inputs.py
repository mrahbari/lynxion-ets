"""Group validated shadow observations and join pre-admitted cost evidence."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from infrastructure.research.exit_policy_shadow_input import BoundShadowObservation


@dataclass(frozen=True)
class CostedShadowPosition:
    position_key: str
    symbol: str
    is_long: bool
    entry_price: float
    leverage: float
    entry_order_id: str
    entry_fee_price_pct: float
    expected_exit_fee_price_pct: float
    fee_schedule_sha256: str
    observations: tuple[BoundShadowObservation, ...]


def _cost(value: Any, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{label} missing")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{label} invalid")
    return result


def group_costed_shadow_positions(
    observations: list[BoundShadowObservation],
    entry_fee_by_position: dict[str, dict[str, Any]],
    fee_schedule: dict[str, Any],
) -> list[CostedShadowPosition]:
    """Build deterministic per-position inputs without evaluating exits or PnL."""
    if not isinstance(observations, list) or not isinstance(entry_fee_by_position, dict):
        raise ValueError("shadow inputs invalid")
    if not isinstance(fee_schedule, dict) or fee_schedule.get("eligible") is not True:
        raise ValueError("exit fee schedule is not admitted")
    exit_fee = _cost(fee_schedule.get("expected_exit_fee_price_pct"), "exit fee")
    schedule_hash = str(fee_schedule.get("snapshot_sha256") or "")
    if len(schedule_hash) != 64:
        raise ValueError("fee schedule hash invalid")

    grouped: dict[str, list[BoundShadowObservation]] = {}
    prior_sequence = -1
    for observation in observations:
        if not isinstance(observation, BoundShadowObservation):
            raise ValueError("unbound shadow observation")
        if observation.sequence <= prior_sequence:
            raise ValueError("shadow observation sequence is not strictly increasing")
        prior_sequence = observation.sequence
        grouped.setdefault(observation.position_key, []).append(observation)
    if set(entry_fee_by_position) != set(grouped):
        raise ValueError("entry fee evidence does not exactly cover positions")

    result = []
    for position_key, rows in grouped.items():
        first = rows[0]
        if any(
            (row.symbol, row.is_long, row.entry_price, row.leverage)
            != (first.symbol, first.is_long, first.entry_price, first.leverage)
            for row in rows[1:]
        ):
            raise ValueError("position identity changed within shadow observations")
        entry_fee = entry_fee_by_position[position_key]
        if not isinstance(entry_fee, dict) or entry_fee.get("eligible") is not True:
            raise ValueError("entry fee evidence is not admitted")
        entry_order_id = str(entry_fee.get("entry_order_id") or "")
        if not entry_order_id:
            raise ValueError("entry order identity missing")
        result.append(CostedShadowPosition(
            position_key=position_key, symbol=first.symbol, is_long=first.is_long,
            entry_price=first.entry_price, leverage=first.leverage,
            entry_order_id=entry_order_id,
            entry_fee_price_pct=_cost(entry_fee.get("entry_fee_price_pct"), "entry fee"),
            expected_exit_fee_price_pct=exit_fee,
            fee_schedule_sha256=schedule_hash,
            observations=tuple(rows),
        ))
    return result
