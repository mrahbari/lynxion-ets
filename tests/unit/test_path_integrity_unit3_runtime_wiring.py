"""Production auto-detect factory wiring with network-incapable injected ports."""

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from application.containers.container import container as legacy_container
from bootstrap.container import Container
from bootstrap.settings.loaders import load_settings
from domain.entities import ExecutionIntent
from domain.enums.order_side import OrderSide
from domain.value_objects import Percentage, Symbol
from infrastructure.messaging.event_system import EventType, SignalEvent


class NoNetworkExecution:
    is_backtest = True

    def __init__(self):
        self.orders = []
        self.guard_decisions = []
        self.broker_dispatches = 0

    def get_current_price(self, symbol):
        return 100.0

    def execute_order(self, order):
        from shared.live_execution_guard import live_execution_guard

        self.orders.append(order)
        settings = SimpleNamespace(broker=SimpleNamespace(
            paper_trading=False, testnet=True,
            bingx_order_placement_enabled=True, bingx_testnet=True,
        ))
        decision, _ = live_execution_guard.authorize_and_send(
            "bingx", settings, order, self._fake_broker_dispatch,
            ledger=SimpleNamespace(new_order_ref=lambda: "unit3-memory-only",
                                   append=lambda *args: None),
        )
        self.guard_decisions.append(decision)
        return None

    def _fake_broker_dispatch(self):
        self.broker_dispatches += 1
        return "offline-no-broker"


class NoNetworkRegistry:
    def __init__(self, service):
        self.service = service

    def get_execution_service(self, **kwargs):
        return self.service

    def get_historical_data_provider(self, **kwargs):
        return SimpleNamespace(get_current_price=lambda symbol: 100.0)


def _intent(side):
    return ExecutionIntent(
        symbol=Symbol("BTCUSDT"), strategy_name="UNIT3_OFFLINE", side=side,
        intent_confidence=Percentage(Decimal("1")),
        risk_parameters={"stop_loss": 95.0 if side == OrderSide.BUY else 105.0,
                         "take_profit": 110.0 if side == OrderSide.BUY else 90.0},
        timestamp=datetime.now(),
    )


@pytest.mark.unit
@pytest.mark.parametrize("side", [OrderSide.BUY, OrderSide.SELL])
@pytest.mark.parametrize("scenario", ["normal", "duplicate", "concurrent", "cooldown", "risk_reject", "wrong_side_sltp", "notional_cap", "active_order", "guard_reject", "inverse_sizing"])
def test_production_auto_factory_has_one_execution_subscriber_no_network(monkeypatch, side, scenario):
    from infrastructure.messaging.event_system import event_router, signal_processor
    from infrastructure.orchestrators.architecture_orchestrator import architecture_orchestrator
    from infrastructure.aggregators.signal_aggregator import signal_aggregator
    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
    from infrastructure.risk.risk_enforcement import RiskEnforcement
    import shared.live_execution_guard as guard_module
    from shared.live_execution_guard import LiveExecutionGuard
    import infrastructure.execution.paper_trading_engine as paper_module
    import infrastructure.watchers.market_opportunity_watcher as watcher_module
    import infrastructure.observability.forward_exit_runtime as forward_module

    spy = NoNetworkExecution()
    guard = LiveExecutionGuard()
    monkeypatch.setattr(guard_module, "live_execution_guard", guard)
    settings = load_settings()
    composition = Container(settings)
    composition.register("broker_registry", lambda: NoNetworkRegistry(spy))
    monkeypatch.setattr(RiskEnforcement, "_load_cooldown_journal", lambda self: {})
    monkeypatch.setattr(paper_module, "PaperTradingEngine", lambda **kwargs: SimpleNamespace(simulate_fill=lambda order: {}))
    monkeypatch.setattr(watcher_module, "MarketOpportunityWatcher", lambda **kwargs: SimpleNamespace(symbols=[Symbol("BTCUSDT")]))
    monkeypatch.setattr(forward_module, "build_forward_exit_runtime_bundle", lambda: None)
    monkeypatch.setattr(signal_aggregator, "start_aggregation", lambda: None)
    monkeypatch.setattr(symbol_cooldown_gate, "is_symbol_allowed", lambda symbol, **kwargs: (True, "offline"))
    monkeypatch.delenv("MAX_ORDER_NOTIONAL_AMOUNT", raising=False)
    if scenario == "notional_cap":
        monkeypatch.setenv("MAX_ORDER_NOTIONAL_AMOUNT", "5")

    old_subscribers = event_router.subscribers
    old_setup = signal_processor._processing_subscribed
    old_running = architecture_orchestrator.is_running
    old_service = architecture_orchestrator.execution_service
    old_risk = legacy_container._services.get("risk_engine")
    event_router.subscribers = {}
    signal_processor._processing_subscribed = False
    architecture_orchestrator.is_running = False
    risk = MagicMock()
    risk._risk_manager.positions = {}
    risk._risk_manager.starting_equity = 10000.0
    risk._risk_manager.total_pnl = 0.0
    if scenario == "inverse_sizing":
        risk.calculate_dynamic_size.side_effect = [0.1, 0.05]
    else:
        risk.calculate_dynamic_size.return_value = 0.1
    legacy_container.register("risk_engine", risk, singleton=True)
    try:
        auto = composition.resolve("auto_detection_orchestrator_factory")(
            ["BTCUSDT"], {"max_risk": 0.02}, False)
        if scenario == "risk_reject":
            monkeypatch.setattr(composition.risk_enforcement()._rm, "is_trading_allowed", lambda: False)
        auto.is_running = True  # no background runner/watchers started
        if scenario == "active_order":
            spy.broker = SimpleNamespace(get_open_orders=lambda symbol: ["existing-offline-order"])
        auto._check_duplicate_execution_intent = lambda intent: False
        auto._remove_pending_execution_intent = lambda intent: None
        auto._stablecoin_filter_config = lambda: (False, ())

        subscribers = event_router.subscribers[EventType.EXECUTION_INTENT]
        assert len(subscribers) == 1
        assert subscribers[0].__self__ is auto
        assert subscribers[0].__name__ == "_handle_execution_intent_event"

        intent = _intent(side)
        if scenario == "wrong_side_sltp":
            intent.risk_parameters["stop_loss"] = 105.0 if side == OrderSide.BUY else 95.0
        if scenario == "guard_reject":
            guard.engage_kill_switch("unit3 offline guard veto")
        event = SignalEvent(EventType.EXECUTION_INTENT, intent, correlation_id=intent.intent_id)
        event_router._route_event(event)
        if scenario == "active_order":
            assert auto.opportunity_queue == []
            assert spy.orders == []
            assert spy.broker_dispatches == 0
            return
        if scenario == "duplicate":
            event_router._route_event(event)
            assert len(auto.opportunity_queue) == 2
        else:
            assert len(auto.opportunity_queue) == 1
        assert spy.orders == []
        if scenario == "cooldown":
            monkeypatch.setattr(symbol_cooldown_gate, "is_symbol_allowed", lambda symbol, **kwargs: (False, "offline cooldown"))
        if scenario == "concurrent":
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(auto._execute_trade_from_intent, [intent, intent]))
        else:
            auto._execute_trade_from_intent(auto.opportunity_queue.pop(0))
        if scenario == "duplicate":
            auto._execute_trade_from_intent(auto.opportunity_queue.pop(0))
        if scenario == "inverse_sizing":
            farther = _intent(side)
            farther.risk_parameters["stop_loss"] = 90.0 if side == OrderSide.BUY else 110.0
            event_router._route_event(SignalEvent(EventType.EXECUTION_INTENT, farther, correlation_id=farther.intent_id))
            auto._execute_trade_from_intent(auto.opportunity_queue.pop(0))
            assert [float(order.quantity) for order in spy.orders] == pytest.approx([0.1, 0.05])
            assert spy.broker_dispatches == 2  # two distinct intents, memory-only callbacks
            return
        if scenario == "cooldown":
            assert spy.orders == []
            assert spy.broker_dispatches == 0
            return
        assert len(spy.orders) == 1
        assert len(spy.guard_decisions) == 1
        if scenario in ("risk_reject", "guard_reject"):
            assert not spy.guard_decisions[0].allowed
            assert spy.broker_dispatches == 0
        else:
            assert spy.guard_decisions[0].allowed, spy.guard_decisions[0].reason
            assert spy.broker_dispatches == 1  # memory-only callback, never a broker
        if scenario == "notional_cap":
            assert float(spy.orders[0].quantity) == pytest.approx(0.05)
        if scenario == "wrong_side_sltp":
            stop = float(spy.orders[0].stop_loss_price.amount)
            assert stop < 100 if side == OrderSide.BUY else stop > 100
        assert composition.risk_enforcement() is not None
        assert spy.orders[0].parent_execution_intent.intent_id == intent.intent_id
        assert risk.calculate_dynamic_size.call_count == 1
    finally:
        event_router.subscribers = old_subscribers
        signal_processor._processing_subscribed = old_setup
        architecture_orchestrator.is_running = old_running
        architecture_orchestrator.execution_service = old_service
        if old_risk is None:
            legacy_container._services.pop("risk_engine", None)
        else:
            legacy_container._services["risk_engine"] = old_risk
