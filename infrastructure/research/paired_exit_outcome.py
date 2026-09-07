"""Pure per-position paired exit economics; no aggregation or cohort access."""

from __future__ import annotations

from dataclasses import dataclass
import math

from infrastructure.research.shadow_position_inputs import TerminalLinkedShadowPosition


@dataclass(frozen=True)
class PolicyEconomics:
    exit_price: float
    price_return: float
    funding_return: float
    net_roe_primary_pct: float
    net_roe_stress_pct: float


@dataclass(frozen=True)
class PairedPositionOutcome:
    position_key: str
    baseline: PolicyEconomics
    candidate: PolicyEconomics
    paired_delta_primary_pct: float
    paired_delta_stress_pct: float


def _finite(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _policy_economics(
    *, entry_price: float, exit_price: float, is_long: bool, leverage: float,
    entry_fee_price_pct: float, exit_fee_price_pct: float, funding_return: float,
    primary_slippage_price_pct: float, stress_slippage_price_pct: float,
) -> PolicyEconomics:
    values = {
        "entry price": entry_price, "exit price": exit_price, "leverage": leverage,
        "entry fee": entry_fee_price_pct, "exit fee": exit_fee_price_pct,
        "funding": funding_return, "primary slippage": primary_slippage_price_pct,
        "stress slippage": stress_slippage_price_pct,
    }
    parsed = {name: _finite(value, name) for name, value in values.items()}
    if parsed["entry price"] <= 0 or parsed["exit price"] <= 0 or parsed["leverage"] != 10.0:
        raise ValueError("authoritative positive prices and 10x leverage are required")
    if min(parsed["entry fee"], parsed["exit fee"], parsed["primary slippage"], parsed["stress slippage"]) < 0:
        raise ValueError("fees and slippage cannot be negative")
    direction = 1.0 if is_long else -1.0
    price_return = direction * (exit_price / entry_price - 1.0)
    fixed_cost = (entry_fee_price_pct + exit_fee_price_pct) / 100.0
    primary_net = price_return + funding_return - fixed_cost - primary_slippage_price_pct / 100.0
    stress_net = price_return + funding_return - fixed_cost - stress_slippage_price_pct / 100.0
    return PolicyEconomics(
        exit_price=exit_price, price_return=price_return, funding_return=funding_return,
        net_roe_primary_pct=primary_net * leverage * 100.0,
        net_roe_stress_pct=stress_net * leverage * 100.0,
    )


def calculate_paired_position_outcome(
    linked: TerminalLinkedShadowPosition, *, candidate_exit_price: float | None,
    baseline_funding_return: float, candidate_funding_return: float,
    primary_slippage_price_pct: float, stress_slippage_price_pct: float,
) -> PairedPositionOutcome:
    """Calculate one synthetic pair after all linkage inputs are admitted."""
    position = linked.position
    baseline_exit_fee_pct = abs(linked.signed_exit_commission) / (
        linked.fill_price * linked.fill_quantity
    ) * 100.0
    baseline = _policy_economics(
        entry_price=position.entry_price, exit_price=linked.fill_price,
        is_long=position.is_long, leverage=position.leverage,
        entry_fee_price_pct=position.entry_fee_price_pct,
        exit_fee_price_pct=baseline_exit_fee_pct,
        funding_return=baseline_funding_return,
        primary_slippage_price_pct=primary_slippage_price_pct,
        stress_slippage_price_pct=stress_slippage_price_pct,
    )
    candidate_early = candidate_exit_price is not None
    if not candidate_early and not math.isclose(
        candidate_funding_return, baseline_funding_return, rel_tol=0.0, abs_tol=1e-15
    ):
        raise ValueError("shared terminal requires identical funding attribution")
    candidate = _policy_economics(
        entry_price=position.entry_price,
        exit_price=float(candidate_exit_price) if candidate_early else linked.fill_price,
        is_long=position.is_long, leverage=position.leverage,
        entry_fee_price_pct=position.entry_fee_price_pct,
        exit_fee_price_pct=(
            position.expected_exit_fee_price_pct if candidate_early else baseline_exit_fee_pct
        ),
        funding_return=candidate_funding_return,
        primary_slippage_price_pct=primary_slippage_price_pct,
        stress_slippage_price_pct=stress_slippage_price_pct,
    )
    return PairedPositionOutcome(
        position_key=position.position_key, baseline=baseline, candidate=candidate,
        paired_delta_primary_pct=candidate.net_roe_primary_pct - baseline.net_roe_primary_pct,
        paired_delta_stress_pct=candidate.net_roe_stress_pct - baseline.net_roe_stress_pct,
    )
