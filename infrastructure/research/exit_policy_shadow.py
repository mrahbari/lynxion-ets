"""Pure, disconnected primitives for preregistered shadow exit policies."""

from __future__ import annotations

import math


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
