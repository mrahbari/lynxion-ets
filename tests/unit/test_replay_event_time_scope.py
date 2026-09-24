from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from domain.entities import FusedSignal, MarketObservation, SignalType
from domain.value_objects import Percentage, Symbol
from infrastructure.aggregators.signal_aggregator import SignalAggregator
from infrastructure.messaging.clock import ReplayClock
from infrastructure.messaging.event_system import EventRouter, EventType, SignalEvent
from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter


T = datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc)


def fused(symbol, timestamp=T):
    return FusedSignal(Symbol(symbol), SignalType.BUY, 0.5, 0.8, "normal",
                       Percentage(Decimal("0.8")), timestamp)


def scope():
    router = EventRouter()
    clock = ReplayClock(T)
    selector = SimpleNamespace(evaluate_fused_signal=lambda _: None)
    aggregator = SignalAggregator(router=router, clock=clock, strategy_selector=selector,
                                  synchronous=True, max_signals_to_evaluate=2)
    selected = []
    aggregator._generate_execution_intent = lambda signal: selected.append(signal.symbol.value)
    return router, aggregator, selected


def test_historical_observation_and_router_preserve_source_time():
    settings = SimpleNamespace(watcher=SimpleNamespace(historical_candle_watcher_enabled=True))
    watcher = HistoricalCandleWatcherAdapter(settings, "HistoricalCandle", "BTCUSDT")
    watcher.update_data({"candle": {"open": 100, "high": 102, "low": 99,
                                    "close": 101, "volume": 10, "close_time": T}})
    observation = watcher.analyze(Symbol("BTCUSDT"))
    assert observation.timestamp == T
    router = EventRouter()
    router.publish_observation(observation)
    assert router.event_queue.get_nowait().timestamp == T


def test_aggregator_same_event_time_same_selection_without_thread():
    outputs = []
    for _ in range(2):
        router, aggregator, selected = scope()
        router._route_event(SignalEvent(EventType.FUSED_SIGNAL, fused("BTCUSDT"), timestamp=T))
        assert selected == []
        router._route_event(SignalEvent(EventType.FUSED_SIGNAL, fused("ETHUSDT"), timestamp=T))
        assert len(selected) == 2
        assert aggregator.collected_signals == []
        outputs.append(tuple(selected))
    assert outputs[0] == outputs[1]


def test_two_scopes_have_isolated_candidates_and_subscriptions():
    router_a, aggregator_a, selected_a = scope()
    router_b, aggregator_b, selected_b = scope()
    assert len(router_a.subscribers[EventType.FUSED_SIGNAL]) == 1
    assert len(router_b.subscribers[EventType.FUSED_SIGNAL]) == 1
    router_a._route_event(SignalEvent(EventType.FUSED_SIGNAL, fused("BTCUSDT"), timestamp=T))
    assert len(aggregator_a.collected_signals) == 1
    assert aggregator_b.collected_signals == []
    assert selected_b == []
    assert selected_a == []


def test_replay_clock_monotonic():
    clock = ReplayClock(T)
    clock.advance(T + timedelta(minutes=15))
    assert clock.now() == T + timedelta(minutes=15)
