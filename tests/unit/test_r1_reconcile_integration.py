"""R1 — periodic reconciliation integration: the orchestrator's reconcile loop runs and
halts on unrecoverable drift."""

import logging
from types import SimpleNamespace

import pytest

from domain.value_objects import Symbol
from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
from infrastructure.execution.live_order_journal import LiveOrderJournal


def _pos(symbol, qty):
    return SimpleNamespace(symbol=Symbol(symbol), quantity=qty, side=SimpleNamespace(value="LONG"))


@pytest.fixture(autouse=True)
def _reset_guard():
    from shared.live_execution_guard import live_execution_guard
    live_execution_guard.disengage_kill_switch()
    yield
    live_execution_guard.disengage_kill_switch()


def _orch(execution_service):
    from shared.logger import EnhancedLogger
    o = object.__new__(AutoDetectionOrchestrator)
    o.logger = EnhancedLogger("test_r1")          # real logger — must support .critical (halt path)
    o.is_running = True
    o.reconcile_interval_seconds = 0
    o.risk_alert_service = SimpleNamespace(send_alert=lambda **k: None)
    o.execution_service = execution_service
    return o


def test_get_reconcile_broker_returns_primary_adapter():
    adapter = SimpleNamespace(get_all_positions=lambda: [])
    multi = SimpleNamespace(brokers={"bingx": adapter, "binance": object()}, primary_broker="bingx")
    o = _orch(SimpleNamespace(broker=multi))
    assert o._get_reconcile_broker() is adapter


def test_reconcile_loop_halts_on_unrecoverable_drift(tmp_path, monkeypatch):
    from shared.live_execution_guard import live_execution_guard
    import infrastructure.execution.live_order_journal as loj_mod

    # Fresh empty journal so a broker position is unrecoverable drift.
    monkeypatch.setattr(loj_mod, "live_order_journal", LiveOrderJournal(path=str(tmp_path / "j.jsonl")))

    class DriftBroker:
        def __init__(self, orch): self.orch = orch; self.calls = 0
        def get_all_positions(self):
            self.calls += 1
            self.orch.is_running = False        # stop the loop after this single pass
            return [_pos("DOGE-USDT", 100)]

    multi = SimpleNamespace(brokers={}, primary_broker="bingx")
    o = _orch(SimpleNamespace(broker=multi))
    broker = DriftBroker(o)
    multi.brokers["bingx"] = broker

    o._reconciliation_loop()                    # runs exactly one pass (broker stops it)

    assert broker.calls == 1
    assert live_execution_guard.is_killed() is True, "unrecoverable drift must halt via kill switch"
