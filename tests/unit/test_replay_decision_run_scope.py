"""The partial canonical decision scope owns mutable state and no broker."""

import socket
from datetime import datetime, timezone
from decimal import Decimal

from domain.entities import MarketObservation
from domain.value_objects import Percentage, Symbol
from infrastructure.messaging.event_system import EventType, event_router
from infrastructure.replay.decision_run_scope import ReplayDecisionRunScope


T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def observation():
    return MarketObservation(
        symbol=Symbol("BTCUSDT"), observation_type="trend_bullish",
        observation_value=0.2, confidence=Percentage(Decimal("0.8")),
        timestamp=T, market_price=100.0,
        metadata={"watcher_name": "TrendMTFWatcher"},
    )


def test_two_decision_scopes_have_distinct_state_and_no_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *args: (_ for _ in ()).throw(
        AssertionError("network reached")))
    live_count = len(event_router.subscribers.get(EventType.MARKET_OBSERVATION, []))
    a = ReplayDecisionRunScope(T)
    b = ReplayDecisionRunScope(T)
    try:
        for field in ("clock", "router", "risk_manager", "engine", "fusion",
                      "hierarchical_fusion", "strategies", "aggregator", "processor",
                      "architecture", "trade_tracker", "trace_sink"):
            assert getattr(a, field) is not getattr(b, field), field
        assert a.architecture.execution_service is None
        assert b.architecture.execution_service is None
        assert a.router.router_thread is None
        assert b.router.router_thread is None
        assert len(event_router.subscribers.get(EventType.MARKET_OBSERVATION, [])) == live_count
        a.strategies.strategies[next(iter(a.strategies.strategies))].current_positions["BTCUSDT"] = object()
        assert all(not adapter.current_positions for adapter in b.strategies.strategies.values())
        a.hierarchical_fusion.symbol_manager.process_discovery(Symbol("BTCUSDT"))
        assert b.hierarchical_fusion.symbol_manager.state_machine.get_state(Symbol("BTCUSDT")) is None
        reached = a.process_observation(observation())
        assert reached[0] is EventType.MARKET_OBSERVATION
        assert EventType.INTERPRETED_SIGNAL in reached
        assert a.processor.last_market_data_time("BTCUSDT") == T
        assert b.processor.last_market_data_time("BTCUSDT") is None
        assert a.risk_manager.price_history_for_correlation["BTCUSDT"] == [100.0]
        assert b.risk_manager.price_history_for_correlation == {}
    finally:
        a.close()
        b.close()


def test_repeated_fresh_decision_scope_reaches_same_event_types():
    traces = []
    for _ in range(2):
        scope = ReplayDecisionRunScope(T)
        try:
            traces.append(tuple(event.value for event in scope.process_observation(observation())))
        finally:
            scope.close()
    assert traces[0] == traces[1]
