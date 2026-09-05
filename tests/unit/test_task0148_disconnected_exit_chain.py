import json
from unittest.mock import MagicMock

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


def _run_selected_closure(monkeypatch, tmp_path, *, identity_store=None, observer=None,
                          order_changes=None):
    import infrastructure.execution.broker_reconciliation as reconciliation_module
    from infrastructure.execution.live_order_journal import live_order_journal
    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
    from infrastructure.strategies.strategy_manager import strategy_manager

    monkeypatch.setattr(
        reconciliation_module,
        "ACTIVE_POSITIONS_JOURNAL_PATH",
        str(tmp_path / "active_positions.json"),
    )
    history = MagicMock(return_value=[_terminal_order(type="TAKE_PROFIT_MARKET", **(order_changes or {}))])
    broker = MagicMock()
    broker.get_order_history = history
    trade_result = MagicMock()
    take_profit = MagicMock()
    journal_result = MagicMock()
    telegram = MagicMock()
    monkeypatch.setattr(strategy_manager, "record_trade_result", trade_result)
    monkeypatch.setattr(symbol_cooldown_gate, "record_take_profit_exit", take_profit)
    monkeypatch.setattr(live_order_journal, "record_result", journal_result, raising=False)
    monkeypatch.setattr("infrastructure.services.risk_alerts.send_telegram", telegram)

    service = BrokerReconciliationService(
        halt_fn=lambda _: None,
        position_identity_store=identity_store,
        terminal_observer=observer,
    )
    service._previous_active_symbols = {"BTC-USDT"}
    service._process_position_closures(broker, set())
    return service, history, trade_result, take_profit, journal_result, telegram


def test_selected_closure_keeps_operational_calls_with_observer_enabled(monkeypatch, tmp_path):
    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    snapshot.upsert(_open_identity())
    ledger = ExitEventLedger(tmp_path / "events")

    result = _run_selected_closure(
        monkeypatch, tmp_path, identity_store=snapshot, observer=ledger
    )
    service, history, trade_result, take_profit, journal_result, telegram = result

    history.assert_called_once_with("BTC-USDT", limit=20)
    trade_result.assert_called_once_with("BTC-USDT", is_profitable=True, position_closed=True)
    take_profit.assert_called_once_with("BTC-USDT")
    journal_result.assert_called_once()
    telegram.assert_called_once()
    assert service._terminal_observation_counts["emitted"] == 1
    event_path = next((tmp_path / "events").glob("*.jsonl"))
    assert ledger.validate_file(event_path)["events"] == 1


def test_observer_failure_does_not_change_selected_closure_calls(monkeypatch, tmp_path):
    store = MagicMock()
    store.resolve_open.return_value = _open_identity()
    observer = MagicMock()
    observer.append.side_effect = RuntimeError("observer unavailable")

    result = _run_selected_closure(
        monkeypatch, tmp_path, identity_store=store, observer=observer
    )
    service, history, trade_result, take_profit, journal_result, telegram = result

    history.assert_called_once_with("BTC-USDT", limit=20)
    trade_result.assert_called_once()
    take_profit.assert_called_once()
    journal_result.assert_called_once()
    telegram.assert_called_once()
    assert service._terminal_observation_counts["errors"] == 1


def test_unknown_terminal_side_is_excluded_but_closure_still_propagates(monkeypatch, tmp_path):
    store = MagicMock()
    observer = MagicMock()
    result = _run_selected_closure(
        monkeypatch,
        tmp_path,
        identity_store=store,
        observer=observer,
        order_changes={"positionSide": ""},
    )
    service, history, trade_result, take_profit, journal_result, telegram = result

    history.assert_called_once()
    trade_result.assert_called_once()
    take_profit.assert_called_once()
    journal_result.assert_called_once()
    telegram.assert_called_once()
    store.resolve_open.assert_not_called()
    observer.append.assert_not_called()
    assert service._terminal_observation_counts["excluded"] == 1
