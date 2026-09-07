from dataclasses import replace

import pytest

from infrastructure.research.exit_policy_shadow_input import BoundShadowObservation
from infrastructure.research.shadow_position_inputs import group_costed_shadow_positions


def observation(sequence=0, position_key="BTC:LONG:100", **updates):
    value = BoundShadowObservation(
        sequence=sequence, event_id=f"e{sequence}", position_key=position_key,
        symbol="BTCUSDT", is_long=True, entry_price=100.0, mark_price=101.0,
        roe_pct=10.0, leverage=10.0, reviewed_stop_price=99.0,
    )
    return replace(value, **updates)


def entry_fee(**updates):
    value = {"eligible": True, "entry_order_id": "entry-1", "entry_fee_price_pct": 0.05}
    value.update(updates)
    return value


def schedule(**updates):
    value = {
        "eligible": True, "expected_exit_fee_price_pct": 0.05,
        "snapshot_sha256": "a" * 64,
    }
    value.update(updates)
    return value


def test_groups_position_causally_and_joins_both_cost_inputs():
    rows = [observation(0), observation(1, mark_price=102.0)]
    result = group_costed_shadow_positions(
        rows, {"BTC:LONG:100": entry_fee()}, schedule()
    )
    assert len(result) == 1
    assert [row.sequence for row in result[0].observations] == [0, 1]
    assert result[0].entry_fee_price_pct == 0.05
    assert result[0].expected_exit_fee_price_pct == 0.05


def test_fee_evidence_must_exactly_cover_grouped_positions():
    with pytest.raises(ValueError, match="exactly cover"):
        group_costed_shadow_positions([observation()], {}, schedule())
    with pytest.raises(ValueError, match="exactly cover"):
        group_costed_shadow_positions(
            [observation()], {"BTC:LONG:100": entry_fee(), "extra": entry_fee()}, schedule()
        )


def test_unadmitted_or_malformed_costs_fail_closed():
    with pytest.raises(ValueError, match="schedule is not admitted"):
        group_costed_shadow_positions([observation()], {"BTC:LONG:100": entry_fee()}, schedule(eligible=False))
    with pytest.raises(ValueError, match="entry fee evidence is not admitted"):
        group_costed_shadow_positions([observation()], {"BTC:LONG:100": entry_fee(eligible=False)}, schedule())
    with pytest.raises(ValueError, match="schedule hash"):
        group_costed_shadow_positions([observation()], {"BTC:LONG:100": entry_fee()}, schedule(snapshot_sha256="bad"))


def test_sequence_and_position_identity_are_immutable():
    with pytest.raises(ValueError, match="strictly increasing"):
        group_costed_shadow_positions(
            [observation(1), observation(0)], {"BTC:LONG:100": entry_fee()}, schedule()
        )
    with pytest.raises(ValueError, match="identity changed"):
        group_costed_shadow_positions(
            [observation(0), observation(1, entry_price=101.0)],
            {"BTC:LONG:100": entry_fee()}, schedule(),
        )
