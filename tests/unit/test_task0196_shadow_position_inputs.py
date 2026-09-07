from dataclasses import replace

import pytest

from infrastructure.research.exit_policy_shadow_input import BoundShadowObservation
from infrastructure.research.shadow_position_inputs import (
    group_costed_shadow_positions,
    join_terminal_evidence,
)


def observation(sequence=0, position_key="BTC:LONG:100", **updates):
    value = BoundShadowObservation(
        sequence=sequence, event_id=f"e{sequence}",
        event_time_utc=f"2026-09-07T00:0{sequence + 1}:00+00:00", run_id="run-1",
        position_key=position_key, symbol="BTCUSDT", is_long=True, quantity=2.0,
        entry_price=100.0, mark_price=101.0,
        roe_pct=10.0, leverage=10.0, reviewed_stop_price=99.0,
    )
    return replace(value, **updates)


def entry_fee(**updates):
    value = {
        "eligible": True, "entry_order_id": "entry-1",
        "entry_fill_time_utc": "2026-09-07T00:00:00+00:00",
        "entry_fee_price_pct": 0.05,
    }
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


def terminal(**updates):
    value = {
        "eligible": True, "terminal_evidence_complete": True,
        "position_key": "BTC:LONG:100", "observer_run_id": "run-1",
        "symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0,
        "exchange_leverage": 10.0, "terminal_order_id": "exit-1",
        "fill_time_utc": "2026-09-07T00:03:00+00:00", "fill_price": 101.0,
        "fill_quantity": 2.0, "realized_pnl": 2.0, "fees": -0.1,
    }
    value.update(updates)
    return value


def costed(rows=None):
    rows = rows or [observation(0), observation(1, mark_price=102.0)]
    return group_costed_shadow_positions(rows, {"BTC:LONG:100": entry_fee()}, schedule())


def test_complete_terminal_links_without_calculating_returns():
    result = join_terminal_evidence(costed(), {"BTC:LONG:100": terminal()})
    assert result[0].terminal_order_id == "exit-1"
    assert result[0].signed_exit_commission == -0.1


def test_partial_or_noncausal_terminal_fails_closed():
    with pytest.raises(ValueError, match="full position"):
        join_terminal_evidence(costed(), {"BTC:LONG:100": terminal(fill_quantity=1.0)})
    with pytest.raises(ValueError, match="strictly after"):
        join_terminal_evidence(
            costed(), {"BTC:LONG:100": terminal(fill_time_utc="2026-09-07T00:02:00+00:00")}
        )


def test_incomplete_or_cross_run_terminal_fails_closed():
    with pytest.raises(ValueError, match="complete and admitted"):
        join_terminal_evidence(
            costed(), {"BTC:LONG:100": terminal(terminal_evidence_complete=False)}
        )
    with pytest.raises(ValueError, match="identity"):
        join_terminal_evidence(
            costed(), {"BTC:LONG:100": terminal(observer_run_id="other")}
        )
    with pytest.raises(ValueError, match="identity changed"):
        group_costed_shadow_positions(
            [observation(0), observation(1, entry_price=101.0)],
            {"BTC:LONG:100": entry_fee()}, schedule(),
        )
