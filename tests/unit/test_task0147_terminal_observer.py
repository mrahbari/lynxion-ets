from copy import deepcopy
from unittest.mock import MagicMock

from infrastructure.execution.broker_reconciliation import BrokerReconciliationService


def _identity():
    return {
        "schema_version": 1, "record_id": "record-1", "position_key": "BTCUSDT:LONG:100",
        "symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "quantity": 2.0,
        "exchange_leverage": 5.0, "first_observed_utc": "2026-09-04T19:00:00+00:00",
        "last_observed_utc": "2026-09-04T19:00:00+00:00", "observer_run_id": "run-1",
        "exchange_position_id": None, "exchange_order_id": None, "lifecycle_state": "OPEN",
    }


def _order(**changes):
    order = {
        "orderId": "exit-7", "symbol": "BTC-USDT", "positionSide": "LONG",
        "type": "STOP_MARKET", "status": "FILLED", "avgPrice": "101.25",
        "executedQty": "2", "realizedProfit": "2.5", "commission": "0.2",
        "updateTime": 1788552000123,
    }
    order.update(changes)
    return order


def test_disabled_terminal_observer_is_an_exact_noop():
    service = BrokerReconciliationService(halt_fn=lambda _: None)
    service._observe_terminal_order("BTC-USDT", _order())
    assert service._terminal_observation_counts == {"emitted": 0, "excluded": 0, "errors": 0}


def test_complete_terminal_evidence_emits_and_advances_identity():
    identity = _identity()
    store = MagicMock()
    store.resolve_open.return_value = deepcopy(identity)
    observer = MagicMock()
    service = BrokerReconciliationService(
        halt_fn=lambda _: None, position_identity_store=store, terminal_observer=observer
    )

    service._observe_terminal_order("BTC-USDT", _order())

    event = observer.append.call_args.args[0]
    assert event["event_type"] == "EXIT_FILL_OBSERVED"
    assert event["fill_price"] == 101.25 and event["fees"] == 0.2
    assert event["manager_state_after"] == "TERMINAL_EVIDENCE_COMPLETE"
    advanced = store.upsert.call_args.args[0]
    assert advanced["lifecycle_state"] == "TERMINAL_EVIDENCE_COMPLETE"
    assert advanced["terminal_order_id"] == "exit-7"


def test_incomplete_terminal_evidence_keeps_nulls_and_only_marks_closure():
    store = MagicMock()
    store.resolve_open.return_value = _identity()
    observer = MagicMock()
    service = BrokerReconciliationService(
        halt_fn=lambda _: None, position_identity_store=store, terminal_observer=observer
    )

    service._observe_terminal_order("BTC-USDT", _order(avgPrice="", commission=None))

    event = observer.append.call_args.args[0]
    assert event["fill_price"] is None and event["fees"] is None
    assert event["manager_state_after"] == "CLOSURE_OBSERVED"
    assert store.upsert.call_args.args[0]["lifecycle_state"] == "CLOSURE_OBSERVED"


def test_unknown_identity_and_observer_failure_are_observational():
    store = MagicMock()
    store.resolve_open.return_value = None
    observer = MagicMock()
    service = BrokerReconciliationService(
        halt_fn=lambda _: None, position_identity_store=store, terminal_observer=observer
    )
    service._observe_terminal_order("BTC-USDT", _order())
    assert service._terminal_observation_counts["excluded"] == 1

    store.resolve_open.return_value = _identity()
    observer.append.side_effect = RuntimeError("write failed")
    service._observe_terminal_order("BTC-USDT", _order())
    assert service._terminal_observation_counts["errors"] == 1
