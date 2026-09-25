"""Risk run time is explicit without changing Live's default clock."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from application.risk_management.enterprise_risk_manager import (
    EnterpriseRiskManager, PositionDirection,
)
from infrastructure.messaging.clock import LiveClock, ReplayClock


def test_replay_risk_uses_event_time_for_day_and_position_lifecycle(monkeypatch):
    import application.risk_management.enterprise_risk_manager as risk_module

    origin = datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc)
    clock = ReplayClock(origin)
    events = []
    monkeypatch.setattr(risk_module, "trade_tracker", SimpleNamespace(
        register_trade=lambda **kwargs: events.append(("enter", kwargs["timestamp"])),
        close_trade=lambda **kwargs: events.append(("exit", kwargs["exit_timestamp"])),
    ))
    manager = EnterpriseRiskManager(clock=clock, start_correlation_worker=False)
    assert manager.daily_start == origin.date()
    assert manager.enter_position("BTCUSDT", 100, 1, PositionDirection.LONG,
                                  95, 110, trade_id="offline-risk-clock")
    assert manager.positions["BTCUSDT"].entry_time == origin
    clock.advance(origin + timedelta(minutes=2))
    manager.exit_position("BTCUSDT", 101, "TP")
    manager.reset_daily_counters()
    assert manager.daily_start == clock.now().date()
    assert events == [("enter", origin), ("exit", clock.now())]
    assert manager.worker_thread is None


def test_omitted_risk_clock_preserves_live_clock_default(monkeypatch):
    instant = datetime(2026, 1, 1)
    monkeypatch.setattr(LiveClock, "now", lambda self: instant)
    manager = EnterpriseRiskManager(start_correlation_worker=False)
    assert isinstance(manager.clock, LiveClock)
    assert manager.daily_start == instant.date()
