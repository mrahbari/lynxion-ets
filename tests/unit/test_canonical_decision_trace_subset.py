"""Decision-level trace for the bounded completed-candle canonical subset."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
import socket

from domain.entities.order import ExecutionIntent
from domain.enums.order_side import OrderSide
from domain.value_objects import Percentage, Symbol
from infrastructure.messaging.event_system import EventType, SignalEvent
from infrastructure.replay.closed_bar_decision_driver import ClosedBarDecisionDriver
from infrastructure.replay.decision_run_scope import ReplayDecisionRunScope
from infrastructure.replay.historical_closed_bar_source import ClosedBar, HistoricalClosedBarSource
from infrastructure.replay.normalized_decision_trace import normalize_event


T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
MINUTE = timedelta(minutes=1)


def _bar(index, close):
    opened = T0 + index * MINUTE
    return ClosedBar("BTCUSDT", MINUTE, opened, opened + MINUTE,
                     close - 1, close + 1, close - 2, close, 10.0)


def _trace(bars, through, monkeypatch):
    attempts = []

    def deny_connect(*args):
        attempts.append(args)
        raise AssertionError("network reached")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    scope = ReplayDecisionRunScope(T0)
    try:
        driver = ClosedBarDecisionDriver(
            scope, HistoricalClosedBarSource(bars),
            SimpleNamespace(watcher=SimpleNamespace(historical_candle_watcher_enabled=True)),
        )
        driver.run_through(through)
        assert attempts == []
        return tuple(scope.decision_trace)
    finally:
        scope.close()


def test_canonical_candle_subset_decision_trace_repeats_and_is_prefix_stable(monkeypatch):
    first, second, future = _bar(0, 100.0), _bar(1, 101.0), _bar(2, 102.0)
    prefix = _trace((first, second), second.close_time, monkeypatch)
    assert prefix == _trace((first, second), second.close_time, monkeypatch)
    assert prefix == _trace((first, second, future), second.close_time, monkeypatch)
    assert {row["event_type"] for row in prefix} >= {
        "market_observation", "interpreted_signal", "fused_signal"
    }
    assert all(datetime.fromisoformat(row["timestamp"]) <= second.close_time for row in prefix)


def test_trace_keeps_decision_fields_but_excludes_only_random_intent_uuid():
    def intent(intent_id, confidence):
        return ExecutionIntent(
            symbol=Symbol("BTCUSDT"), strategy_name="fixture",
            side=OrderSide.BUY, intent_confidence=Percentage(Decimal(confidence)),
            risk_parameters={"stop_loss": 95.0, "take_profit": 110.0},
            timestamp=T0, intent_id=intent_id,
        )

    def trace(item):
        return normalize_event(SignalEvent(
            EventType.EXECUTION_INTENT, item, timestamp=T0,
            source_component="SignalAggregator", correlation_id="fixture",
        ))

    assert trace(intent("random-a", "0.8")) == trace(intent("random-b", "0.8"))
    assert trace(intent("random-a", "0.8")) != trace(intent("random-b", "0.7"))
    assert trace(intent("random-a", "0.8"))["data"]["risk_parameters"] == {
        "stop_loss": 95.0, "take_profit": 110.0,
    }
