"""B4 — broker reconciliation + halt-on-drift: local journal vs actual broker state."""

from types import SimpleNamespace

import pytest

from domain.value_objects import Symbol
from infrastructure.execution.live_order_journal import LiveOrderJournal
from infrastructure.execution.broker_reconciliation import BrokerReconciliationService


def test_complete_initial_ack_evidence_does_not_create_unknown_marker(tmp_path):
    journal = _journal(tmp_path)
    ref = journal.record_intent("BTC-USDT", "BUY", "1", "bingx", stop_loss="90", take_profit="110")
    journal.record_submitted(ref, "ENTRY-1", "bingx", protective_order_ids={
        "STOP_MARKET": "SL-1", "TAKE_PROFIT_MARKET": "TP-1"})
    broker = _FakeBroker(positions=[_pos("BTC-USDT", 1)], statuses={"ENTRY-1": "FILLED"})
    report = BrokerReconciliationService(halt_fn=lambda reason: None).reconcile(broker, journal)
    # Existing contract reports a recovered transition as not-yet-in-sync this pass.
    assert report["in_sync"] is False
    assert report["orders_resolved"] == [{"order_id": "ENTRY-1", "status": "FILLED", "executed_qty": None}]
    assert journal.in_flight() == []
    assert BrokerReconciliationService(halt_fn=lambda reason: None).reconcile(broker, journal)["in_sync"] is True

def test_recovery_protection_persistence_failure_halts(tmp_path, monkeypatch):
    journal = _journal(tmp_path)
    ref = journal.record_intent("BTC-USDT", "BUY", "1", "bingx", stop_loss="90")
    journal.record_submitted(ref, "ENTRY-1", "bingx")
    def fail(*args, **kwargs):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(journal, "record_protection_unknown", fail)
    halts = []
    report = BrokerReconciliationService(halt_fn=halts.append).reconcile(
        _FakeBroker(positions=[_pos("BTC-USDT", 1)], statuses={"ENTRY-1": "FILLED"}), journal)
    assert report["halted"] is True and report["in_sync"] is False
    assert halts == ["UNVERIFIED_PROTECTION_PERSISTENCE_FAILED"]
    assert journal.in_flight()[0]["status"] == "SUBMITTED"

@pytest.mark.parametrize("status", ["FILLED", "PARTIALLY_FILLED", "PARTIAL", "UNKNOWN", "CANCELED"])
@pytest.mark.parametrize("ids", [None, {"STOP_MARKET": "SL-1"}])
def test_entry_fill_cannot_hide_missing_requested_protection(tmp_path, status, ids):
    journal = _journal(tmp_path)
    ref = journal.record_intent("BTC-USDT", "BUY", "1", "bingx", stop_loss="90", take_profit="110")
    journal.record_submitted(ref, "ENTRY-1", "bingx", protective_order_ids=ids)
    before = (tmp_path / "j.jsonl").read_bytes()
    broker = _FakeBroker(positions=[_pos("BTC-USDT", 1)], statuses={"ENTRY-1": status})
    broker.get_order_fill = lambda *args: {"status": status, "executed_qty": "1" if status == "FILLED" else "0.5",
                                         "avg_price": "100"}
    report = BrokerReconciliationService(halt_fn=lambda reason: None).reconcile(broker, journal)
    assert report["in_sync"] is False and report["orders_resolved"] == []
    assert any(row["issue"] == "requested_protection_acknowledgements_missing" for row in report["recoverable"])
    assert journal.in_flight()[0]["status"] == "SUBMITTED"
    assert (tmp_path / "j.jsonl").read_bytes().startswith(before)
    assert any(row["status"] == "PROTECTION_UNKNOWN" and row["entry_order_ref"] == ref for row in journal.in_flight())
    after = (tmp_path / "j.jsonl").read_bytes()
    BrokerReconciliationService(halt_fn=lambda reason: None).reconcile(broker, journal)
    assert (tmp_path / "j.jsonl").read_bytes() == after
    with pytest.raises(RuntimeError):
        journal.record_intent("ETH-USDT", "BUY", "1", "bingx")
    assert LiveOrderJournal(path=str(tmp_path / "j.jsonl")).in_flight()[0]["order_ref"] == ref

def test_durable_unknown_protection_is_reported_unresolved_while_flat(tmp_path):
    journal = _journal(tmp_path)
    ref = journal.record_protection_unknown("BTC-USDT", "SELL", "1", "bingx")
    before = (tmp_path / "j.jsonl").read_bytes()
    report = BrokerReconciliationService(halt_fn=lambda reason: None).reconcile(_FakeBroker(), journal)
    assert report["in_sync"] is False and report["orders_resolved"] == []
    assert any(record["order_ref"] == ref for record in report["recoverable"])
    assert journal.in_flight()[0]["status"] == "PROTECTION_UNKNOWN"
    assert (tmp_path / "j.jsonl").read_bytes() == before

@pytest.mark.parametrize("field,value", [("positionSide", "SHORT"), ("positionSide", None),
    ("side", "BUY"), ("side", None), ("executedQty", "0.5"), ("executedQty", None)])
def test_exit_must_match_observed_position_side_and_full_quantity(tmp_path, monkeypatch, field, value):
    service = BrokerReconciliationService(halt_fn=lambda reason: None)
    broker = _FakeBroker(positions=[_pos("ADA-USDT", 1.0)])
    journal = _journal(tmp_path)
    service.reconcile(broker, journal)
    row = {"symbol": "ADAUSDT", "orderId": "UNVERIFIED", "type": "STOP_MARKET",
           "status": "FILLED", "realizedProfit": "-1", "side": "SELL", "positionSide": "LONG", "executedQty": "1"}
    row[field] = value
    broker._positions = []
    broker.get_order_history = lambda *args, **kwargs: [row]
    holds = []
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda *args, **kwargs: pytest.fail("lifecycle shape unverified"))
    monkeypatch.setattr("infrastructure.risk.symbol_cooldown_gate.symbol_cooldown_gate", SimpleNamespace(record_unverified_exit=holds.append))
    monkeypatch.setattr("infrastructure.services.risk_alerts.send_telegram", lambda *args: None)
    service.reconcile(broker, journal)
    assert holds == ["ADA-USDT"]
    assert not service._processed_closed_exits

@pytest.mark.parametrize("order_type,pnl,expected", [
    ("TAKE_PROFIT_MARKET", "-2", False), ("TAKE_PROFIT_MARKET", "0", False),
    ("STOP_MARKET", "2", True)])
def test_exit_profit_classification_uses_pnl_not_order_name(tmp_path, monkeypatch, order_type, pnl, expected):
    service = BrokerReconciliationService(halt_fn=lambda reason: None)
    service._previous_active_symbols = {"ADA-USDT"}
    service._observed_active_symbols = {"ADA-USDT"}
    service._observed_position_details = {"ADA-USDT": {"side": "LONG", "quantity": "1"}}
    broker = _FakeBroker()
    broker.get_order_history = lambda *args, **kwargs: [{"symbol": "ADAUSDT",
        "side": "SELL", "positionSide": "LONG", "executedQty": "1", "orderId": "ISOLATED-EXIT", "type": order_type, "status": "FILLED", "realizedProfit": pnl}]
    results, gates = [], []
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda symbol, is_profitable, **kwargs: results.append(is_profitable))
    monkeypatch.setattr("infrastructure.risk.symbol_cooldown_gate.symbol_cooldown_gate", SimpleNamespace(
        record_stop_loss_exit=lambda *args: gates.append("loss"),
        record_take_profit_exit=lambda *args: gates.append("profit")))
    import infrastructure.execution.live_order_journal as journal_module
    monkeypatch.setattr(journal_module, "live_order_journal", SimpleNamespace(record_result=lambda **kwargs: None))
    monkeypatch.setattr("infrastructure.services.risk_alerts.send_telegram", lambda *args: None)
    service._process_position_closures(broker, set())
    assert results == [expected]
    assert gates == ["profit" if expected else "loss"]

@pytest.mark.parametrize("order_symbol", [None, "XRP-USDT"])
def test_exit_history_without_matching_symbol_is_unverified(tmp_path, monkeypatch, order_symbol):
    service = BrokerReconciliationService(halt_fn=lambda reason: None)
    service._previous_active_symbols = {"ADA-USDT"}
    service._observed_active_symbols = {"ADA-USDT"}
    service._observed_position_details = {"ADA-USDT": {"side": "LONG", "quantity": "1"}}
    broker = _FakeBroker()
    row = {"side": "SELL", "positionSide": "LONG", "executedQty": "1", "orderId": "WRONG-LIFECYCLE", "status": "FILLED", "type": "STOP_MARKET", "realizedProfit": "-10"}
    if order_symbol is not None:
        row["symbol"] = order_symbol
    broker.get_order_history = lambda *args, **kwargs: [row]
    holds = []
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda *args, **kwargs: pytest.fail("symbol identity unverified"))
    monkeypatch.setattr("infrastructure.risk.symbol_cooldown_gate.symbol_cooldown_gate", SimpleNamespace(record_unverified_exit=holds.append))
    monkeypatch.setattr("infrastructure.services.risk_alerts.send_telegram", lambda *args: None)
    service._process_position_closures(broker, set())
    assert holds == ["ADA-USDT"]
    assert not service._processed_closed_exits

@pytest.mark.parametrize("history_case", ["empty", "timeout", "missing_pnl", "nan_pnl"])
def test_observed_flat_with_unknown_outcome_never_invents_loss(tmp_path, monkeypatch, history_case):
    service = BrokerReconciliationService(halt_fn=lambda reason: None)
    service._previous_active_symbols = {"ADA-USDT"}
    service._observed_active_symbols = {"ADA-USDT"}
    service._observed_position_details = {"ADA-USDT": {"side": "LONG", "quantity": "1"}}
    broker = _FakeBroker()
    def history(*args, **kwargs):
        if history_case == "timeout":
            raise TimeoutError("synthetic history unavailable")
        if history_case == "empty":
            return []
        row = {"side": "SELL", "positionSide": "LONG", "executedQty": "1", "symbol": "ADAUSDT", "orderId": "STOP", "status": "FILLED", "type": "STOP_MARKET"}
        if history_case == "nan_pnl":
            row["realizedProfit"] = "NaN"
        return [row]
    broker.get_order_history = history
    holds, alerts, writes = [], [], []
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda *args, **kwargs: pytest.fail("outcome unknown"))
    monkeypatch.setattr("infrastructure.risk.symbol_cooldown_gate.symbol_cooldown_gate", SimpleNamespace(
        record_unverified_exit=holds.append,
        record_stop_loss_exit=lambda *args: pytest.fail("not a verified loss"),
        record_take_profit_exit=lambda *args: pytest.fail("not a verified profit")))
    import infrastructure.execution.live_order_journal as journal_module
    monkeypatch.setattr(journal_module, "live_order_journal", SimpleNamespace(record_result=lambda **kwargs: writes.append(kwargs)))
    monkeypatch.setattr("infrastructure.services.risk_alerts.send_telegram", alerts.append)
    service._process_position_closures(broker, set())
    service._process_position_closures(broker, set())
    assert holds == ["ADA-USDT"] and writes == []
    assert len(alerts) == 1 and "UNKNOWN" in alerts[0]
    assert service._processed_closed_exits == set()

def test_restored_first_flat_is_unverified_not_new_trade_result(tmp_path, monkeypatch):
    (tmp_path / "active_positions_journal.json").write_text('{"active_symbols":["ADA-USDT"]}')
    service = BrokerReconciliationService(halt_fn=lambda reason: None)
    broker = _FakeBroker()
    broker.get_order_history = lambda *args, **kwargs: pytest.fail("no observed lifecycle to join")
    calls, alerts = [], []
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda *args, **kwargs: pytest.fail("not a verified trade result"))
    monkeypatch.setattr("infrastructure.risk.symbol_cooldown_gate.symbol_cooldown_gate",
                        SimpleNamespace(record_unverified_exit=calls.append))
    monkeypatch.setattr("infrastructure.services.risk_alerts.send_telegram", alerts.append)
    service.reconcile(broker, _journal(tmp_path))
    service.reconcile(broker, _journal(tmp_path))
    assert calls == ["ADA-USDT"]
    assert len(alerts) == 1 and "UNVERIFIED" in alerts[0]
    assert service._processed_closed_exits == set()

@pytest.mark.parametrize("existing_expiry", [0, 99999999999])
def test_unverified_exit_hold_preserves_history_and_stronger_gate(monkeypatch, existing_expiry):
    from datetime import datetime
    from infrastructure.risk.symbol_cooldown_gate import SymbolCooldownGate
    gate = object.__new__(SymbolCooldownGate)
    gate._sl_cooldowns = {"ADAUSDT": existing_expiry}
    gate._symbol_loss_history = {"ADAUSDT": [1.0]}
    monkeypatch.setattr(gate, "_save_cooldown_journal", lambda: None)
    when = datetime(2026, 1, 1)
    gate.record_unverified_exit("ADA-USDT", when)
    assert gate._sl_cooldowns["ADAUSDT"] == max(existing_expiry, when.timestamp() + 3600)
    assert gate._symbol_loss_history == {"ADAUSDT": [1.0]}

@pytest.mark.parametrize("status", ["CANCELED", "CANCELLED", "REJECTED", "EXPIRED"])
def test_nonfilled_protective_order_is_never_recorded_as_fill(tmp_path, monkeypatch, status):
    service = BrokerReconciliationService(halt_fn=lambda reason: None)
    service._previous_active_symbols = {"ADA-USDT"}
    service._observed_active_symbols = {"ADA-USDT"}
    service._observed_position_details = {"ADA-USDT": {"side": "LONG", "quantity": "1"}}
    broker = _FakeBroker()
    broker.get_order_history = lambda *args, **kwargs: [{
        "side": "SELL", "positionSide": "LONG", "executedQty": "1", "symbol": "ADAUSDT", "orderId": "NONFILL", "status": status, "type": "STOP_MARKET"}]
    writes = []
    import infrastructure.execution.live_order_journal as journal_module
    monkeypatch.setattr(journal_module, "live_order_journal", SimpleNamespace(
        record_result=lambda **kwargs: writes.append(kwargs)))
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda *args, **kwargs: None)
    monkeypatch.setattr("infrastructure.services.risk_alerts.send_telegram", lambda *args: None)
    service._process_position_closures(broker, set())
    assert writes == []
    assert "ADA-USDT_NONFILL" not in service._processed_closed_exits

@pytest.mark.parametrize("failure", ["exception", "missing"])
def test_unavailable_position_snapshot_never_processes_closures(tmp_path, monkeypatch, failure):
    service = BrokerReconciliationService(halt_fn=lambda reason: None)
    service._previous_active_symbols = {"DOGE-USDT"}
    def positions():
        if failure == "exception":
            raise TimeoutError("synthetic unavailable snapshot")
        return None
    broker = SimpleNamespace(get_all_positions=positions)
    monkeypatch.setattr(service, "_process_position_closures", lambda *args: pytest.fail(
        "unavailable broker snapshot must not be interpreted as flat"))
    journal = _journal(tmp_path)
    before = (tmp_path / "j.jsonl").read_bytes() if (tmp_path / "j.jsonl").exists() else None
    report = service.reconcile(broker, journal)
    assert report["in_sync"] is False and report["errors"]
    assert service._previous_active_symbols == {"DOGE-USDT"}
    assert ((tmp_path / "j.jsonl").read_bytes() if (tmp_path / "j.jsonl").exists() else None) == before

def _pos(symbol, qty, side="LONG"):
    return SimpleNamespace(symbol=Symbol(symbol), quantity=qty, side=SimpleNamespace(value=side))


class _FakeBroker:
    def __init__(self, positions=None, statuses=None):
        self._positions = positions or []
        self._statuses = statuses or {}
    def get_all_positions(self):
        return self._positions
    def get_order_status(self, order_id, symbol):
        return self._statuses.get(str(order_id), "NEW")


@pytest.fixture(autouse=True)
def _isolate_active_positions_journal(tmp_path, monkeypatch):
    test_path = str(tmp_path / "active_positions_journal.json")
    monkeypatch.setattr("infrastructure.execution.broker_reconciliation.ACTIVE_POSITIONS_JOURNAL_PATH", test_path)
    yield


def _journal(tmp_path, name="j.jsonl"):
    return LiveOrderJournal(path=str(tmp_path / name))


def test_no_drift_when_positions_known_and_orders_open(tmp_path):
    j = _journal(tmp_path)
    ref = j.record_intent("BTC-USDT", "BUY", "0.001", "bingx", "x1")
    j.record_submitted(ref, "OID1", "bingx")
    broker = _FakeBroker(positions=[_pos("BTC-USDT", 0.001)], statuses={"OID1": "NEW"})
    halts = []
    rep = BrokerReconciliationService(halt_fn=halts.append).reconcile(broker, j)
    assert rep["halted"] is False and rep["unrecoverable"] == [] and halts == []


def test_recoverable_resolves_inflight_order(tmp_path):
    j = _journal(tmp_path)
    ref = j.record_intent("BTC-USDT", "BUY", "0.001", "bingx", "x1")
    j.record_submitted(ref, "OID1", "bingx")
    broker = _FakeBroker(positions=[_pos("BTC-USDT", 0.001)], statuses={"OID1": "FILLED"})
    rep = BrokerReconciliationService(halt_fn=lambda r: None).reconcile(broker, j)
    assert any(o["order_id"] == "OID1" and o["status"] == "FILLED" for o in rep["orders_resolved"])
    assert j.in_flight() == []                       # resolved -> no longer in-flight
    assert rep["halted"] is False


def test_unknown_broker_status_while_flat_does_not_invent_cancellation(tmp_path):
    journal = _journal(tmp_path)
    ref = journal.record_intent("FET-USDT", "BUY", "10", "bingx", "stable-client-id")
    journal.record_submitted(ref, "OID-UNKNOWN", "bingx")
    broker = _FakeBroker(positions=[], statuses={"OID-UNKNOWN": "UNKNOWN"})
    before = (tmp_path / "j.jsonl").read_bytes()

    report = BrokerReconciliationService(halt_fn=lambda reason: None).reconcile(broker, journal)

    assert report["orders_resolved"] == []
    assert report["recoverable"] == [{"order_id": "OID-UNKNOWN", "issue": "status=UNKNOWN", "symbol": "FET-USDT"}]
    assert journal.in_flight()[0]["status"] == "SUBMITTED"
    assert (tmp_path / "j.jsonl").read_bytes() == before
    again = BrokerReconciliationService(halt_fn=lambda reason: None).reconcile(broker, journal)
    assert again["recoverable"] == report["recoverable"]
    assert (tmp_path / "j.jsonl").read_bytes() == before


def test_broker_status_timeout_while_flat_preserves_unresolved_order(tmp_path):
    journal = _journal(tmp_path)
    ref = journal.record_intent("FET-USDT", "BUY", "10", "bingx", "stable-client-id")
    journal.record_submitted(ref, "OID-TIMEOUT", "bingx")
    broker = _FakeBroker(positions=[])

    def timeout(_order_id, _symbol):
        raise TimeoutError("status query timed out")

    broker.get_order_status = timeout
    before = (tmp_path / "j.jsonl").read_bytes()
    report = BrokerReconciliationService(halt_fn=lambda reason: None).reconcile(broker, journal)

    assert report["errors"] == ["status(OID-TIMEOUT) failed: status query timed out"]
    assert report["recoverable"] == [{"order_id": "OID-TIMEOUT", "issue": "status=UNKNOWN", "symbol": "FET-USDT"}]
    assert report["orders_resolved"] == []
    assert journal.in_flight()[0]["status"] == "SUBMITTED"
    assert (tmp_path / "j.jsonl").read_bytes() == before


def test_unrecoverable_drift_halts(tmp_path):
    j = _journal(tmp_path)                            # journal empty: no local record of anything
    broker = _FakeBroker(positions=[_pos("ETH-USDT", 0.5)])  # broker holds a position we don't know about
    halts = []
    rep = BrokerReconciliationService(halt_fn=halts.append).reconcile(broker, j)
    assert rep["halted"] is True
    assert any(u["symbol"] == "ETH-USDT" for u in rep["unrecoverable"])
    assert halts and "UNRECOVERABLE" in halts[0]


def test_default_halt_engages_kill_switch(tmp_path):
    from shared.live_execution_guard import live_execution_guard
    live_execution_guard.disengage_kill_switch()
    j = _journal(tmp_path)
    broker = _FakeBroker(positions=[_pos("ETH-USDT", 0.5)])
    BrokerReconciliationService().reconcile(broker, j)   # default halt -> guard kill switch
    assert live_execution_guard.is_killed() is True
    live_execution_guard.disengage_kill_switch()


def test_entry_order_filled_does_not_trigger_trade_result(tmp_path, monkeypatch):
    """TEST 1: Entry order FILLED while position still exists must NOT trigger record_trade_result()."""
    j = _journal(tmp_path)
    ref = j.record_intent("ADA-USDT", "BUY", "1.0", "bingx", "x1")
    j.record_submitted(ref, "ENTRY_OID", "bingx")

    broker = _FakeBroker(positions=[_pos("ADA-USDT", 1.0)], statuses={"ENTRY_OID": "FILLED"})

    trade_results = []
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda sym, is_profitable, position_closed=True: trade_results.append((sym, is_profitable)))

    svc = BrokerReconciliationService(halt_fn=lambda r: None)
    svc.reconcile(broker, j)

    # Assert record_trade_result was NOT called for entry fill
    assert trade_results == []


def test_sl_position_close_triggers_cooldown(tmp_path, monkeypatch):
    """TEST 2: Position closure via STOP_MARKET (realizedProfit < 0) calls record_trade_result(is_profitable=False)."""
    j = _journal(tmp_path)
    broker = _FakeBroker(positions=[_pos("ADA-USDT", 1.0)])

    svc = BrokerReconciliationService(halt_fn=lambda r: None)

    # Pass 1: Position is OPEN
    svc.reconcile(broker, j)

    # Pass 2: Position drops to 0 (CLOSED) via STOP_MARKET
    broker._positions = []
    broker.get_order_history = lambda sym, limit=10: [
        {"side": "SELL", "positionSide": "LONG", "executedQty": "1", "symbol": "ADAUSDT", "orderId": "SL_EXIT_OID", "type": "STOP_MARKET", "status": "FILLED", "realizedProfit": "-10.00"}
    ]

    trade_results = []
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda sym, is_profitable, position_closed=True: trade_results.append((sym, is_profitable)))

    svc.reconcile(broker, j)

    # Assert record_trade_result was called ONCE with is_profitable=False
    assert trade_results == [("ADA-USDT", False)]


def test_tp_position_close_no_cooldown(tmp_path, monkeypatch):
    """TEST 3: Position closure via TAKE_PROFIT_MARKET calls record_trade_result(is_profitable=True)."""
    j = _journal(tmp_path)
    broker = _FakeBroker(positions=[_pos("ADA-USDT", 1.0)])

    svc = BrokerReconciliationService(halt_fn=lambda r: None)

    # Pass 1: Position OPEN
    svc.reconcile(broker, j)

    # Pass 2: Position CLOSED via TAKE_PROFIT_MARKET
    broker._positions = []
    broker.get_order_history = lambda sym, limit=10: [
        {"side": "SELL", "positionSide": "LONG", "executedQty": "1", "symbol": "ADAUSDT", "orderId": "TP_EXIT_OID", "type": "TAKE_PROFIT_MARKET", "status": "FILLED", "realizedProfit": "15.00"}
    ]

    trade_results = []
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda sym, is_profitable, position_closed=True: trade_results.append((sym, is_profitable)))

    svc.reconcile(broker, j)

    # Assert record_trade_result was called ONCE with is_profitable=True
    assert trade_results == [("ADA-USDT", True)]


def test_idempotent_closed_position_event(tmp_path, monkeypatch):
    """TEST 4: Same closed position in multiple reconciliation cycles calls record_trade_result EXACTLY ONCE."""
    j = _journal(tmp_path)
    broker = _FakeBroker(positions=[_pos("ADA-USDT", 1.0)])

    svc = BrokerReconciliationService(halt_fn=lambda r: None)

    # Pass 1: Position OPEN
    svc.reconcile(broker, j)

    # Pass 2 & 3: Position CLOSED
    broker._positions = []
    broker.get_order_history = lambda sym, limit=10: [
        {"side": "SELL", "positionSide": "LONG", "executedQty": "1", "symbol": "ADAUSDT", "orderId": "SL_EXIT_OID", "type": "STOP_MARKET", "status": "FILLED", "realizedProfit": "-10.00"}
    ]

    trade_results = []
    from infrastructure.strategies.strategy_manager import strategy_manager
    monkeypatch.setattr(strategy_manager, "record_trade_result", lambda sym, is_profitable, position_closed=True: trade_results.append((sym, is_profitable)))

    # Cycle 2
    svc.reconcile(broker, j)
    # Cycle 3 (Duplicate cycle)
    svc.reconcile(broker, j)

    # Assert called EXACTLY ONCE across multiple cycles
    assert trade_results == [("ADA-USDT", False)]

