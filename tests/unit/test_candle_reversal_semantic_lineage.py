"""Current semantic behavior only; these tests do not propose a mapping."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from domain.entities import MarketObservation, SignalType
from domain.value_objects import Percentage, Symbol
from infrastructure.engines.engine_service import EngineService
from infrastructure.fusion.hierarchical.conflict_resolution import ConflictResolutionRules
from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter
from infrastructure.watchers.monitoring_analysis_service import MonitoringAnalysisService


def test_current_engine_does_not_interpret_candle_reversal_as_a_side():
    observation = MarketObservation(
        symbol=Symbol("BTCUSDT"),
        observation_type="candle_reversal_bullish_emerging",
        observation_value=0.25,
        confidence=Percentage(Decimal("0.5")),
        timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    signal = EngineService().process_observation(observation)
    assert signal.signal_type is SignalType.NEUTRAL
    assert signal.direction > 0  # Numeric direction alone is not a BUY decision.


def test_current_live_monitoring_shape_does_not_fill_candle_watcher_buffer():
    settings = SimpleNamespace(watcher=SimpleNamespace(historical_candle_watcher_enabled=True))
    watcher = HistoricalCandleWatcherAdapter(settings, "HistoricalCandle", "BTCUSDT")
    flat = MonitoringAnalysisService()._format_market_data_for_watcher({
        "open": 100.0, "high": 103.0, "low": 99.0,
        "close": 102.0, "volume": 10.0,
        "timestamp": datetime(2026, 6, 1, tzinfo=timezone.utc),
    })
    assert "candle" not in flat
    watcher.update_data(flat)
    assert watcher.candles == []
    assert watcher.analyze(Symbol("BTCUSDT")) is None
    watcher.update_data({"candle": {**flat, "close_time": flat["timestamp"]}})
    assert len(watcher.candles) == 1


def test_hierarchical_direction_requires_two_aligned_observations():
    observation = MarketObservation(
        symbol=Symbol("BTCUSDT"),
        observation_type="candle_reversal_bullish_emerging",
        observation_value=0.25,
        confidence=Percentage(Decimal("0.8")),
        timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    item = {"observation": observation, "watcher_name": "historical_candle"}
    one = ConflictResolutionRules._resolve_direction_conflicts([item], "RISK_ON")
    other = {"observation": observation, "watcher_name": "trend_mtf"}
    two = ConflictResolutionRules._resolve_direction_conflicts([item, other], "RISK_ON")
    assert one["has_direction"] is False
    assert one["reason"] == "insufficient_aligned_direction_signals"
    assert two["has_direction"] is True
    assert two["direction"] == "BUY"
