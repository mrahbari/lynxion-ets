"""E-P5.2 discipline remediation: backtest-time-aware + outcome feedback.

Locks in that strategy discipline keys off SIMULATED time (not wall-clock) and
responds to realised trade outcomes, so backtests are credible:
- daily-trade limit resets per simulated day (not capped for the whole run),
- consecutive-loss tracking responds to fed outcomes,
- the consecutive-loss safety pause is TEMPORARY (recovers after a cool-off),
- the post-exit cooldown uses the simulated exit time.
"""
from datetime import datetime, timedelta

import pytest

from infrastructure.strategies.adapters.trend_follow_strategy_adapter import (
    TrendFollowStrategyAdapter,
)

CFG = {
    "max_trades_per_day": 10,
    "max_consecutive_losses": 3,
    "consecutive_loss_pause_minutes": 240,  # 4h
    "cooldown_after_exit_minutes": 30,
    "min_bars_between_entries": 0,
}
SYM = "ETHUSDT"  # deliberately NOT BTC — discipline must be symbol-agnostic


def _adapter():
    a = TrendFollowStrategyAdapter(dict(CFG))
    a.config.update(CFG)  # ensure discipline reads the test thresholds
    return a


def test_daily_limit_resets_across_simulated_days():
    a = _adapter()
    day1 = datetime(2026, 1, 1, 12, 0)
    day2 = datetime(2026, 1, 2, 12, 0)
    # Simulate 10 intents already emitted on day1.
    a.intent_count_today[(SYM, day1.date())] = 10
    assert a._passes_daily_trade_limit_check(SYM, day1) is False   # day1 capped
    assert a._passes_daily_trade_limit_check(SYM, day2) is True    # new simulated day -> reset


def test_outcome_feedback_tracks_consecutive_losses():
    a = _adapter()
    t = datetime(2026, 1, 1, 0, 0)
    a.record_trade_result(SYM, is_profitable=False, exit_time=t)
    a.record_trade_result(SYM, is_profitable=False, exit_time=t)
    assert a.consecutive_losses[SYM] == 2
    a.record_trade_result(SYM, is_profitable=True, exit_time=t)   # a win resets the streak
    assert a.consecutive_losses[SYM] == 0


def test_consecutive_loss_pause_is_temporary():
    a = _adapter()
    t0 = datetime(2026, 1, 1, 0, 0)
    for _ in range(3):
        a.record_trade_result(SYM, is_profitable=False, exit_time=t0)
    assert a.consecutive_losses[SYM] == 3
    # Paused immediately and shortly after the 3rd loss...
    assert a._passes_consecutive_losses_check(SYM, t0) is False
    assert a._passes_consecutive_losses_check(SYM, t0 + timedelta(minutes=60)) is False
    # ...but recovers once the cool-off (240m) elapses (and clears the streak).
    assert a._passes_consecutive_losses_check(SYM, t0 + timedelta(minutes=241)) is True
    assert a.consecutive_losses[SYM] == 0


def test_exit_cooldown_uses_simulated_time():
    a = _adapter()
    t0 = datetime(2026, 1, 1, 0, 0)
    a.record_trade_result(SYM, is_profitable=True, exit_time=t0, position_closed=True)
    assert a.last_exit_time[SYM] == t0
    assert a._passes_exit_cooldown_check(SYM, t0 + timedelta(minutes=10)) is False  # < 30m
    assert a._passes_exit_cooldown_check(SYM, t0 + timedelta(minutes=31)) is True   # >= 30m


def test_discipline_is_symbol_agnostic():
    # State is keyed by the symbol passed in — no implicit BTC bucket.
    a = _adapter()
    t = datetime(2026, 1, 1, 0, 0)
    a.record_trade_result("SOLUSDT", is_profitable=False, exit_time=t)
    assert a.consecutive_losses.get("SOLUSDT") == 1
    assert "BTCUSDT" not in a.consecutive_losses
