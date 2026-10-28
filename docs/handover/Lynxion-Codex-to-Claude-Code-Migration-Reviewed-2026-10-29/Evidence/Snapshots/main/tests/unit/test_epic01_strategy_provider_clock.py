"""Historical adapter replay must not synthesize a wall-clock bar time."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from infrastructure.backtest.strategy_provider import load_sample_strategy


@pytest.fixture(autouse=True)
def _isolate_adapter(monkeypatch):
    # Test the provider's clock boundary without loading runtime configuration.
    from infrastructure.strategies.adapters import trend_follow_strategy_adapter

    class FakeAdapter:
        def __init__(self, config):
            self.config = config

        def update_with_market_data(self, bar):
            pass

        def generate_signal(self, symbol):
            return None

        def record_trade_result(self, *args, **kwargs):
            pass

    monkeypatch.setattr(trend_follow_strategy_adapter, 'TrendFollowStrategyAdapter', FakeAdapter)


def _bar(index):
    return pd.Series({
        'open': 100.0, 'high': 101.0, 'low': 99.0,
        'close': 100.0, 'volume': 1.0,
    }, name=index)


@pytest.mark.parametrize('index', [0, pd.NaT, 'not-a-time'])
def test_missing_or_invalid_historical_bar_clock_fails_closed(index):
    strategy = load_sample_strategy('trend_following')
    with pytest.raises(ValueError, match='historical bar timestamp'):
        strategy(_bar(index), {'symbol': 'BTCUSDT'})


def test_valid_historical_bar_clock_is_not_rejected():
    strategy = load_sample_strategy('trend_following')
    strategy(_bar(datetime(2026, 1, 1, tzinfo=timezone.utc)), {'symbol': 'BTCUSDT'})
