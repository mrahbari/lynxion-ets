import json

from infrastructure.execution.broker_reconciliation import BrokerReconciliationService
from infrastructure.observability.exit_event_ledger import ExitEventLedger
from infrastructure.observability.position_identity_snapshot import (
    PositionIdentitySnapshot,
    deterministic_record_id,
)


def _open_identity(side="LONG", first="2026-09-04T19:00:00+00:00"):
    position_key = f"BTCUSDT:{side}:100"
    run_id = "task0148-run"
    return {
        "schema_version": 1,
        "record_id": deterministic_record_id(position_key, run_id, first),
        "position_key": position_key,
        "symbol": "BTCUSDT",
        "side": side,
        "entry_price": 100.0,
        "quantity": 2.0,
        "exchange_leverage": 5.0,
        "first_observed_utc": first,
        "last_observed_utc": first,
        "observer_run_id": run_id,
        "exchange_position_id": None,
        "exchange_order_id": None,
        "lifecycle_state": "OPEN",
    }


def _terminal_order(**changes):
    order = {
        "orderId": "exit-0148",
        "symbol": "BTC-USDT",
        "positionSide": "LONG",
        "type": "STOP_MARKET",
        "status": "FILLED",
        "avgPrice": "101.25",
        "executedQty": "2",
        "realizedProfit": "2.5",
        "commission": "0.2",
        "updateTime": 1788552000123,
        "stopPrice": "101.3",
        "workingType": "MARK_PRICE",
    }
    order.update(changes)
    return order


def _components(tmp_path):
    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    ledger = ExitEventLedger(tmp_path / "events")
    snapshot.upsert(_open_identity())
    service = BrokerReconciliationService(
        halt_fn=lambda _: None,
        position_identity_store=snapshot,
        terminal_observer=ledger,
    )
    return service, snapshot, ledger


def test_real_components_persist_and_validate_one_complete_exit(tmp_path):
    service, snapshot, ledger = _components(tmp_path)

    service._observe_terminal_order("BTC-USDT", _terminal_order())

    event_path = next((tmp_path / "events").glob("*.jsonl"))
    validation = ledger.validate_file(event_path)
    event = json.loads(event_path.read_text(encoding="utf-8"))
    assert validation["events"] == 1
    assert event["fill_price"] == 101.25
    assert event["terminal_order_id"] == "exit-0148"
    assert event["manager_state_after"] == "TERMINAL_EVIDENCE_COMPLETE"
    assert snapshot.resolve_open("BTCUSDT", "LONG") is None
    persisted = json.loads((tmp_path / "identities.json").read_text(encoding="utf-8"))
    record = next(iter(persisted["records"].values()))
    assert record["lifecycle_state"] == "TERMINAL_EVIDENCE_COMPLETE"
    assert record["terminal_order_id"] == "exit-0148"


def test_real_components_preserve_nulls_and_restart_idempotency(tmp_path):
    service, snapshot, ledger = _components(tmp_path)
    incomplete = _terminal_order(avgPrice="", commission=None)

    service._observe_terminal_order("BTC-USDT", incomplete)
    reconstructed = BrokerReconciliationService(
        halt_fn=lambda _: None,
        position_identity_store=PositionIdentitySnapshot(tmp_path / "identities.json"),
        terminal_observer=ExitEventLedger(tmp_path / "events"),
    )
    reconstructed._observe_terminal_order("BTC-USDT", incomplete)

    event_path = next((tmp_path / "events").glob("*.jsonl"))
    events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
    assert len(events) == 1
    assert events[0]["fill_price"] is None and events[0]["fees"] is None
    assert events[0]["manager_state_after"] == "CLOSURE_OBSERVED"
    assert reconstructed._terminal_observation_counts["excluded"] == 1
    assert ledger.validate_file(event_path)["events"] == 1


def test_ambiguous_and_corrupt_identity_fail_without_event_file(tmp_path):
    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    snapshot.upsert(_open_identity(first="2026-09-04T19:00:00+00:00"))
    snapshot.upsert(_open_identity(first="2026-09-04T19:01:00+00:00"))
    ledger = ExitEventLedger(tmp_path / "events")
    service = BrokerReconciliationService(
        halt_fn=lambda _: None, position_identity_store=snapshot, terminal_observer=ledger
    )

    service._observe_terminal_order("BTC-USDT", _terminal_order())
    assert service._terminal_observation_counts["errors"] == 1
    assert not (tmp_path / "events").exists()

    (tmp_path / "identities.json").write_text("not-json", encoding="utf-8")
    service._observe_terminal_order("BTC-USDT", _terminal_order())
    assert service._terminal_observation_counts["errors"] == 2
    assert not (tmp_path / "events").exists()
