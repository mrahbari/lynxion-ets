import pytest

from infrastructure.research.exit_policy_shadow_input import BoundShadowObservation
from infrastructure.research.paired_exit_outcome import calculate_paired_position_outcome
from infrastructure.research.shadow_position_inputs import (
    CostedShadowPosition,
    TerminalLinkedShadowPosition,
)


def linked(is_long=True):
    observation = BoundShadowObservation(
        sequence=0, event_id="e0", event_time_utc="2026-09-07T00:01:00+00:00",
        run_id="r1", position_key="BTC:position", symbol="BTCUSDT",
        is_long=is_long, quantity=2.0, entry_price=100.0, mark_price=101.0,
        roe_pct=10.0, leverage=10.0, reviewed_stop_price=99.0,
    )
    position = CostedShadowPosition(
        run_id="r1", position_key="BTC:position", symbol="BTCUSDT",
        is_long=is_long, entry_price=100.0, leverage=10.0, quantity=2.0,
        entry_order_id="entry", entry_fee_price_pct=0.05,
        entry_fill_time_utc="2026-09-07T00:00:00+00:00",
        expected_exit_fee_price_pct=0.05, fee_schedule_sha256="a" * 64,
        observations=(observation,),
    )
    return TerminalLinkedShadowPosition(
        position=position, terminal_order_id="exit",
        fill_time_utc="2026-09-07T00:02:00+00:00", fill_price=101.0,
        fill_quantity=2.0, realized_pnl=2.0, signed_exit_commission=-0.101,
    )


def calculate(item, candidate_exit_price):
    return calculate_paired_position_outcome(
        item, candidate_exit_price=candidate_exit_price,
        baseline_funding_return=-0.0001, candidate_funding_return=-0.00005,
        primary_slippage_price_pct=0.10, stress_slippage_price_pct=0.20,
    )


def test_long_candidate_pair_is_cost_and_funding_adjusted():
    result = calculate(linked(), 102.0)
    assert result.baseline.net_roe_primary_pct == pytest.approx(7.9)
    assert result.candidate.net_roe_primary_pct == pytest.approx(17.95)
    assert result.paired_delta_primary_pct == pytest.approx(10.05)


def test_stress_is_exactly_one_roe_point_worse_at_10x():
    result = calculate(linked(), 102.0)
    assert result.candidate.net_roe_primary_pct - result.candidate.net_roe_stress_pct == pytest.approx(1.0)


def test_no_early_candidate_exit_uses_authoritative_terminal_fee():
    result = calculate_paired_position_outcome(
        linked(), candidate_exit_price=None,
        baseline_funding_return=-0.0001, candidate_funding_return=-0.0001,
        primary_slippage_price_pct=0.10, stress_slippage_price_pct=0.20,
    )
    assert result.candidate.exit_price == result.baseline.exit_price
    assert result.paired_delta_primary_pct == pytest.approx(0.0)

    with pytest.raises(ValueError, match="identical funding"):
        calculate(linked(), None)


def test_short_direction_is_symmetric():
    item = linked(is_long=False)
    result = calculate(item, 98.0)
    assert result.candidate.price_return == pytest.approx(0.02)


def test_non_10x_or_invalid_candidate_price_fails_closed():
    item = linked()
    object.__setattr__(item.position, "leverage", 5.0)
    with pytest.raises(ValueError, match="10x"):
        calculate(item, 102.0)
    with pytest.raises(ValueError, match="positive"):
        calculate(linked(), 0.0)
