import pytest

from infrastructure.research.exit_policy_shadow import (
    candidate_floor_activates,
    net_floor_stop_price,
)


def test_long_net_floor_reserves_fees_and_remaining_slippage():
    price = net_floor_stop_price(
        entry_price=100.0, is_long=True, leverage=10.0,
        target_net_roe_pct=5.0, entry_fee_price_pct=0.05,
        expected_exit_fee_price_pct=0.05, remaining_slippage_price_pct=0.10,
    )
    assert price == pytest.approx(100.7)


def test_short_net_floor_is_symmetric():
    price = net_floor_stop_price(
        entry_price=100.0, is_long=False, leverage=10.0,
        target_net_roe_pct=5.0, entry_fee_price_pct=0.05,
        expected_exit_fee_price_pct=0.05, remaining_slippage_price_pct=0.10,
    )
    assert price == pytest.approx(99.3)


def test_activation_is_inclusive_only_at_frozen_threshold():
    assert candidate_floor_activates(11.999) is False
    assert candidate_floor_activates(12.0) is True


@pytest.mark.parametrize("field", [
    "entry_fee_price_pct", "expected_exit_fee_price_pct", "remaining_slippage_price_pct",
])
def test_negative_cost_reserve_fails_closed(field):
    kwargs = dict(
        entry_price=100.0, is_long=True, leverage=10.0,
        target_net_roe_pct=5.0, entry_fee_price_pct=0.05,
        expected_exit_fee_price_pct=0.05, remaining_slippage_price_pct=0.10,
    )
    kwargs[field] = -0.01
    with pytest.raises(ValueError):
        net_floor_stop_price(**kwargs)


def test_missing_authoritative_leverage_fails_closed():
    with pytest.raises(ValueError):
        net_floor_stop_price(
            entry_price=100.0, is_long=True, leverage=0.0,
            target_net_roe_pct=5.0, entry_fee_price_pct=0.05,
            expected_exit_fee_price_pct=0.05, remaining_slippage_price_pct=0.10,
        )
