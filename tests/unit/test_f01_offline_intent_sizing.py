"""F01: pre-broker sizing characterization; fake execution service only."""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from application.containers.container import container
from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
from domain.entities import ExecutionIntent
from domain.enums.order_side import OrderSide
from domain.value_objects import Money, Percentage, Symbol
from infrastructure.messaging.event_system import SignalProcessor
from infrastructure.risk.risk_engine_adapter import ConsolidatedRiskEngineAdapter


class CaptureOnlyExecution:
    is_backtest = True  # disables live heartbeat; never calls a broker

    def __init__(self):
        self.orders = []

    def get_current_price(self, symbol):
        return 100.0

    def execute_order(self, order):
        self.orders.append(order)
        return None


def _intent(side, stop):
    return ExecutionIntent(
        symbol=Symbol("BTCUSDT"), strategy_name="F01_OFFLINE",
        side=side, intent_confidence=Percentage(Decimal("1")),
        risk_parameters={"limit_price": 100.0, "stop_loss": stop,
                         "take_profit": 110.0 if side == OrderSide.BUY else 90.0},
        timestamp=datetime.now(),
    )


@pytest.mark.unit
@pytest.mark.parametrize("side,near,far", [
    (OrderSide.BUY, 95.0, 90.0), (OrderSide.SELL, 105.0, 110.0),
])
def test_f01_dynamic_quantity_reaches_prebroker_order(monkeypatch, side, near, far):
    from infrastructure.messaging import event_system
    from infrastructure.orchestrators.architecture_orchestrator import architecture_orchestrator

    monkeypatch.delenv("MAX_ORDER_NOTIONAL_AMOUNT", raising=False)
    monkeypatch.setattr(architecture_orchestrator, "execution_service", None)
    monkeypatch.setattr(event_system, "load_settings", lambda: SimpleNamespace(
        position_sizing=SimpleNamespace(fixed_position_size_enabled=False),
        risk=SimpleNamespace(max_order_notional_amount=None, max_leverage=2.0),
    ))
    manager = EnterpriseRiskManager(
        max_portfolio_exposure=100000, max_position_exposure=50000,
        max_risk_per_trade=0.01, fixed_position_size_enabled=False,
    )
    manager.starting_equity = 10000.0
    manager.total_pnl = 0.0
    original = container._services.get("risk_engine")
    container.register("risk_engine", ConsolidatedRiskEngineAdapter(manager), singleton=True)
    try:
        processor = SignalProcessor(SimpleNamespace())
        service = CaptureOnlyExecution()
        for stop in (near, far):
            processor._process_execution_intent(SimpleNamespace(data=_intent(side, stop)), service)
        assert len(service.orders) == 2
        quantities = [float(order.quantity) for order in service.orders]
        assert quantities == pytest.approx([20.0, 10.0])
        assert [float(order.quantity) * float(order.price.amount) for order in service.orders] == pytest.approx([2000.0, 1000.0])
        assert all(float(order.requested_leverage) == 2.0 for order in service.orders)
        assert all(order.position_side == ("LONG" if side == OrderSide.BUY else "SHORT") for order in service.orders)
    finally:
        if original is None:
            container._services.pop("risk_engine", None)
        else:
            container._services["risk_engine"] = original


@pytest.mark.unit
@pytest.mark.parametrize("mode,exposure,order_cap,risk_pct,expected", [
    ("dynamic", 1000.0, None, 0.01, [9.9, 9.9]),
    ("dynamic", 50000.0, 500.0, 0.01, [5.0, 5.0]),
    ("fixed", 50000.0, None, 0.01, [4.0, 4.0]),
    ("dynamic", 50000.0, None, 0.0000001, [0.001, 0.001]),
])
def test_f01_caps_fixed_mode_and_minimum(monkeypatch, mode, exposure, order_cap, risk_pct, expected):
    from infrastructure.messaging import event_system
    from infrastructure.orchestrators.architecture_orchestrator import architecture_orchestrator

    monkeypatch.delenv("MAX_ORDER_NOTIONAL_AMOUNT", raising=False)
    monkeypatch.setattr(architecture_orchestrator, "execution_service", None)
    monkeypatch.setattr(event_system, "load_settings", lambda: SimpleNamespace(
        position_sizing=SimpleNamespace(fixed_position_size_enabled=(mode == "fixed"), fixed_position_amount=400),
        risk=SimpleNamespace(max_order_notional_amount=order_cap, max_leverage=2.0),
    ))
    manager = EnterpriseRiskManager(
        max_portfolio_exposure=100000, max_position_exposure=exposure,
        max_risk_per_trade=risk_pct, fixed_position_size_enabled=(mode == "fixed"),
        fixed_position_amount=400.0,
    )
    manager.starting_equity = 10000.0
    manager.total_pnl = 0.0
    original = container._services.get("risk_engine")
    container.register("risk_engine", ConsolidatedRiskEngineAdapter(manager), singleton=True)
    try:
        processor = SignalProcessor(SimpleNamespace())
        service = CaptureOnlyExecution()
        for stop in (95.0, 90.0):
            processor._process_execution_intent(SimpleNamespace(data=_intent(OrderSide.BUY, stop)), service)
        assert len(service.orders) == 2
        assert [float(order.quantity) for order in service.orders] == pytest.approx(expected)
    finally:
        if original is None:
            container._services.pop("risk_engine", None)
        else:
            container._services["risk_engine"] = original
