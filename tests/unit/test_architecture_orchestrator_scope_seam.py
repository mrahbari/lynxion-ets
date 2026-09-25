"""Explicit orchestration bindings do not subscribe the live router."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from infrastructure.aggregators.signal_aggregator import signal_aggregator
from infrastructure.messaging.event_system import (
    EventRouter, EventType, SignalEvent, SignalProcessor, event_router, signal_processor,
)
from infrastructure.orchestrators.architecture_orchestrator import ArchitectureOrchestrator


class Recorder:
    def record_price(self, symbol, price):
        raise AssertionError("test observation has no market price")


class Engine:
    def __init__(self):
        self.seen = []

    def process_observation(self, observation):
        self.seen.append(observation.symbol.value)
        return None


def test_default_orchestrator_bindings_keep_live_instances():
    orchestrator = ArchitectureOrchestrator(
        engine_service=Engine(), fusion_service=object(),
        strategy_manager=object(), execution_service=None,
    )
    assert orchestrator.event_router is event_router
    assert orchestrator.signal_processor is signal_processor
    assert orchestrator.signal_aggregator is signal_aggregator


def test_explicit_processor_subscribes_only_its_router():
    live_count = len(event_router.subscribers.get(EventType.MARKET_OBSERVATION, []))
    router_a, router_b = EventRouter(), EventRouter()
    engine_a, engine_b = Engine(), Engine()
    for router, engine in ((router_a, engine_a), (router_b, engine_b)):
        processor = SignalProcessor(router, forensic_sink=object(), price_recorder=Recorder())
        orchestrator = ArchitectureOrchestrator(
            engine_service=engine, fusion_service=object(),
            strategy_manager=object(), event_router=router,
            signal_processor_instance=processor,
            signal_aggregator_instance=object(),
        )
        assert orchestrator.signal_processor is processor
        assert len(router.subscribers[EventType.MARKET_OBSERVATION]) == 1

    observation = SimpleNamespace(
        symbol=SimpleNamespace(value="BTCUSDT"), market_price=None,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    router_a._route_event(SignalEvent(EventType.MARKET_OBSERVATION, observation,
                                      timestamp=observation.timestamp))
    assert engine_a.seen == ["BTCUSDT"]
    assert engine_b.seen == []
    assert len(event_router.subscribers.get(EventType.MARKET_OBSERVATION, [])) == live_count


def test_explicit_processor_cannot_bind_a_different_router():
    processor = SignalProcessor(EventRouter(), forensic_sink=object(), price_recorder=Recorder())
    with pytest.raises(ValueError, match="same EventRouter"):
        ArchitectureOrchestrator(
            engine_service=Engine(), fusion_service=object(), strategy_manager=object(),
            event_router=EventRouter(), signal_processor_instance=processor,
            signal_aggregator_instance=object(),
        )
