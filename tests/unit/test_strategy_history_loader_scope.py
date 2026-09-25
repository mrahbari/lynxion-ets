"""Explicit research history cannot fall through to the live broker registry."""

from types import SimpleNamespace

from domain.value_objects import Symbol
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


def test_explicit_empty_history_is_fail_closed_against_live_registry(monkeypatch):
    from infrastructure.services import broker_registry as registry_module

    def forbidden(*args, **kwargs):
        raise AssertionError("global broker registry reached")

    monkeypatch.setattr(registry_module.broker_registry,
                        "get_historical_data_provider", forbidden)
    adapter = BaseStrategyAdapter("TrendFollow")
    calls = []
    adapter.bind_history_loader(lambda symbol, config: calls.append(
        (symbol.value, config["timeframe"])) or [])
    adapter.ensure_data_buffer(Symbol("BTCUSDT"))
    assert calls == [("BTCUSDT", adapter.config["timeframe"])]
    assert adapter.data_buffer == []


def test_omitted_loader_keeps_default_live_registry_path(monkeypatch):
    from infrastructure.services import broker_registry as registry_module

    calls = []
    provider = SimpleNamespace(get_historical_data=lambda *args, **kwargs: [
        {"close": 100.0, "high": 101.0, "low": 99.0, "volume": 1.0}
    ])
    monkeypatch.setattr(registry_module.broker_registry,
                        "get_historical_data_provider",
                        lambda **kwargs: calls.append(kwargs) or provider)
    adapter = BaseStrategyAdapter("TrendFollow")
    adapter.ensure_data_buffer(Symbol("BTCUSDT"))
    assert len(calls) == 1
    assert calls[0]["download_enabled"] is True
    assert adapter.data_buffer[0]["close"] == 100.0


def test_replay_decision_scope_binds_every_adapter_to_explicit_history(monkeypatch):
    from datetime import datetime, timezone
    from decimal import Decimal
    from domain.entities import MarketObservation
    from domain.value_objects import Percentage
    from infrastructure.replay.decision_run_scope import ReplayDecisionRunScope
    from infrastructure.services import broker_registry as registry_module

    global_calls = []
    monkeypatch.setattr(registry_module.broker_registry,
                        "get_historical_data_provider",
                        lambda **kwargs: global_calls.append(kwargs) or None)

    event_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scope = ReplayDecisionRunScope(event_time)
    try:
        assert scope.strategies.strategies
        assert all(callable(adapter._history_loader)
                   for adapter in scope.strategies.strategies.values())
        scope.process_observation(MarketObservation(
            symbol=Symbol("BTCUSDT"), observation_type="trend_bullish",
            observation_value=0.2, confidence=Percentage(Decimal("0.8")),
            timestamp=event_time, market_price=100.0,
            metadata={"watcher_name": "TrendMTFWatcher"},
        ))
        assert global_calls == []
    finally:
        scope.close()
