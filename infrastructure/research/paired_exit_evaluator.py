"""Disconnected causal binding from shadow observations to paired economics."""

from __future__ import annotations

from infrastructure.research.exit_policy_shadow import ShadowExitState, advance_candidate_shadow
from infrastructure.research.paired_exit_outcome import (
    PairedPositionOutcome,
    calculate_paired_position_outcome,
)
from infrastructure.research.shadow_friction_inputs import admit_funding_window
from infrastructure.research.shadow_position_inputs import TerminalLinkedShadowPosition


def evaluate_linked_shadow_pair(
    linked: TerminalLinkedShadowPosition, *, funding_snapshot: dict,
    primary_slippage_price_pct: float, stress_slippage_price_pct: float,
) -> PairedPositionOutcome:
    """Evaluate one linked position without aggregating or reading a cohort."""
    position = linked.position
    state = ShadowExitState()
    fill_time = None
    for observation in position.observations:
        state = advance_candidate_shadow(
            state, sequence=observation.sequence, mark_price=observation.mark_price,
            observed_roe_pct=observation.roe_pct, entry_price=position.entry_price,
            is_long=position.is_long, leverage=position.leverage,
            entry_fee_price_pct=position.entry_fee_price_pct,
            expected_exit_fee_price_pct=position.expected_exit_fee_price_pct,
            reviewed_policy_stop_price=observation.reviewed_stop_price,
        )
        if state.terminal:
            fill_time = observation.event_time_utc
            break

    candidate_exit_price = state.fill_price if state.terminal else None
    candidate_exit_time = fill_time if fill_time is not None else linked.fill_time_utc
    baseline_funding = admit_funding_window(
        funding_snapshot, symbol=position.symbol, is_long=position.is_long,
        entry_time_utc=position.entry_fill_time_utc, exit_time_utc=linked.fill_time_utc,
    )
    candidate_funding = admit_funding_window(
        funding_snapshot, symbol=position.symbol, is_long=position.is_long,
        entry_time_utc=position.entry_fill_time_utc, exit_time_utc=candidate_exit_time,
    )
    if baseline_funding.get("eligible") is not True or candidate_funding.get("eligible") is not True:
        raise ValueError("funding evidence is not admitted for both policy windows")
    return calculate_paired_position_outcome(
        linked, candidate_exit_price=candidate_exit_price,
        baseline_funding_return=baseline_funding["funding_price_return"],
        candidate_funding_return=candidate_funding["funding_price_return"],
        primary_slippage_price_pct=primary_slippage_price_pct,
        stress_slippage_price_pct=stress_slippage_price_pct,
    )
