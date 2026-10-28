"""Offline replay must reject ambiguous or nonchronological bar clocks."""

import pandas as pd
import pytest

from infrastructure.backtest.realistic_backtester import RealisticBacktester


@pytest.mark.parametrize('timestamp_value', ['2026-01-02T00:00:00Z', pd.NaT])
def test_timestamp_column_conflicting_with_index_fails_closed(timestamp_value):
    index = pd.DatetimeIndex(['2026-01-01T00:00:00Z'])
    bars = pd.DataFrame({
        'open': [100.0], 'high': [101.0], 'low': [99.0],
        'close': [100.0], 'timestamp': [timestamp_value],
    }, index=index)
    with pytest.raises(ValueError, match='timestamp'):
        RealisticBacktester()._validate_data(bars)


def test_matching_timestamp_column_is_accepted():
    index = pd.DatetimeIndex(['2026-01-01T00:00:00Z'])
    bars = pd.DataFrame({
        'open': [100.0], 'high': [101.0], 'low': [99.0],
        'close': [100.0], 'timestamp': [index[0]],
    }, index=index)
    RealisticBacktester()._validate_data(bars)


@pytest.mark.parametrize('index', [
    pd.DatetimeIndex(['2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z']),
    pd.DatetimeIndex(['2026-01-02T00:00:00Z', '2026-01-01T00:00:00Z']),
])
def test_duplicate_or_out_of_order_bar_clock_fails_closed(index):
    bars = pd.DataFrame({
        'open': [100.0, 100.0], 'high': [101.0, 101.0],
        'low': [99.0, 99.0], 'close': [100.0, 100.0],
    }, index=index)
    with pytest.raises(ValueError, match='strictly increasing'):
        RealisticBacktester()._validate_data(bars)
