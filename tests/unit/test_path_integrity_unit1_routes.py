"""Offline route trace: the execution spy has no broker or network capability."""

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
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
@pytest.mark.parametrize("scenario", ["normal", "duplicate_delivery", "queue_redelivery", "cooldown_blocked", "concurrent_delivery", "notional_cap", "inverse_sizing"])
def test_execution_route_variants_with_no_network_broker(monkeypatch, side, scenario):
    from infrastructure.messaging import event_system
    from infrastructure.orchestrators.architecture_orchestrator import architecture_orchestrator
    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate

    monkeypatch.delenv("MAX_ORDER_NOTIONAL_AMOUNT", raising=False)

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
    if scenario == "inverse_sizing":
        risk.calculate_dynamic_size.side_effect = [20.0, 10.0]
    else:
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
            risk=SimpleNamespace(max_leverage=2.0, max_order_notional_amount=50.0 if scenario == "notional_cap" else None),
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
        assert len(spy.orders) == 0  # direct subscriber no longer owns execution
        if scenario == "duplicate_delivery":
            router._route_event(event)
            assert len(auto.opportunity_queue) == 1  # auto-detection dedup works
            assert len(spy.orders) == 0
        if scenario == "cooldown_blocked":
            monkeypatch.setattr(symbol_cooldown_gate, "is_symbol_allowed", lambda symbol: (False, "offline cooldown"))
        if scenario == "concurrent_delivery":
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(auto._execute_trade_from_intent, [intent, intent]))
            assert sum(result.get("error") == "DUPLICATE_LOGICAL_INTENT" for result in results) == 1
        elif scenario == "inverse_sizing":
            auto._execute_trade_from_intent(auto.opportunity_queue.pop(0))
            farther = make_intent(side)
            farther.risk_parameters["stop_loss"] = 90.0 if side == OrderSide.BUY else 110.0
            router._route_event(SignalEvent(EventType.EXECUTION_INTENT, farther, correlation_id="unit1-second-intent"))
            auto._execute_trade_from_intent(auto.opportunity_queue.pop(0))
            assert [float(order.quantity) for order in spy.orders] == pytest.approx([20.0, 10.0])
        else:
            auto._execute_trade_from_intent(auto.opportunity_queue.pop(0))
            if scenario == "queue_redelivery":
                assert auto._execute_trade_from_intent(intent)["error"] == "DUPLICATE_LOGICAL_INTENT"
        expected = {"normal": 1, "duplicate_delivery": 1, "cooldown_blocked": 0,
                    "concurrent_delivery": 1, "notional_cap": 1, "inverse_sizing": 2,
                    "queue_redelivery": 1}[scenario]
        assert len(spy.orders) == expected
        assert all(order.parent_execution_intent is intent for order in spy.orders[:1])
        if scenario == "notional_cap":
            order = spy.orders[0]
            assert float(order.quantity) == pytest.approx(0.5)
            assert float(order.stop_loss_price.amount) == pytest.approx(97.0 if side == OrderSide.BUY else 103.0)
            assert float(order.take_profit_price.amount) == pytest.approx(105.5 if side == OrderSide.BUY else 94.5)
        assert risk.calculate_dynamic_size.call_count == expected
    finally:
        if original is None:
            container._services.pop("risk_engine", None)
        else:
            container._services["risk_engine"] = original


@pytest.mark.unit
def test_signal_processor_registration_is_idempotent_and_non_executing():
    router = EventRouter()
    processor = SignalProcessor(router)
    service = PreBrokerSpy()
    processor.setup_signal_processing(None, None, None, service)
    processor.setup_signal_processing(None, None, None, service)
    assert EventType.EXECUTION_INTENT not in router.subscribers
    assert len(router.subscribers[EventType.MARKET_OBSERVATION]) == 1
