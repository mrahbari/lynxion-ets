"""2026-11-25: orphan PROTECTION_UNKNOWN stop-update records (position already flat) blocked all orders for ~6 h."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from infrastructure.execution import broker_reconciliation as rec

NOW = datetime(2026, 11, 25, 14, 0, tzinfo=timezone.utc)


class _Journal:
    def __init__(self, records):
        self.records, self.closed = records, []

    def in_flight(self):
        return self.records

    def record_terminal(self, ref, status, **extra):
        self.closed.append((ref, status))


def _r(ref, sym, age_s, entry_ref=None, status="PROTECTION_UNKNOWN"):
    return {"order_ref": ref, "symbol": sym, "status": status, "entry_order_ref": entry_ref,
            "ts": (NOW - timedelta(seconds=age_s)).isoformat()}


def test_flat_old_stop_update_record_is_closed_others_kept():
    j = _Journal([_r("a", "IMXUSDT", 3600), _r("b", "NOTUSDT", 3600), _r("c", "ADAUSDT", 30),
                  _r("d", "XRPUSDT", 3600, entry_ref="e1"), _r("e", "SOLUSDT", 3600, status="INTENT")])
    report = {"errors": []}
    rec.BrokerReconciliationService._resolve_orphan_protection(
        j, [SimpleNamespace(symbol="NOT-USDT")], report, now=NOW)
    assert j.closed == [("a", "CANCELLED")]                 # NOT open, ADA too recent, XRP entry-protection, SOL intent
    assert report["orphan_protection_resolved"] == ["IMXUSDT"]


class _Broker:
    def __init__(self, status="OK", orders=()):
        self.ev = {"status": status, "orders": list(orders)}

    def get_pending_orders_evidence(self, symbol):
        return self.ev


class _J2(_Journal):
    def record_failed(self, ref, reason=""):
        self.closed.append((ref, "FAILED"))


def test_orphan_intent_closed_only_when_flat_and_no_pending_orders():
    def run(broker, positions=()):
        j = _J2([{**_r("i", "PEOPLEUSDT", 600, status="INTENT"), "order_id": None}])
        rec.BrokerReconciliationService._resolve_orphan_protection(j, list(positions), {"errors": []}, now=NOW,
                                                                   broker=broker)
        return j.closed
    assert run(_Broker()) == [("i", "FAILED")]
    assert run(_Broker(orders=[{"orderId": 1}])) == []                      # a pending order could still fill
    assert run(_Broker(status="API_ERROR")) == []                          # no evidence -> keep blocking
    assert run(_Broker(), [SimpleNamespace(symbol="PEOPLE-USDT")]) == []   # position open
    assert run(None) == []                                                 # no broker -> unchanged behaviour
