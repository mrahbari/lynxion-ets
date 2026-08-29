"""B4 — broker reconciliation + halt-on-drift: local journal vs actual broker state."""

from types import SimpleNamespace

import pytest

from domain.value_objects import Symbol
from infrastructure.execution.live_order_journal import LiveOrderJournal
from infrastructure.execution.broker_reconciliation import BrokerReconciliationService


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


def test_inspect_reports_drift_without_mutating_or_halting(tmp_path):
    j = _journal(tmp_path)
    ref = j.record_intent("BTC-USDT", "BUY", "0.001", "bingx", "x1")
    j.record_submitted(ref, "OID1", "bingx")
    before = (tmp_path / "j.jsonl").read_bytes()
    halts = []
    broker = _FakeBroker(positions=[_pos("ETH-USDT", 0.5)])

    report = BrokerReconciliationService(halt_fn=halts.append).inspect(broker, j)

    assert report["broker_positions_missing_from_journal"] == [{"symbol": "ETH-USDT", "quantity": "0.5", "side": "LONG"}]
    assert halts == []
    assert (tmp_path / "j.jsonl").read_bytes() == before


def test_recoverable_resolves_inflight_order(tmp_path):
    j = _journal(tmp_path)
    ref = j.record_intent("BTC-USDT", "BUY", "0.001", "bingx", "x1")
    j.record_submitted(ref, "OID1", "bingx")
    broker = _FakeBroker(positions=[_pos("BTC-USDT", 0.001)], statuses={"OID1": "FILLED"})
    rep = BrokerReconciliationService(halt_fn=lambda r: None).reconcile(broker, j)
    assert any(o["order_id"] == "OID1" and o["status"] == "FILLED" for o in rep["orders_resolved"])
    assert j.in_flight() == []                       # resolved -> no longer in-flight
    assert rep["halted"] is False


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
        {"orderId": "SL_EXIT_OID", "type": "STOP_MARKET", "status": "FILLED", "realizedProfit": "-10.00"}
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
        {"orderId": "TP_EXIT_OID", "type": "TAKE_PROFIT_MARKET", "status": "FILLED", "realizedProfit": "15.00"}
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
        {"orderId": "SL_EXIT_OID", "type": "STOP_MARKET", "status": "FILLED", "realizedProfit": "-10.00"}
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
