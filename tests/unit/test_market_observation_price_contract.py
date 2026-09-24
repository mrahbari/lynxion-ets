from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domain.entities import MarketObservation
from domain.value_objects import Percentage, Symbol
from infrastructure.messaging.event_system import EventRouter, EventType, SignalEvent, SignalProcessor


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class Recorder:
    def __init__(self):
        self.calls = []

    def record_price(self, symbol, price):
        self.calls.append((symbol, price))


def observation(value=0.15, market_price=None):
    return MarketObservation(
        symbol=Symbol("BTCUSDT"), observation_type="funding_rate", observation_value=value,
        confidence=Percentage(Decimal("0.7")), timestamp=NOW, market_price=market_price,
    )


def process(obs, recorder):
    processor = SignalProcessor(EventRouter(), price_recorder=recorder)
    seen = []
    engine = SimpleNamespace(process_observation=lambda item: seen.append(item) or None)
    processor._process_observation(SignalEvent(EventType.MARKET_OBSERVATION, obs, timestamp=NOW), engine)
    return seen


def test_legacy_constructor_and_analytical_value_are_not_price():
    obs = observation(value=-0.02)
    recorder = Recorder()
    assert obs.market_price is None
    assert process(obs, recorder) == [obs]
    assert recorder.calls == []


def test_explicit_causal_price_forwarded_once_without_container_lookup(monkeypatch):
    from application.containers.container import container

    monkeypatch.setattr(container, "resolve", lambda name: (_ for _ in ()).throw(AssertionError("global lookup")))
    recorder = Recorder()
    obs = observation(value=-0.02, market_price=123.45)
    assert process(obs, recorder) == [obs]
    assert recorder.calls == [("BTCUSDT", 123.45)]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0, 0.0, "not-a-number", True])
def test_invalid_price_not_forwarded_but_analysis_continues(bad, caplog):
    recorder = Recorder()
    obs = observation(market_price=bad)
    assert process(obs, recorder) == [obs]
    assert recorder.calls == []
    assert "Skipping invalid market_price" in caplog.text


def test_default_live_adapter_targets_same_bridged_risk_instance(monkeypatch):
    from application.containers.container import container

    manager = Recorder()
    bridge = SimpleNamespace(_risk_manager=manager)
    monkeypatch.setitem(container._services, "risk_engine", bridge)
    obs = observation(market_price=100.0)
    assert process(obs, SignalProcessor(EventRouter())._price_recorder) == [obs]
    assert manager.calls == [("BTCUSDT", 100.0)]


def test_recorder_failure_is_visible_and_analysis_still_runs(caplog):
    class BrokenRecorder:
        def record_price(self, symbol, price):
            raise RuntimeError("recorder failed")

    obs = observation(market_price=100.0)
    assert process(obs, BrokenRecorder()) == [obs]
    assert "Market price recording failed" in caplog.text


def test_price_is_stored_per_observation_not_recomputed_from_later_data():
    first = observation(market_price=100.0)
    future = observation(market_price=120.0)
    assert first.market_price == 100.0
    recorder = Recorder()
    process(first, recorder)
    process(future, recorder)
    assert recorder.calls == [("BTCUSDT", 100.0), ("BTCUSDT", 120.0)]
    assert first.market_price == 100.0


def test_tick_producer_uses_received_tick_price_and_keeps_prior_snapshot():
    from infrastructure.watchers.adapters.tick import TickWatcherAdapter

    watcher = TickWatcherAdapter(
        "TickWatcher", "BTCUSDT", watcher_config=SimpleNamespace(tick_watcher_enabled=True),
    )
    for idx in range(10):
        watcher.update_data({"tick": {"price": 100.0 + idx, "volume": 1.0}})
    first = watcher.analyze(Symbol("BTCUSDT"))
    assert first.market_price == 109.0
    watcher.update_data({"tick": {"price": 200.0, "volume": 1.0}})
    second = watcher.analyze(Symbol("BTCUSDT"))
    assert second.market_price == 200.0
    assert first.market_price == 109.0
