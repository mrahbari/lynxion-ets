"""The queued execution owner can use explicit per-run Risk dependencies."""

from types import SimpleNamespace
from datetime import datetime, timezone
import threading

from infrastructure.orchestrators._auto_detection_execution import _AutoDetectionExecutionMixin
from infrastructure.orchestrators._auto_detection_dedup import _AutoDetectionDedupMixin


class Owner(_AutoDetectionExecutionMixin):
    pass


class ScopedOwner(_AutoDetectionDedupMixin, _AutoDetectionExecutionMixin):
    pass


def test_execution_and_dedup_use_injected_event_clock():
    event_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    owner = ScopedOwner()
    owner._execution_clock = SimpleNamespace(now=lambda: event_time)
    owner._settings = SimpleNamespace(execution=SimpleNamespace(
        prevent_same_direction_trade_per_symbol=True))
    owner._pending_intents_lock = threading.RLock()
    owner._pending_intents = {}
    owner._pending_intent_temp_ids = {}
    owner._pending_orders_tracker = SimpleNamespace(
        get_pending_orders_for_symbol=lambda symbol: [])
    owner.logger = SimpleNamespace(info=lambda *args: None)
    intent = SimpleNamespace(symbol=SimpleNamespace(value="BTCUSDT"),
                             side=SimpleNamespace(name="BUY"))
    assert owner._execution_now() == event_time
    assert owner._check_duplicate_execution_intent(intent) is False
    assert owner._pending_intents["BTCUSDT"]["BUY"] == event_time


def test_omitted_execution_clock_retains_live_clock(monkeypatch):
    from infrastructure.messaging.clock import LiveClock
    expected = datetime(2026, 1, 1)
    monkeypatch.setattr(LiveClock, "now", lambda self: expected)
    assert Owner()._execution_now() == expected


def test_explicit_auto_detection_constructor_binds_only_scoped_router(monkeypatch):
    from infrastructure.messaging.event_system import EventRouter, EventType, event_router
    from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
    import infrastructure.observability.forward_exit_runtime as forward_runtime

    monkeypatch.setattr(forward_runtime, "build_forward_exit_runtime_bundle", lambda: None)
    live_count = len(event_router.subscribers.get(EventType.EXECUTION_INTENT, []))
    owners = []
    for _ in range(2):
        router = EventRouter()
        architecture = SimpleNamespace(
            engine_service=object(), fusion_service=object(), strategy_manager=object(),
            event_router=router, execution_service=None, starts=0, stops=0,
        )
        architecture.start = lambda architecture=architecture: setattr(
            architecture, "starts", architecture.starts + 1)
        architecture.stop = lambda architecture=architecture: setattr(
            architecture, "stops", architecture.stops + 1)
        watcher = SimpleNamespace(symbols=["BTCUSDT"], stop_monitoring=lambda: None)
        alert = object()
        execution = SimpleNamespace(set_system_running_state=lambda _: None)
        pending = SimpleNamespace(clears=0)
        pending.clear_all_pending_orders = lambda pending=pending: setattr(
            pending, "clears", pending.clears + 1)
        owner = AutoDetectionOrchestrator(
            settings=SimpleNamespace(), market_data_repo=object(),
            execution_service=execution, portfolio_service=object(),
            optimization_service=object(), symbols=["BTCUSDT"],
            architecture_orchestrator_instance=architecture,
            opportunity_watcher_instance=watcher,
            risk_alert_service_instance=alert,
            pending_orders_state=pending,
        )
        assert owner.event_router is router
        assert owner.opportunity_watcher is watcher
        assert owner.risk_alert_service is alert
        assert architecture.execution_service is execution
        assert architecture.starts == 1
        assert router.subscribers[EventType.EXECUTION_INTENT] == [
            owner._handle_execution_intent_event]
        owner.stop_system()
        assert architecture.stops == 1
        assert pending.clears == 1
        owners.append(owner)
    assert owners[0].event_router is not owners[1].event_router
    assert len(event_router.subscribers.get(EventType.EXECUTION_INTENT, [])) == live_count


def test_explicit_risk_and_cooldown_do_not_resolve_live_globals(monkeypatch):
    from application.containers.container import container
    import infrastructure.risk.symbol_cooldown_gate as cooldown_module

    monkeypatch.setattr(container, "resolve", lambda *args: (_ for _ in ()).throw(
        AssertionError("global risk resolved")))
    monkeypatch.setattr(cooldown_module, "symbol_cooldown_gate", None)
    owner = Owner()
    risk = object()
    gate = object()
    owner._risk_engine = risk
    owner._cooldown_gate = gate
    assert owner._get_risk_engine() is risk
    assert owner._get_cooldown_gate() is gate


def test_default_bindings_remain_live_compatibility_paths(monkeypatch):
    from application.containers.container import container
    import infrastructure.risk.symbol_cooldown_gate as cooldown_module

    risk = object()
    gate = object()
    monkeypatch.setattr(container, "resolve", lambda name: risk if name == "risk_engine" else None)
    monkeypatch.setattr(cooldown_module, "symbol_cooldown_gate", gate)
    owner = Owner()
    assert owner._get_risk_engine() is risk
    assert owner._get_cooldown_gate() is gate


def test_execution_cooldown_rejection_uses_injected_gate():
    class Gate:
        def __init__(self):
            self.symbols = []

        def is_symbol_allowed(self, symbol):
            self.symbols.append(symbol.value)
            return False, "offline-block"

    gate = Gate()
    owner = Owner()
    owner.is_running = True
    owner.logger = SimpleNamespace(warning=lambda *a: None, error=lambda *a: None)
    owner._cooldown_gate = gate
    owner._intent_claim_store = SimpleNamespace(claim=lambda _: True)
    owner._settings = SimpleNamespace(execution=SimpleNamespace(
        prevent_same_direction_trade_per_symbol=False))
    owner._check_broker_active_orders_for_duplicate = lambda _: True
    owner._remove_pending_execution_intent = lambda _: None
    owner._stablecoin_filter_config = lambda: (False, set())
    intent = SimpleNamespace(
        intent_id="scoped-risk-unit", symbol=SimpleNamespace(value="BTCUSDT"),
        side=SimpleNamespace(name="BUY"), strategy_name="UNIT",
        intent_confidence=SimpleNamespace(value=1.0),
    )
    result = owner._execute_trade_from_intent(intent)
    assert result["status"] == "failed"
    assert "offline-block" in result["error"]
    assert gate.symbols == ["BTCUSDT"]
