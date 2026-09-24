from datetime import datetime, timedelta, timezone

import pytest

from infrastructure.replay.historical_closed_bar_source import ClosedBar, HistoricalClosedBarSource


UTC = timezone.utc
TF = timedelta(minutes=15)


def bar(minute, symbol="BTCUSDT", timeframe=TF):
    start = datetime(2026, 1, 1, 0, minute, tzinfo=UTC)
    return ClosedBar(symbol, timeframe, start, start + timeframe, 100, 102, 99, 101, 10)


def test_only_completed_bars_and_prefix_invariance():
    prefix = [bar(0), bar(15)]
    source_a = HistoricalClosedBarSource(prefix)
    source_b = HistoricalClosedBarSource(prefix + [bar(30)])
    decision_time = prefix[-1].close_time
    assert list(source_a.completed_through(decision_time)) == list(source_b.completed_through(decision_time))
    assert list(source_b.completed_through(prefix[0].open_time)) == []


def test_duplicate_gap_and_out_of_order_fail_closed():
    for bars in ([bar(0), bar(0)], [bar(0), bar(30)], [bar(15), bar(0)]):
        with pytest.raises(ValueError):
            HistoricalClosedBarSource(bars)


def test_mtf_bar_unavailable_until_its_actual_close():
    hour = bar(0, timeframe=timedelta(hours=1))
    source = HistoricalClosedBarSource([hour])
    assert list(source.completed_through(datetime(2026, 1, 1, 0, 45, tzinfo=UTC))) == []
    assert list(source.completed_through(hour.close_time)) == [hour]


def test_missing_and_nonfinite_are_not_zero_filled():
    with pytest.raises((TypeError, ValueError)):
        HistoricalClosedBarSource([ClosedBar("BTCUSDT", TF, bar(0).open_time, bar(0).close_time, 100, 102, 99, float("nan"), 10)])


def test_repeated_source_and_utc_day_boundary_are_deterministic():
    midnight = datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
    previous = ClosedBar("ETHUSDT", TF, midnight - TF, midnight, 100, 102, 99, 101, 10)
    next_bar = ClosedBar("ETHUSDT", TF, midnight, midnight + TF, 101, 103, 100, 102, 10)
    a = HistoricalClosedBarSource([previous, next_bar])
    b = HistoricalClosedBarSource([previous, next_bar])
    assert list(a.completed_through(midnight)) == list(b.completed_through(midnight)) == [previous]
