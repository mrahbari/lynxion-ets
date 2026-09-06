from infrastructure.risk.active_position_manager import ActivePositionManager


def _context():
    return {
        "evaluation_id": "eval-1", "position_key": "BTCUSDT:LONG:100",
        "symbol": "BTCUSDT", "is_long": True, "quantity": 1.0,
        "entry_price": 100.0, "current_price": 102.0,
        "exchange_leverage": 10.0, "roe_pct": 20.0,
        "peak_price": 102.0, "peak_roe_pct": 20.0, "state_before": {},
    }


class RejectingBroker:
    def __init__(self, errors):
        self.errors = list(errors)
        self.place_calls = 0

    def _place_conditional_order(self, **kwargs):
        error = self.errors[min(self.place_calls, len(self.errors) - 1)]
        self.place_calls += 1
        return {"success": False, "error": error}


def _responses(events):
    return [event for event in events if event["event_type"] == "STOP_REPLACE_RESPONDED"]


def test_stale_snapshot_failure_is_not_retried():
    events = []
    broker = RejectingBroker(["position not exist"])
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-1")

    assert manager._sync_sl_to_exchange(
        broker, "BTCUSDT", True, 1.0, 101.0, observation_context=_context()
    ) is False
    assert broker.place_calls == 1
    assert _responses(events)[0]["failure_classification"] == "STALE_SNAPSHOT_TERMINAL"
    assert _responses(events)[0]["retry_decision"] == "DEFER_FRESH_EVALUATION"


def test_timestamp_failure_gets_only_one_newly_signed_retry(monkeypatch):
    events = []
    broker = RejectingBroker(["timestamp is invalid", "timestamp is invalid"])
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-1")
    monkeypatch.setattr("infrastructure.risk.active_position_manager.time.sleep", lambda _: None)

    assert manager._sync_sl_to_exchange(
        broker, "BTCUSDT", True, 1.0, 101.0, observation_context=_context()
    ) is False
    assert broker.place_calls == 2
    assert [event["retry_decision"] for event in _responses(events)] == [
        "RETRY_NEW_TIMESTAMP", "DEFER_FRESH_EVALUATION",
    ]


def test_ambiguous_failure_fails_closed_without_outer_retry():
    events = []
    broker = RejectingBroker(["rejected"])
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-1")

    assert manager._sync_sl_to_exchange(
        broker, "BTCUSDT", True, 1.0, 101.0, observation_context=_context()
    ) is False
    assert broker.place_calls == 1
    assert _responses(events)[0]["failure_classification"] == "AMBIGUOUS_TERMINAL"
