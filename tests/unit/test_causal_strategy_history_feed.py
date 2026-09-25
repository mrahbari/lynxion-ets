"""Point-in-time strategy buffers use actual completed timeframe bars only."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest

from infrastructure.replay.causal_strategy_history import CausalStrategyHistoryFeed
from infrastructure.replay.closed_bar_decision_driver import ClosedBarDecisionDriver
from infrastructure.replay.historical_closed_bar_source import ClosedBar, HistoricalClosedBarSource
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)


def bar(opened, timeframe, close, symbol="BTCUSDT"):
    return ClosedBar(symbol, timeframe, opened, opened + timeframe,
                     close - 1, close + 1, close - 2, close, 10.0)


def adapters():
    short = BaseStrategyAdapter("SweepScalper")
    long = BaseStrategyAdapter("TrendFollow")
    short.config["timeframe"] = "1m"
    long.config["timeframe"] = "1h"
    return short, long


def test_driver_feeds_only_causal_matching_bars_before_same_time_decisions():
    short, long = adapters()
    manager = SimpleNamespace(strategies={"short": short, "long": long})
    history = CausalStrategyHistoryFeed(manager, "BTCUSDT")
    minute_at_hour = bar(T0 + 59 * MINUTE, MINUTE, 101.0)
    hour_at_hour = bar(T0, HOUR, 102.0)
    future = bar(T0 + HOUR, MINUTE, 103.0)
    seen = []
    scope = SimpleNamespace(process_observation=lambda observation:
                            seen.append((observation.timestamp,
                                         tuple(item["close"] for item in short.data_buffer),
                                         tuple(item["close"] for item in long.data_buffer))) or ())
    settings = SimpleNamespace(watcher=SimpleNamespace(historical_candle_watcher_enabled=True))
    # Separate source streams may have gaps; this fixture uses only the same
    # close boundary plus its contiguous next minute for the 1m stream.
    source = HistoricalClosedBarSource((minute_at_hour, hour_at_hour, future))
    driver = ClosedBarDecisionDriver(scope, source, settings, history)
    driver.run_through(T0 + HOUR)
    assert seen == [
        (T0 + HOUR, (101.0,), (102.0,)),
        (T0 + HOUR, (101.0,), (102.0,)),
    ]
    assert driver.run_through(T0 + HOUR) == ()
    assert all(item["close"] != 103.0 for item in short.data_buffer)
    driver.run_through(T0 + HOUR + MINUTE)
    assert short.data_buffer[-1]["close"] == 103.0
    assert long.data_buffer[-1]["close"] == 102.0


def test_strategy_history_rejects_cross_symbol_future_and_duplicate():
    short, _ = adapters()
    history = CausalStrategyHistoryFeed(SimpleNamespace(strategies={"short": short}), "BTCUSDT")
    first = bar(T0, MINUTE, 100.0)
    with pytest.raises(ValueError, match="future"):
        history.accept(first, T0)
    history.accept(first, first.close_time)
    with pytest.raises(ValueError, match="duplicate"):
        history.accept(first, first.close_time)
    with pytest.raises(ValueError, match="one-symbol"):
        history.accept(bar(T0 + MINUTE, MINUTE, 200.0, "ETHUSDT"), T0 + 2 * MINUTE)


def test_canonical_decision_trace_with_causal_history_has_stable_prefix():
    from infrastructure.replay.decision_run_scope import ReplayDecisionRunScope

    first = bar(T0, MINUTE, 100.0)
    second = bar(T0 + MINUTE, MINUTE, 101.0)
    future = bar(T0 + 2 * MINUTE, MINUTE, 102.0)
    settings = SimpleNamespace(watcher=SimpleNamespace(historical_candle_watcher_enabled=True))

    def run(bars):
        scope = ReplayDecisionRunScope(T0)
        try:
            feed = CausalStrategyHistoryFeed(scope.strategies, "BTCUSDT")
            driver = ClosedBarDecisionDriver(
                scope, HistoricalClosedBarSource(bars), settings, feed)
            driver.run_through(second.close_time)
            buffer = next(adapter.data_buffer for adapter in scope.strategies.strategies.values()
                          if adapter.config.get("timeframe") == "1m")
            return tuple(scope.decision_trace), tuple(item["close"] for item in buffer)
        finally:
            scope.close()

    prefix = run((first, second))
    assert prefix == run((first, second))
    assert prefix == run((first, second, future))
    assert prefix[1] == (100.0, 101.0)
    assert all(event["event_type"] != "execution_intent" for event in prefix[0])
