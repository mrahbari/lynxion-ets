"""B5 — order lifecycle: functional cancel + status polling at the multi-broker layer,
routed via the order_id -> (exchange, symbol) map."""

import logging
import threading

import pytest

from domain.value_objects import Symbol
from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService


class _FakeAdapter:
    def __init__(self):
        self.cancelled = []
    def cancel_order(self, order_id, symbol):
        self.cancelled.append((order_id, symbol)); return True
    def get_order_status(self, order_id, symbol):
        return "FILLED"


def _svc():
    s = object.__new__(MultiBrokerExecutionService)
    s.logger = logging.getLogger("test_b5")
    s.brokers = {"bingx": _FakeAdapter()}
    s._order_exchange_map = {}
    s._order_map_lock = threading.Lock()
    return s


def test_cancel_and_status_unknown_order():
    s = _svc()
    assert s.cancel_order("NOPE") is False
    assert s.get_execution_status("NOPE") == "unknown"


def test_cancel_and_status_route_to_origin_exchange():
    s = _svc()
    with s._order_map_lock:
        s._order_exchange_map["OID1"] = ("bingx", Symbol("BTC-USDT"))
    assert s.cancel_order("OID1") is True
    assert s.brokers["bingx"].cancelled == [("OID1", Symbol("BTC-USDT"))]
    assert s.get_execution_status("OID1") == "FILLED"
