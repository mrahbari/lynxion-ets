"""Structured exchange-visibility evidence for TASK-0139."""

import pytest

from tests.unit.test_task0137_exit_observer import _observation_context, _position


def test_pending_stop_verification_preserves_matching_exchange_evidence():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class Broker:
        def __init__(self):
            self.pending_calls = 0

        def get_pending_orders(self, symbol):
            self.pending_calls += 1
            return [
                {
                    "orderId": "wrong-side",
                    "type": "STOP_MARKET",
                    "side": "BUY",
                    "positionSide": "SHORT",
                    "stopPrice": "101.0",
                },
                {
                    "orderId": "visible-stop-7",
                    "type": "STOP_MARKET",
                    "side": "SELL",
                    "positionSide": "LONG",
                    "stopPrice": "101.0",
                },
            ]

    broker = Broker()
    evidence = ActivePositionManager._verify_pending_stop(
        broker, "BTC-USDT", "SELL", "LONG", 101.0
    )

    assert broker.pending_calls == 1
    assert evidence["order_id"] == "visible-stop-7"
    assert evidence["visible_stop_price"] == 101.0
    assert evidence["observed_at_utc"].endswith("+00:00")


def test_pending_stop_verification_exhaustion_preserves_existing_poll_count(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class Broker:
        def __init__(self):
            self.pending_calls = 0

        def get_pending_orders(self, symbol):
            self.pending_calls += 1
            return []

    broker = Broker()
    sleeps = []
    monkeypatch.setattr(
        "infrastructure.risk.active_position_manager.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    evidence = ActivePositionManager._verify_pending_stop(
        broker, "BTC-USDT", "SELL", "LONG", 101.0
    )

    assert evidence is None
    assert broker.pending_calls == 3
    assert sleeps == [0.2, 0.2, 0.2]


def test_visible_stop_event_is_linked_after_broker_response():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class Broker:
        def __init__(self):
            self.place_calls = 0
            self.pending_calls = 0

        def _place_conditional_order(self, **kwargs):
            self.place_calls += 1
            return {"success": True, "order_id": "visible-stop-7"}

        def get_pending_orders(self, symbol):
            self.pending_calls += 1
            return [{
                "orderId": "visible-stop-7",
                "type": "STOP_MARKET",
                "side": "SELL",
                "positionSide": "LONG",
                "stopPrice": "101.0",
            }]

    events = []
    context = _observation_context()
    broker = Broker()
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-stop")

    result = manager._sync_sl_to_exchange(
        broker, "BTCUSDT", True, 1.0, 101.0, observation_context=context
    )

    assert result is True
    assert broker.place_calls == 1
    assert broker.pending_calls == 1
    assert [event["event_type"] for event in events] == [
        "STOP_REPLACE_REQUESTED",
        "STOP_REPLACE_RESPONDED",
        "STOP_VISIBILITY_VERIFIED",
    ]
    assert events[2]["causal_event_id"] == events[1]["event_id"]
    assert events[2]["exchange_order_id"] == "visible-stop-7"
    assert events[2]["visible_stop_price"] == 101.0
    assert context["verified_visibility_event_id"] == events[2]["event_id"]


def test_invisible_accepted_stop_emits_one_failed_visibility_per_existing_attempt(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class Broker:
        def __init__(self):
            self.place_calls = 0
            self.pending_calls = 0

        def _place_conditional_order(self, **kwargs):
            self.place_calls += 1
            return {"success": True, "order_id": f"invisible-{self.place_calls}"}

        def get_pending_orders(self, symbol):
            self.pending_calls += 1
            return []

    events = []
    context = _observation_context()
    broker = Broker()
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-stop")
    monkeypatch.setattr("infrastructure.risk.active_position_manager.time.sleep", lambda _: None)

    result = manager._sync_sl_to_exchange(
        broker, "BTCUSDT", True, 1.0, 101.0, observation_context=context
    )

    failures = [event for event in events if event["event_type"] == "STOP_VISIBILITY_FAILED"]
    responses = [event for event in events if event["event_type"] == "STOP_REPLACE_RESPONDED"]
    assert result is False
    assert broker.place_calls == 3
    assert broker.pending_calls == 9
    assert len(failures) == 3
    assert [event["causal_event_id"] for event in failures] == [
        event["event_id"] for event in responses
    ]
    assert "verified_visibility_event_id" not in context
    assert not [event for event in events if event["event_type"] == "STATE_COMMITTED"]


def test_manager_emits_state_commit_only_after_existing_state_mutation():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class Broker:
        def __init__(self):
            self.place_calls = 0
            self.pending_calls = 0

        def get_all_positions(self):
            return [_position(price=102.0)]

        def _place_conditional_order(self, **kwargs):
            self.place_calls += 1
            self.stop_price = kwargs["stop_price"]
            return {"success": True, "order_id": "be-stop-1"}

        def get_pending_orders(self, symbol):
            self.pending_calls += 1
            return [{
                "orderId": "be-stop-1",
                "type": "STOP_MARKET",
                "side": "SELL",
                "positionSide": "LONG",
                "stopPrice": self.stop_price,
            }]

    events = []
    broker = Broker()
    manager = ActivePositionManager(
        be_trigger_roe=5.0,
        trail_trigger_roe=50.0,
        exit_observer=events.append,
        observer_run_id="run-commit",
    )
    manager._positions_state["BTCUSDT"] = {
        "symbol": "BTCUSDT",
        "is_long": True,
        "entry_price": 100.0,
        "quantity": 1.0,
        "peak_price": 100.0,
        "peak_roe": 0.0,
        "breakeven_active": False,
        "current_sl_price": 95.0,
        "trailing_sl_price": 0.0,
        "first_seen": 1.0,
        "initial_sl_verified": True,
    }

    actions = manager.evaluate_open_positions(broker)

    commits = [event for event in events if event["event_type"] == "STATE_COMMITTED"]
    visibility = [event for event in events if event["event_type"] == "STOP_VISIBILITY_VERIFIED"]
    assert [action["type"] for action in actions] == ["BREAKEVEN_ACTIVATED"]
    assert broker.place_calls == 1
    assert broker.pending_calls == 1
    assert len(visibility) == len(commits) == 1
    assert commits[0]["causal_event_id"] == visibility[0]["event_id"]
    assert commits[0]["causal_event_type"] == "STOP_VISIBILITY_VERIFIED"
    assert commits[0]["manager_state_after"]["breakeven_active"] is True
    assert commits[0]["manager_state_after"]["current_sl_price"] == pytest.approx(100.35)
