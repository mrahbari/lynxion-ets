"""Existing broker execution controls can bind to local safe adapters."""

import socket
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import pytest

from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.messaging.clock import ReplayClock
from infrastructure.replay.simulated_broker import SimulatedBrokerAdapter
from infrastructure.services.broker_execution_service import BrokerExecutionService
from infrastructure.shared.pending_orders_tracker import PendingOrdersState
from shared.circuit_breaker import CircuitBreaker
from shared.live_execution_guard import LiveExecutionGuard


T = datetime(2026, 1, 1, tzinfo=timezone.utc)


class Ledger:
    def __init__(self):
        self.records = []

    def new_order_ref(self):
        return "offline-ref"

    def append(self, kind, payload):
        self.records.append((kind, payload))


def test_scoped_existing_order_service_reaches_only_simulated_broker(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *args: (_ for _ in ()).throw(
        AssertionError("network reached")))
    clock = ReplayClock(T)
    breaker = CircuitBreaker("order_path:bingx", clock=clock)
    guard = LiveExecutionGuard(breaker_lookup=lambda broker: breaker)
    risk_calls = []
    guard.set_risk_enforcer(lambda order: (risk_calls.append(order), (True, ""))[1])
    broker = SimulatedBrokerAdapter()
    ledger = Ledger()
    forensic = SimpleNamespace(
        _generate_trade_id=lambda *args: "offline-trade",
        log_broker_execution=lambda **kwargs: forensic_records.append(kwargs),
    )
    forensic_records = []
    notifications = []
    pending = PendingOrdersState(clock=clock)
    settings = SimpleNamespace(
        execution=SimpleNamespace(prevent_same_direction_trade_per_symbol=True),
        broker=SimpleNamespace(paper_trading=False, testnet=True,
                               bingx_testnet=True, bingx_order_placement_enabled=True),
    )
    service = BrokerExecutionService(
        settings, broker_type="bingx", broker_adapter=broker, guard_instance=guard,
        ledger_instance=ledger, pending_orders_state=pending,
        symbol_validator_instance=SimpleNamespace(is_symbol_approved=lambda _: True),
        forensic_sink=forensic,
        notification_callback=lambda order, order_id: notifications.append(order_id),
        clock=clock,
    )
    order = Order(
        symbol=Symbol("BTCUSDT"), side=OrderSide.BUY, quantity=Decimal("1"),
        price=Money(Decimal("100"), "USDT"),
        stop_loss_price=Money(Decimal("95"), "USDT"),
        take_profit_price=Money(Decimal("110"), "USDT"),
    )
    assert service.execute_order(order) == "REPLAY-00000001"
    assert len(risk_calls) >= 1
    assert list(broker.orders) == ["REPLAY-00000001"]
    assert [kind for kind, _ in ledger.records] == ["decision", "result"]
    assert notifications == ["REPLAY-00000001"]
    assert forensic_records[0]["timestamp"] == T
    assert pending.get_pending_orders_for_symbol(order.symbol) == []


def test_scoped_order_service_rejects_missing_risk_enforcer():
    with pytest.raises(ValueError, match="Risk enforcer"):
        BrokerExecutionService(
            SimpleNamespace(), broker_type="bingx",
            broker_adapter=SimulatedBrokerAdapter(),
            guard_instance=LiveExecutionGuard(breaker_lookup=lambda _: None),
            ledger_instance=Ledger(), pending_orders_state=PendingOrdersState(),
            symbol_validator_instance=object(), forensic_sink=object(),
            notification_callback=lambda *args: None,
            clock=ReplayClock(T),
        )
