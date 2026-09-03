"""Runtime-disabled ActivePositionManager observation boundary for TASK-0137."""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace


def _position(*, price=100.0, leverage=Decimal("5")):
    from domain.entities import Position, PositionSide
    from domain.value_objects import Money, Symbol

    return Position(
        symbol=Symbol("BTCUSDT"),
        side=PositionSide.LONG,
        quantity=Decimal("1"),
        entry_price=Money(Decimal("100"), "USDT"),
        mark_price=price,
        timestamp=datetime.now(),
        leverage=leverage,
        isolated=True,
    )


def test_enabled_observer_records_position_and_explicit_no_action():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    events = []
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-1")
    actions = manager.evaluate_open_positions(
        SimpleNamespace(get_all_positions=lambda: [_position()])
    )

    assert actions == []
    assert [event["event_type"] for event in events] == [
        "POSITION_OBSERVED", "MANAGER_EVALUATED",
    ]
    assert events[1]["decision"] == "NO_ACTION"
    assert events[0]["exchange_leverage"] == 5.0
    assert events[0]["evaluation_id"] == events[1]["evaluation_id"]


def test_unknown_leverage_is_observed_and_never_mutates_stop(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    events = []
    synced = []
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-2")
    monkeypatch.setattr(manager, "_sync_sl_to_exchange", lambda *args: synced.append(args) or True)

    actions = manager.evaluate_open_positions(
        SimpleNamespace(get_all_positions=lambda: [_position(leverage=None)])
    )

    assert actions == [] and synced == []
    assert [event["event_type"] for event in events] == [
        "POSITION_OBSERVED", "MANAGER_EVALUATED",
    ]
    assert events[1]["decision"] == "SKIP_UNTRUSTED_LEVERAGE"
    assert events[0]["exchange_leverage"] is None


def test_observer_failure_does_not_change_protective_action(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    broker_calls = []

    def broken_observer(event):
        raise RuntimeError("observer unavailable")

    manager = ActivePositionManager(
        be_trigger_roe=5.0,
        trail_trigger_roe=50.0,
        exit_observer=broken_observer,
        observer_run_id="run-3",
    )
    monkeypatch.setattr(
        manager,
        "_sync_sl_to_exchange",
        lambda *args: broker_calls.append(args) or True,
    )

    actions = manager.evaluate_open_positions(
        SimpleNamespace(get_all_positions=lambda: [_position(price=102.0)])
    )

    assert [action["type"] for action in actions] == ["BREAKEVEN_ACTIVATED"]
    assert len(broker_calls) == 1
    assert manager.observer_failures == 2


def test_disabled_observer_emits_nothing_and_preserves_no_action_result():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    manager = ActivePositionManager()
    actions = manager.evaluate_open_positions(
        SimpleNamespace(get_all_positions=lambda: [_position()])
    )

    assert actions == []
    assert manager.observer_failures == 0
