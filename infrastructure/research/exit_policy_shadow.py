"""Pure, disconnected primitives for preregistered shadow exit policies."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class ShadowExitState:
    last_sequence: int = -1
    stop_price: Optional[float] = None
    floor_active: bool = False
    activation_sequence: Optional[int] = None
    terminal: bool = False
    fill_price: Optional[float] = None
    fill_sequence: Optional[int] = None


def net_floor_stop_price(
    *, entry_price: float, is_long: bool, leverage: float,
    target_net_roe_pct: float, entry_fee_price_pct: float,
    expected_exit_fee_price_pct: float, remaining_slippage_price_pct: float,
) -> float:
    """Convert a net ROE floor into a fee/slippage-reserved stop price."""
    values = {
        "entry_price": entry_price,
        "leverage": leverage,
        "target_net_roe_pct": target_net_roe_pct,
        "entry_fee_price_pct": entry_fee_price_pct,
        "expected_exit_fee_price_pct": expected_exit_fee_price_pct,
        "remaining_slippage_price_pct": remaining_slippage_price_pct,
    }
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("shadow floor inputs must be finite")
    if entry_price <= 0 or leverage < 1 or target_net_roe_pct < 0:
        raise ValueError("entry, leverage, and target are invalid")
    if min(entry_fee_price_pct, expected_exit_fee_price_pct,
           remaining_slippage_price_pct) < 0:
        raise ValueError("cost reserves cannot be negative")

    target_price_return = target_net_roe_pct / (100.0 * leverage)
    cost_reserve = (
        entry_fee_price_pct
        + expected_exit_fee_price_pct
        + remaining_slippage_price_pct
    ) / 100.0
    required_price_return = target_price_return + cost_reserve
    multiplier = 1.0 + required_price_return if is_long else 1.0 - required_price_return
    if multiplier <= 0:
        raise ValueError("short shadow floor is outside the valid price domain")
    return entry_price * multiplier


def candidate_floor_activates(observed_roe_pct: float, *, trigger_roe_pct: float = 12.0) -> bool:
    if not math.isfinite(observed_roe_pct) or not math.isfinite(trigger_roe_pct):
        raise ValueError("shadow trigger inputs must be finite")
    if trigger_roe_pct < 0:
        raise ValueError("shadow trigger cannot be negative")
    return observed_roe_pct >= trigger_roe_pct


def advance_candidate_shadow(
    state: ShadowExitState, *, sequence: int, mark_price: float,
    observed_roe_pct: float, entry_price: float, is_long: bool, leverage: float,
    entry_fee_price_pct: float, expected_exit_fee_price_pct: float,
    reviewed_policy_stop_price: Optional[float] = None,
    remaining_slippage_price_pct: float = 0.10,
    trigger_roe_pct: float = 12.0, target_net_roe_pct: float = 5.0,
) -> ShadowExitState:
    """Advance one causal mark observation; new stops become active next observation."""
    if state.terminal:
        raise ValueError("cannot advance a terminal shadow position")
    if sequence <= state.last_sequence:
        raise ValueError("shadow observations must be strictly ordered")
    if not math.isfinite(mark_price) or mark_price <= 0:
        raise ValueError("mark price must be positive and finite")
    if reviewed_policy_stop_price is not None and (
        not math.isfinite(reviewed_policy_stop_price) or reviewed_policy_stop_price <= 0
    ):
        raise ValueError("reviewed policy stop must be positive and finite")

    # Only a stop established by an earlier observation can fill now. A gap uses the
    # first observed mark, never the requested stop price.
    if state.stop_price is not None:
        crossed = mark_price <= state.stop_price if is_long else mark_price >= state.stop_price
        if crossed:
            return replace(
                state, last_sequence=sequence, terminal=True,
                fill_price=mark_price, fill_sequence=sequence,
            )

    next_stop = state.stop_price
    if reviewed_policy_stop_price is not None:
        if next_stop is None:
            next_stop = reviewed_policy_stop_price
        else:
            next_stop = (
                max(next_stop, reviewed_policy_stop_price)
                if is_long else min(next_stop, reviewed_policy_stop_price)
            )

    floor_active = state.floor_active
    activation_sequence = state.activation_sequence
    if not floor_active and candidate_floor_activates(
        observed_roe_pct, trigger_roe_pct=trigger_roe_pct
    ):
        floor = net_floor_stop_price(
            entry_price=entry_price, is_long=is_long, leverage=leverage,
            target_net_roe_pct=target_net_roe_pct,
            entry_fee_price_pct=entry_fee_price_pct,
            expected_exit_fee_price_pct=expected_exit_fee_price_pct,
            remaining_slippage_price_pct=remaining_slippage_price_pct,
        )
        next_stop = floor if next_stop is None else (
            max(next_stop, floor) if is_long else min(next_stop, floor)
        )
        floor_active = True
        activation_sequence = sequence

    return replace(
        state, last_sequence=sequence, stop_price=next_stop,
        floor_active=floor_active, activation_sequence=activation_sequence,
    )
