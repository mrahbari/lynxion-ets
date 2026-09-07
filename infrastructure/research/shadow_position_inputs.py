"""Group validated shadow observations and join pre-admitted cost evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any

from infrastructure.research.exit_policy_shadow_input import BoundShadowObservation


@dataclass(frozen=True)
class CostedShadowPosition:
    run_id: str
    position_key: str
    symbol: str
    is_long: bool
    entry_price: float
    leverage: float
    quantity: float
    entry_order_id: str
    entry_fee_price_pct: float
    expected_exit_fee_price_pct: float
    fee_schedule_sha256: str
    observations: tuple[BoundShadowObservation, ...]


@dataclass(frozen=True)
class TerminalLinkedShadowPosition:
    position: CostedShadowPosition
    terminal_order_id: str
    fill_time_utc: str
    fill_price: float
    fill_quantity: float
    realized_pnl: float
    signed_exit_commission: float


def _cost(value: Any, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{label} missing")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{label} invalid")
    return result


def _finite(value: Any, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{label} missing")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} invalid")
    return result


def _utc(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("terminal time must be UTC")
    return parsed


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
            (row.run_id, row.symbol, row.is_long, row.entry_price, row.leverage, row.quantity)
            != (first.run_id, first.symbol, first.is_long, first.entry_price, first.leverage, first.quantity)
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
            run_id=first.run_id, position_key=position_key, symbol=first.symbol,
            is_long=first.is_long, entry_price=first.entry_price,
            leverage=first.leverage, quantity=first.quantity,
            entry_order_id=entry_order_id,
            entry_fee_price_pct=_cost(entry_fee.get("entry_fee_price_pct"), "entry fee"),
            expected_exit_fee_price_pct=exit_fee,
            fee_schedule_sha256=schedule_hash,
            observations=tuple(rows),
        ))
    return result


def join_terminal_evidence(
    positions: list[CostedShadowPosition],
    terminal_by_position: dict[str, dict[str, Any]],
) -> list[TerminalLinkedShadowPosition]:
    """Link complete authoritative terminal evidence without calculating returns."""
    if set(terminal_by_position) != {position.position_key for position in positions}:
        raise ValueError("terminal evidence does not exactly cover positions")
    linked = []
    terminal_ids: set[str] = set()
    for position in positions:
        terminal = terminal_by_position[position.position_key]
        if terminal.get("eligible") is not True or terminal.get("terminal_evidence_complete") is not True:
            raise ValueError("terminal evidence is not complete and admitted")
        expected = (
            position.position_key, position.run_id, position.symbol,
            "LONG" if position.is_long else "SHORT", position.entry_price, position.leverage,
        )
        actual = (
            terminal.get("position_key"), terminal.get("observer_run_id"), terminal.get("symbol"),
            terminal.get("side"), terminal.get("entry_price"), terminal.get("exchange_leverage"),
        )
        if actual != expected:
            raise ValueError("terminal identity does not match shadow position")
        fill_quantity = _cost(terminal.get("fill_quantity"), "terminal fill quantity")
        if fill_quantity == 0:
            raise ValueError("terminal fill quantity invalid")
        if not math.isclose(fill_quantity, position.quantity, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError("terminal fill does not cover full position quantity")
        fill_time = _utc(terminal.get("fill_time_utc"))
        last_observation = _utc(position.observations[-1].event_time_utc)
        if fill_time <= last_observation:
            raise ValueError("terminal fill is not strictly after last observation")
        terminal_id = str(terminal.get("terminal_order_id") or "")
        if not terminal_id or terminal_id in terminal_ids:
            raise ValueError("terminal order identity is missing or reused")
        terminal_ids.add(terminal_id)
        linked.append(TerminalLinkedShadowPosition(
            position=position, terminal_order_id=terminal_id,
            fill_time_utc=terminal["fill_time_utc"],
            fill_price=_cost(terminal.get("fill_price"), "terminal fill price"),
            fill_quantity=fill_quantity,
            realized_pnl=_finite(terminal.get("realized_pnl"), "terminal realized PnL"),
            signed_exit_commission=_finite(terminal.get("fees"), "terminal commission"),
        ))
    return linked
