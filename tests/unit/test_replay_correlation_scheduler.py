"""Deterministic, closed-event-time correlation publication tests."""

from datetime import datetime, timedelta, timezone

import pytest

from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
from infrastructure.messaging.clock import ReplayClock
from infrastructure.risk.replay_correlation_scheduler import ReplayCorrelationScheduler


T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def scope():
    manager = EnterpriseRiskManager(start_correlation_worker=False)
    clock = ReplayClock(T0)
    scheduler = ReplayCorrelationScheduler(manager, clock)
    assert manager.worker_thread is None
    return manager, scheduler


def prices(count=5):
    return [(symbol, value) for i in range(count)
            for symbol, value in (("BTCUSDT", 100 + i), ("ETHUSDT", 200 + 2 * i))]


def run_fixture():
    manager, scheduler = scope()
    scheduler.advance(T0, prices(4))
    scheduler.advance(T0 + timedelta(seconds=10), prices(5)[-2:])
    scheduler.advance(T0 + timedelta(seconds=35))
    return manager.get_correlation_snapshot(), tuple(scheduler.publications)


def test_repeated_event_time_fixture_is_identical_without_a_worker():
    first, trace1 = run_fixture()
    second, trace2 = run_fixture()
    assert dict(first.matrix["BTCUSDT"]) == dict(second.matrix["BTCUSDT"])
    assert first.version == second.version == 3
    assert trace1 == trace2 == (
        (T0 + timedelta(seconds=10), 1),
        (T0 + timedelta(seconds=20), 2),
        (T0 + timedelta(seconds=30), 3),
    )


def test_gap_boundaries_cannot_see_future_price_batch():
    manager, scheduler = scope()
    scheduler.advance(T0, prices(4))
    scheduler.advance(T0 + timedelta(seconds=25), prices(5)[-2:])
    assert manager.get_correlation_snapshot().version == 0
    assert scheduler.publications == []
    scheduler.advance(T0 + timedelta(seconds=30))
    assert manager.get_correlation_snapshot().version == 1
    assert scheduler.publications == [(T0 + timedelta(seconds=30), 1)]


def test_clock_visits_each_due_boundary_before_future_event_time():
    manager, scheduler = scope()
    observed = []
    original = manager.recalculate_correlations

    def record_time():
        observed.append(scheduler._clock.now())
        original()

    manager.recalculate_correlations = record_time
    scheduler.advance(T0, prices(5))
    scheduler.advance(T0 + timedelta(seconds=35))
    assert observed == [T0 + timedelta(seconds=seconds) for seconds in (10, 20, 30)]


def test_same_time_prices_precede_due_publication_and_sizing():
    manager, scheduler = scope()
    scheduler.advance(T0, prices(4))
    pinned = scheduler.advance(T0 + timedelta(seconds=10), prices(5)[-2:])
    assert pinned.version == 1
    assert manager.calculate_correlation_penalty(
        "BTCUSDT", ["ETHUSDT"], snapshot=pinned
    ) == pytest.approx(1.2)
    with pytest.raises(ValueError, match="strictly increasing"):
        scheduler.advance(T0 + timedelta(seconds=10), [])


def test_two_replay_scopes_do_not_share_correlation_state():
    manager_a, scheduler_a = scope()
    manager_b, scheduler_b = scope()
    scheduler_a.advance(T0, prices(5))
    scheduler_a.advance(T0 + timedelta(seconds=10))
    assert manager_a.get_correlation_snapshot().version == 1
    assert manager_b.get_correlation_snapshot().version == 0
    assert scheduler_b.publications == []


def test_replay_uses_no_thread_or_sleep(monkeypatch):
    import threading
    import time

    monkeypatch.setattr(threading, "Thread", lambda *a, **k: pytest.fail("thread created"))
    monkeypatch.setattr(time, "sleep", lambda *a, **k: pytest.fail("wall sleep used"))
    manager, scheduler = scope()
    scheduler.advance(T0, prices(5))
    scheduler.advance(T0 + timedelta(seconds=10))
    assert manager.get_correlation_snapshot().version == 1
