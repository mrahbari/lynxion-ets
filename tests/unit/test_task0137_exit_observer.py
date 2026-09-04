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
    assert events[0]["manager_thresholds"] == {
        "breakeven_trigger_roe_pct": 6.0,
        "trailing_trigger_roe_pct": 10.0,
        "trailing_distance_price_pct": 0.005,
        "fee_buffer_price_pct": 0.0035,
    }


def test_unknown_leverage_is_observed_and_never_mutates_stop(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    events = []
    synced = []
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-2")
    monkeypatch.setattr(
        manager,
        "_sync_sl_to_exchange",
        lambda *args, **kwargs: synced.append((args, kwargs)) or True,
    )

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
        lambda *args, **kwargs: broker_calls.append((args, kwargs)) or True,
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


def _observation_context():
    return {
        "evaluation_id": "run-stop:eval:1",
        "position_key": "BTCUSDT:LONG:100",
        "symbol": "BTCUSDT",
        "is_long": True,
        "quantity": 1.0,
        "entry_price": 100.0,
        "current_price": 102.0,
        "exchange_leverage": 5.0,
        "roe_pct": 10.0,
        "peak_price": 102.0,
        "peak_roe_pct": 10.0,
        "state_before": {},
    }


def test_each_existing_stop_attempt_emits_one_request_and_response(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class Broker:
        def __init__(self):
            self.place_calls = 0
            self.pending_calls = 0

        def _place_conditional_order(self, **kwargs):
            self.place_calls += 1
            if self.place_calls < 3:
                return {"success": False, "error": "rejected"}
            return {"success": True}

        def get_pending_orders(self, symbol):
            self.pending_calls += 1
            return [{
                "type": "STOP_MARKET",
                "side": "SELL",
                "positionSide": "LONG",
                "stopPrice": "101.0",
            }]

    events = []
    broker = Broker()
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-stop")
    monkeypatch.setattr("infrastructure.risk.active_position_manager.time.sleep", lambda _: None)

    result = manager._sync_sl_to_exchange(
        broker, "BTCUSDT", True, 1.0, 101.0,
        observation_context=_observation_context(),
    )

    requests = [event for event in events if event["event_type"] == "STOP_REPLACE_REQUESTED"]
    responses = [event for event in events if event["event_type"] == "STOP_REPLACE_RESPONDED"]
    assert result is True
    assert broker.place_calls == 3
    assert broker.pending_calls == 1
    assert [event["attempt"] for event in requests] == [1, 2, 3]
    assert [event["attempt"] for event in responses] == [1, 2, 3]
    assert [event["causal_event_id"] for event in responses] == [
        event["event_id"] for event in requests
    ]
    assert [event["accepted"] for event in responses] == [False, False, True]


def test_stop_observer_failure_does_not_generate_broker_retry():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class Broker:
        def __init__(self):
            self.place_calls = 0

        def _place_conditional_order(self, **kwargs):
            self.place_calls += 1
            return {"success": True}

        def get_pending_orders(self, symbol):
            return [{
                "type": "STOP_MARKET",
                "side": "SELL",
                "positionSide": "LONG",
                "stopPrice": "101.0",
            }]

    def broken_observer(event):
        raise RuntimeError("observer unavailable")

    broker = Broker()
    manager = ActivePositionManager(exit_observer=broken_observer, observer_run_id="run-stop")

    result = manager._sync_sl_to_exchange(
        broker, "BTCUSDT", True, 1.0, 101.0,
        observation_context=_observation_context(),
    )

    assert result is True
    assert broker.place_calls == 1
    assert manager.observer_failures == 2
