"""Runtime-disabled restart-hydration observations for TASK-0141."""

from tests.unit.test_task0137_exit_observer import _position


class HydrationBroker:
    def __init__(self, stop_price="100.36"):
        self.stop_price = stop_price
        self.pending_calls = 0

    def get_all_positions(self):
        return [_position(price=101.0)]

    def get_pending_orders(self, symbol):
        self.pending_calls += 1
        return [{
            "orderId": "restart-stop-9",
            "type": "STOP_MARKET",
            "side": "SELL",
            "positionSide": "LONG",
            "stopPrice": self.stop_price,
        }]


def test_existing_stop_hydration_emits_exact_selected_exchange_evidence():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    events = []
    broker = HydrationBroker()
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="restart-run")

    actions = manager.evaluate_open_positions(broker)

    hydrated = [event for event in events if event["event_type"] == "POSITION_HYDRATED"]
    assert actions == []
    assert broker.pending_calls == 1
    assert len(hydrated) == 1
    assert hydrated[0]["exchange_order_id"] == "restart-stop-9"
    assert hydrated[0]["recovered_stop_price"] == 100.36
    assert hydrated[0]["recovered_profit_lock"] is True
    assert hydrated[0]["hydration_source"] == "BINGX_PENDING_ORDERS"
    assert hydrated[0]["exchange_leverage"] == 5.0
    assert hydrated[0]["manager_state_after"]["breakeven_active"] is True
    assert hydrated[0]["manager_state_after"]["trailing_sl_price"] == 100.36


def test_non_positive_existing_stop_emits_no_hydration_and_adds_no_request():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    events = []
    broker = HydrationBroker(stop_price="0")
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="restart-run")

    actions = manager.evaluate_open_positions(broker)

    assert actions == []
    assert broker.pending_calls == 1
    assert not [event for event in events if event["event_type"] == "POSITION_HYDRATED"]
    assert not [event for event in events if event["event_type"] == "STOP_REPLACE_REQUESTED"]
    assert manager._positions_state["BTCUSDT"]["current_sl_price"] == 0.0


def test_hydration_observer_failure_does_not_change_state_or_broker_calls():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    def broken_observer(event):
        raise RuntimeError("observer unavailable")

    broker = HydrationBroker()
    manager = ActivePositionManager(
        exit_observer=broken_observer,
        observer_run_id="restart-run",
    )

    actions = manager.evaluate_open_positions(broker)

    assert actions == []
    assert broker.pending_calls == 1
    assert manager._positions_state["BTCUSDT"]["current_sl_price"] == 100.36
    assert manager._positions_state["BTCUSDT"]["breakeven_active"] is True
    assert manager.observer_failures == 3
