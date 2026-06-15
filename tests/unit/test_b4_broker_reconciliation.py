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
