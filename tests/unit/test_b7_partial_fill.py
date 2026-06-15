"""B7 — partial fill handling: lifecycle, restart recovery, reconciliation interaction."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from infrastructure.execution.live_order_journal import LiveOrderJournal
from infrastructure.execution.broker_reconciliation import BrokerReconciliationService


def test_partial_fill_lifecycle(tmp_path):
    j = LiveOrderJournal(path=str(tmp_path / "j.jsonl"))
    ref = j.record_intent("BTC-USDT", "BUY", "1.0", "bingx", "x1")
    j.record_submitted(ref, "OID1", "bingx")
    assert j.record_fill(ref, "0.4", "1.0") == "PARTIALLY_FILLED"
    assert j.net_filled(ref) == Decimal("0.4")
    assert len(j.in_flight()) == 1                       # partial stays in-flight
    assert j.record_fill(ref, "1.0", "1.0") == "FILLED"
    assert j.in_flight() == []                           # fully filled -> terminal


def test_partial_fill_survives_restart(tmp_path):
    p = str(tmp_path / "j.jsonl")
    j1 = LiveOrderJournal(path=p)
    ref = j1.record_intent("ETH-USDT", "BUY", "2.0", "bingx", "x2")
    j1.record_submitted(ref, "OID2", "bingx")
    j1.record_fill(ref, "0.5", "2.0")
    # restart
    j2 = LiveOrderJournal(path=p)
    rec = j2.recover()
    assert rec["status_counts"].get("PARTIALLY_FILLED") == 1
    assert j2.net_filled(ref) == Decimal("0.5")          # partial state recovered
    inflight = j2.in_flight()
    assert len(inflight) == 1 and inflight[0]["status"] == "PARTIALLY_FILLED"


class _FillBroker:
    def __init__(self, fills):
        self._fills = fills
    def get_all_positions(self):
        return []
    def get_order_fill(self, order_id, symbol):
        return self._fills.get(str(order_id), {"status": "NEW", "executed_qty": 0, "avg_price": None})


def test_reconciliation_records_partial_then_full(tmp_path):
    j = LiveOrderJournal(path=str(tmp_path / "j.jsonl"))
    ref = j.record_intent("BTC-USDT", "BUY", "1.0", "bingx", "x1")
    j.record_submitted(ref, "OID1", "bingx")
    svc = BrokerReconciliationService(halt_fn=lambda r: None)

    # First reconcile: broker reports a partial fill.
    broker = _FillBroker({"OID1": {"status": "PARTIALLY_FILLED", "executed_qty": 0.4, "avg_price": 60000}})
    rep = svc.reconcile(broker, j)
    assert any(r.get("issue") == "partially_filled" for r in rep["recoverable"])
    assert j.net_filled(ref) == Decimal("0.4")
    assert len(j.in_flight()) == 1                       # still in-flight

    # Second reconcile: order now fully filled.
    broker2 = _FillBroker({"OID1": {"status": "FILLED", "executed_qty": 1.0, "avg_price": 60010}})
    rep2 = svc.reconcile(broker2, j)
    assert any(o["status"] == "FILLED" for o in rep2["orders_resolved"])
    assert j.in_flight() == []                           # resolved
