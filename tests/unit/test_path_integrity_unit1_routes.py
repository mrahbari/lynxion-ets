"""Offline route trace: the execution spy has no broker or network capability."""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from application.containers.container import container
from domain.entities import ExecutionIntent
from domain.enums.order_side import OrderSide
from domain.value_objects import Percentage, Symbol
from infrastructure.messaging.event_system import EventRouter, EventType, SignalEvent, SignalProcessor
from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator


class PreBrokerSpy:
    is_backtest = True

    def __init__(self):
        self.orders = []

    def get_current_price(self, symbol):
        return 100.0

    def execute_order(self, order):
        self.orders.append(order)
        return None


def make_intent(side):
    return ExecutionIntent(
        symbol=Symbol("BTCUSDT"), strategy_name="UNIT1_OFFLINE",
        side=side, intent_confidence=Percentage(Decimal("1")),
        risk_parameters={"limit_price": 100.0,
                         "stop_loss": 95.0 if side == OrderSide.BUY else 105.0,
                         "take_profit": 110.0 if side == OrderSide.BUY else 90.0},
        timestamp=datetime.now(),
    )


@pytest.mark.unit
@pytest.mark.parametrize("side", [OrderSide.BUY, OrderSide.SELL])
@pytest.mark.parametrize("scenario", ["normal", "duplicate_delivery", "cooldown_blocked"])
def test_execution_route_variants_with_no_network_broker(monkeypatch, side, scenario):
    from infrastructure.messaging import event_system
    from infrastructure.orchestrators.architecture_orchestrator import architecture_orchestrator
    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate

    spy = PreBrokerSpy()
    router = EventRouter()
    processor = SignalProcessor(router)
    processor.logger = MagicMock()
    processor.setup_signal_processing(None, None, None, spy)
    monkeypatch.setattr(architecture_orchestrator, "execution_service", None)
    monkeypatch.setattr(event_system, "load_settings", lambda: SimpleNamespace(
        position_sizing=SimpleNamespace(fixed_position_size_enabled=False),
        risk=SimpleNamespace(max_order_notional_amount=None, max_leverage=2.0),
    ))
    monkeypatch.setattr(symbol_cooldown_gate, "is_symbol_allowed", lambda symbol: (True, "ok"))
    risk = MagicMock()
    risk._risk_manager.positions = {}
    risk._risk_manager.starting_equity = 10000.0
    risk._risk_manager.total_pnl = 0.0
    risk.calculate_dynamic_size.return_value = 1.0
    original = container._services.get("risk_engine")
    container.register("risk_engine", risk, singleton=True)
    try:
        auto = object.__new__(AutoDetectionOrchestrator)
        auto.logger = MagicMock()
        auto.is_running = True
        auto.execution_service = spy
        auto.market_data_repo = SimpleNamespace(get_current_price=lambda symbol: 100.0)
        auto._settings = SimpleNamespace(
            position_sizing=SimpleNamespace(fixed_position_size_enabled=False),
            risk=SimpleNamespace(max_leverage=2.0),
            execution=SimpleNamespace(prevent_same_direction_trade_per_symbol=False),
        )
        auto.opportunity_queue = []
        auto._calculate_opportunity_score = lambda intent: 1.0
        auto._check_broker_active_orders_for_duplicate = lambda intent: True
        seen = set()

        def dedup(candidate):
            key = id(candidate)
            if key in seen:
                return True
            seen.add(key)
            return False

        auto._check_duplicate_execution_intent = dedup
        auto._stablecoin_filter_config = lambda: (False, ())
        auto._remove_pending_execution_intent = lambda intent: None
        router.subscribe(EventType.EXECUTION_INTENT, auto._handle_execution_intent_event)

        intent = make_intent(side)
        event = SignalEvent(EventType.EXECUTION_INTENT, intent, correlation_id="unit1-one-intent")
        router._route_event(event)
        assert len(auto.opportunity_queue) == 1
        assert len(spy.orders) == 1  # synchronous SignalProcessor subscriber
        if scenario == "duplicate_delivery":
            router._route_event(event)
            assert len(auto.opportunity_queue) == 1  # auto-detection dedup works
            assert len(spy.orders) == 2  # SignalProcessor has no matching intent-id dedup
        if scenario == "cooldown_blocked":
            monkeypatch.setattr(symbol_cooldown_gate, "is_symbol_allowed", lambda symbol: (False, "offline cooldown"))
        auto._execute_trade_from_intent(auto.opportunity_queue.pop(0))
        expected = {"normal": 2, "duplicate_delivery": 3, "cooldown_blocked": 1}[scenario]
        assert len(spy.orders) == expected
        assert all(order.parent_execution_intent is intent for order in spy.orders)
        assert risk.calculate_dynamic_size.call_count == expected
    finally:
        if original is None:
            container._services.pop("risk_engine", None)
        else:
            container._services["risk_engine"] = original
