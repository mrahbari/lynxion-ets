"""Closed-bar watcher subset reaches existing canonical event handlers causally."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from infrastructure.replay.closed_bar_decision_driver import ClosedBarDecisionDriver
from infrastructure.replay.decision_run_scope import ReplayDecisionRunScope
from infrastructure.replay.historical_closed_bar_source import ClosedBar, HistoricalClosedBarSource


START = datetime(2026, 1, 1, tzinfo=timezone.utc)
MINUTE = timedelta(minutes=1)


def bar(symbol, index, close):
    opened = START + index * MINUTE
    return ClosedBar(symbol, MINUTE, opened, opened + MINUTE,
                     close - 1, close + 1, close - 2, close, 10.0)


def run(bars, through):
    source = HistoricalClosedBarSource(bars)
    scope = ReplayDecisionRunScope(START)
    settings = SimpleNamespace(watcher=SimpleNamespace(historical_candle_watcher_enabled=True))
    try:
        driver = ClosedBarDecisionDriver(scope, source, settings)
        reached = driver.run_through(through)
        normalized = tuple((
            item.symbol.value, item.timestamp, item.observation_type,
            item.observation_value, item.market_price,
            tuple(event.value for event in events),
        ) for item, events in reached)
        assert driver.run_through(through) == ()
        return normalized, dict(scope.risk_manager.price_history_for_correlation), driver
    finally:
        scope.close()


def test_closed_bar_subset_prefix_is_stable_when_future_bar_is_appended():
    first = bar("BTCUSDT", 0, 100.0)
    second = bar("BTCUSDT", 1, 101.0)
    future = bar("BTCUSDT", 2, 102.0)
    prefix, prefix_prices, _ = run((first, second), second.close_time)
    extended, extended_prices, _ = run((first, second, future), second.close_time)
    assert prefix == extended
    assert prefix_prices == extended_prices == {"BTCUSDT": [100.0, 101.0]}
    assert [row[1] for row in prefix] == [first.close_time, second.close_time]


def test_closed_bar_subset_keeps_two_symbol_watcher_buffers_separate():
    btc = bar("BTCUSDT", 0, 100.0)
    eth = bar("ETHUSDT", 0, 200.0)
    normalized, prices, driver = run((btc, eth), btc.close_time)
    assert [row[0] for row in normalized] == ["BTCUSDT", "ETHUSDT"]
    assert prices == {"BTCUSDT": [100.0], "ETHUSDT": [200.0]}
    assert len(driver.watchers) == 2


def test_closed_bar_driver_preserves_live_watcher_identity_for_fusion():
    candle = bar("BTCUSDT", 0, 100.0)
    scope = ReplayDecisionRunScope(START)
    try:
        driver = ClosedBarDecisionDriver(
            scope, HistoricalClosedBarSource((candle,)),
            SimpleNamespace(watcher=SimpleNamespace(historical_candle_watcher_enabled=True)),
        )
        reached = driver.run_through(candle.close_time)
        assert reached[0][0].metadata["watcher_name"] == "historical_candle"
        fused = [row for row in scope.decision_trace if row["event_type"] == "fused_signal"]
        assert len(fused) == 1
        assert fused[0]["data"]["metadata"]["hierarchical_fusion"] is True
    finally:
        scope.close()
