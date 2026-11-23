"""A stop-out followed by a same-symbol re-entry before the next reconciliation pass (A-B-A)
must not happen: the entry is held until the exit is booked (cooldown, trade result, notice).

Incident 2026-11-23 PROMUSDT: SL filled 11:23:50, new BUY 11:24:03, the first exit was never
reconciled (no cooldown, no close message) because the next snapshot still showed a LONG."""

import socket
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

import infrastructure.execution.broker_reconciliation as rec
from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.messaging.clock import ReplayClock
from infrastructure.replay.simulated_broker import SimulatedBrokerAdapter
from infrastructure.services.broker_execution_service import BrokerExecutionService
from infrastructure.shared.pending_orders_tracker import PendingOrdersState
from shared.circuit_breaker import CircuitBreaker
from shared.live_execution_guard import LiveExecutionGuard

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _single_pass_closure(monkeypatch):
    """These tests describe closure handling itself; confirmation debounce is tested separately."""
    import infrastructure.execution.broker_reconciliation as br
    monkeypatch.setattr(br, "CLOSURE_CONFIRM_PASSES", 1)
    monkeypatch.setattr(br, "EMPTY_SNAPSHOT_EXTRA_PASSES", 0)


@pytest.fixture(autouse=True)
def _clean():
    rec._LAST_OBSERVED_OPEN.clear()
    yield
    rec._LAST_OBSERVED_OPEN.clear()


class _Ledger:
    records = []

    def new_order_ref(self):
        return "offline-ref"

    def append(self, kind, payload):
        pass


def _service(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a: (_ for _ in ()).throw(AssertionError("network")))
    clock = ReplayClock(T)
    breaker = CircuitBreaker("order_path:bingx", clock=clock)
    guard = LiveExecutionGuard(breaker_lookup=lambda b: breaker)
    guard.set_risk_enforcer(lambda order: (True, ""))
    broker = SimulatedBrokerAdapter()
    settings = SimpleNamespace(
        execution=SimpleNamespace(prevent_same_direction_trade_per_symbol=True),
        broker=SimpleNamespace(paper_trading=False, testnet=True, bingx_testnet=True,
                               bingx_order_placement_enabled=True))
    svc = BrokerExecutionService(
        settings, broker_type="bingx", broker_adapter=broker, guard_instance=guard,
        ledger_instance=_Ledger(), pending_orders_state=PendingOrdersState(clock=clock),
        symbol_validator_instance=SimpleNamespace(is_symbol_approved=lambda _: True),
        forensic_sink=SimpleNamespace(_generate_trade_id=lambda *a: "t", log_broker_execution=lambda **k: None),
        notification_callback=lambda o, i: None, clock=clock)
    return svc, broker


def _order(sym="PROMUSDT"):
    return Order(symbol=Symbol(sym), side=OrderSide.BUY, quantity=Decimal("1"),
                 price=Money(Decimal("100"), "USDT"), stop_loss_price=Money(Decimal("95"), "USDT"),
                 take_profit_price=Money(Decimal("110"), "USDT"))


def test_snapshot_records_open_symbols_normalized(tmp_path):
    svc = rec.BrokerReconciliationService(halt_fn=lambda r: None,
                                          active_positions_journal_path=str(tmp_path / "a.json"))
    svc._process_position_closures(SimpleNamespace(), {"PROM-USDT"})
    assert rec.exit_unreconciled("PROMUSDT") and rec.exit_unreconciled(Symbol("PROMUSDT"))
    svc._process_position_closures(SimpleNamespace(), set())   # next pass books the exit
    assert not rec.exit_unreconciled("PROMUSDT")


def test_entry_held_when_last_pass_saw_position_but_broker_is_flat(monkeypatch):
    svc, broker = _service(monkeypatch)
    rec._LAST_OBSERVED_OPEN.add("PROMUSDT")
    assert svc.execute_order(_order()) is None
    assert list(broker.orders) == []


def test_entry_allowed_once_exit_is_reconciled_or_symbol_never_open(monkeypatch):
    svc, broker = _service(monkeypatch)
    rec._LAST_OBSERVED_OPEN.add("OTHERUSDT")
    assert svc.execute_order(_order()) is not None


def _recon(tmp_path):
    return rec.BrokerReconciliationService(halt_fn=lambda r: None,
                                           active_positions_journal_path=str(tmp_path / "a.json"))


def _debounce(monkeypatch):
    monkeypatch.setattr(rec, "CLOSURE_CONFIRM_PASSES", 2)
    monkeypatch.setattr(rec, "EMPTY_SNAPSHOT_EXTRA_PASSES", 1)


def test_empty_snapshot_blip_does_not_book_closures(tmp_path, monkeypatch):
    """BingX VST 2026-11-23: positions endpoint returned code 0 with an empty list for ~14 s; the
    reconciler booked 12 open positions as closed (UNKNOWN) twice. A blip must book nothing."""
    _debounce(monkeypatch)
    svc = _recon(tmp_path)
    svc._process_position_closures(SimpleNamespace(), {"LINK-USDT", "ONDO-USDT"})
    svc._process_position_closures(SimpleNamespace(), set())                      # empty blip
    assert svc._previous_active_symbols == {"LINK-USDT", "ONDO-USDT"}
    assert rec.exit_unreconciled("LINKUSDT")                                      # entries still held
    svc._process_position_closures(SimpleNamespace(), set())                      # second empty pass
    assert svc._previous_active_symbols == {"LINK-USDT", "ONDO-USDT"}
    svc._process_position_closures(SimpleNamespace(), {"LINK-USDT", "ONDO-USDT"})  # read recovers
    assert svc._absent_passes == {}


def test_real_exit_is_booked_after_confirmation(tmp_path, monkeypatch):
    _debounce(monkeypatch)
    svc = _recon(tmp_path)
    svc._process_position_closures(SimpleNamespace(), {"LINK-USDT", "ONDO-USDT"})
    svc._process_position_closures(SimpleNamespace(), {"LINK-USDT"})
    assert "ONDO-USDT" in svc._previous_active_symbols                            # pending, not booked
    svc._process_position_closures(SimpleNamespace(), {"LINK-USDT"})
    assert svc._previous_active_symbols == {"LINK-USDT"}                          # booked on 2nd pass
    assert not rec.exit_unreconciled("ONDOUSDT")
