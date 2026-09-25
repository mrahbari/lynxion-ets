"""Guard breaker state can be local and event-time controlled."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from infrastructure.messaging.clock import LiveClock, ReplayClock
from shared.circuit_breaker import CircuitBreaker
from shared.live_execution_guard import ExecutionMode, LiveExecutionGuard


T = datetime(2026, 1, 1, tzinfo=timezone.utc)
ORDER = SimpleNamespace(symbol=SimpleNamespace(value="BTCUSDT"))
SETTINGS = SimpleNamespace(broker=SimpleNamespace(paper_trading=True, testnet=True))


def scoped():
    clock = ReplayClock(T)
    breaker = CircuitBreaker("order_path:bingx", clock=clock)
    guard = LiveExecutionGuard(breaker_lookup=lambda broker: breaker)
    guard.set_risk_enforcer(lambda order: (True, ""))
    return clock, breaker, guard


def test_two_guards_have_distinct_breaker_state_and_event_time():
    clock_a, breaker_a, guard_a = scoped()
    _, breaker_b, guard_b = scoped()
    assert guard_a.evaluate("bingx", SETTINGS, ORDER).mode is ExecutionMode.PAPER
    for _ in range(5):
        breaker_a._on_failure()
    assert breaker_a.open_since == T
    assert guard_a.evaluate("bingx", SETTINGS, ORDER).mode is ExecutionMode.BLOCKED
    assert guard_b.evaluate("bingx", SETTINGS, ORDER).mode is ExecutionMode.PAPER
    assert breaker_b.failure_count == 0
    clock_a.advance(T + timedelta(seconds=60))
    assert breaker_a.get_status()["should_reset"] is False
    clock_a.advance(T + timedelta(seconds=61))
    assert breaker_a.get_status()["should_reset"] is True
    assert guard_a.evaluate("bingx", SETTINGS, ORDER).mode is ExecutionMode.PAPER


def test_default_breaker_clock_remains_live(monkeypatch):
    expected = datetime(2026, 1, 1)
    monkeypatch.setattr(LiveClock, "now", lambda self: expected)
    breaker = CircuitBreaker("offline-default")
    breaker._on_failure()
    assert isinstance(breaker.clock, LiveClock)
    assert breaker.last_failure_time == expected
