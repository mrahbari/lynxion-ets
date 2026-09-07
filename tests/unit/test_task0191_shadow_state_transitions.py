import pytest

from infrastructure.research.exit_policy_shadow import (
    ShadowExitState,
    advance_candidate_shadow,
)


BASE = dict(
    entry_price=100.0, is_long=True, leverage=10.0,
    entry_fee_price_pct=0.05, expected_exit_fee_price_pct=0.05,
)


def test_activation_observation_cannot_fill_new_floor():
    state = advance_candidate_shadow(
        ShadowExitState(), sequence=1, mark_price=100.6,
        observed_roe_pct=12.0, **BASE,
    )
    assert state.floor_active is True
    assert state.activation_sequence == 1
    assert state.stop_price == pytest.approx(100.7)
    assert state.terminal is False


def test_subsequent_gap_cross_fills_at_observed_mark_not_stop():
    active = advance_candidate_shadow(
        ShadowExitState(), sequence=1, mark_price=101.2,
        observed_roe_pct=12.0, **BASE,
    )
    filled = advance_candidate_shadow(
        active, sequence=2, mark_price=100.4, observed_roe_pct=4.0, **BASE,
    )
    assert filled.terminal is True
    assert filled.fill_price == 100.4
    assert filled.fill_sequence == 2


def test_reviewed_policy_stop_is_monotonic_for_long():
    state = advance_candidate_shadow(
        ShadowExitState(), sequence=1, mark_price=101.0,
        observed_roe_pct=10.0, reviewed_policy_stop_price=100.2, **BASE,
    )
    state = advance_candidate_shadow(
        state, sequence=2, mark_price=101.1,
        observed_roe_pct=11.0, reviewed_policy_stop_price=100.1, **BASE,
    )
    assert state.stop_price == 100.2


def test_short_floor_and_ratchet_are_monotonic_downward():
    short = dict(BASE, is_long=False)
    state = advance_candidate_shadow(
        ShadowExitState(), sequence=1, mark_price=98.8,
        observed_roe_pct=12.0, reviewed_policy_stop_price=99.6, **short,
    )
    assert state.stop_price == pytest.approx(99.3)
    state = advance_candidate_shadow(
        state, sequence=2, mark_price=98.7,
        observed_roe_pct=13.0, reviewed_policy_stop_price=99.4, **short,
    )
    assert state.stop_price == pytest.approx(99.3)


def test_pre_activation_reviewed_stop_can_fill():
    state = advance_candidate_shadow(
        ShadowExitState(), sequence=1, mark_price=101.0,
        observed_roe_pct=5.0, reviewed_policy_stop_price=99.0, **BASE,
    )
    filled = advance_candidate_shadow(
        state, sequence=2, mark_price=98.5, observed_roe_pct=-15.0, **BASE,
    )
    assert filled.terminal is True
    assert filled.floor_active is False


def test_out_of_order_or_post_terminal_observation_fails_closed():
    state = advance_candidate_shadow(
        ShadowExitState(), sequence=1, mark_price=101.0,
        observed_roe_pct=5.0, reviewed_policy_stop_price=99.0, **BASE,
    )
    with pytest.raises(ValueError):
        advance_candidate_shadow(
            state, sequence=1, mark_price=101.0, observed_roe_pct=5.0, **BASE,
        )
