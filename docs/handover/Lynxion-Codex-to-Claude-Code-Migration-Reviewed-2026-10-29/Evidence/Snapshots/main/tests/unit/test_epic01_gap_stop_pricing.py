"""A stop crossed at the open cannot fill at its better trigger price."""

import pandas as pd
import pytest

from infrastructure.backtest.realistic_backtester import RealisticBacktester


@pytest.mark.parametrize(
    'direction,opening,high,low,stop,target,expected',
    [
        (1, 90.0, 92.0, 88.0, 95.0, 110.0, 90.0),
        (-1, 110.0, 112.0, 108.0, 105.0, 90.0, 110.0),
    ],
)
def test_existing_position_gaps_through_stop_at_worse_open(
    direction, opening, high, low, stop, target, expected
):
    backtester = RealisticBacktester(fee_rate=0, slippage_factor=0)
    backtester.position = direction * 1.0
    backtester.position_value = direction * 100.0
    backtester.cash = 10000.0 - direction * 100.0
    backtester.active_positions = [{
        'entry_price': 100.0, 'size': 1.0, 'direction': direction,
        'stop_loss': stop, 'take_profit': target, 'entry_regime': 'unknown',
    }]
    bar = pd.Series({'open': opening, 'high': high, 'low': low,
                     'close': opening, 'volume': 1000.0})
    backtester._check_stop_loss_take_profit(bar, pd.Timestamp('2026-01-02', tz='UTC'))
    assert backtester.trades[-1]['exit_type'] == 'SL'
    assert backtester.trades[-1]['price'] == expected
