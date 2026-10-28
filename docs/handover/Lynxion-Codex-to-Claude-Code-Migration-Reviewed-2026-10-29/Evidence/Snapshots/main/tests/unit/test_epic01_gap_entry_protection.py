"""A next-open entry cannot inherit protective levels crossed by that open."""

import pandas as pd
import pytest

from infrastructure.backtest.execution_intent import OrderSide, create_execution_intent
from infrastructure.backtest.realistic_backtester import RealisticBacktester


@pytest.mark.parametrize(
    'side,opening,stop,target',
    [
        (OrderSide.BUY, 90.0, 95.0, 110.0),
        (OrderSide.BUY, 115.0, 95.0, 110.0),
        (OrderSide.SELL, 110.0, 105.0, 90.0),
        (OrderSide.SELL, 85.0, 105.0, 90.0),
    ],
)
def test_gap_crossed_bracket_is_not_admitted(side, opening, stop, target):
    index = pd.date_range('2026-01-01', periods=62, freq='h', tz='UTC')
    bars = pd.DataFrame({
        'open': [100.0] * 61 + [opening],
        'high': [101.0] * 61 + [max(opening, 100.0) + 1.0],
        'low': [99.0] * 61 + [min(opening, 100.0) - 1.0],
        'close': [100.0] * 61 + [opening],
        'volume': [1000.0] * 62,
    }, index=index)

    def strategy(row, _params):
        if row.name != index[60]:
            return None
        return create_execution_intent(
            side=side, size=0.1, price=100.0,
            timestamp=row.name.to_pydatetime(), symbol='BTCUSDT',
            stop_loss=stop, take_profit=target,
        )

    backtester = RealisticBacktester(fee_rate=0, slippage_factor=0,
                                     spread_bps=0, latency_slippage_bps=0)
    backtester.run_backtest(bars, strategy, {'symbol': 'BTCUSDT'})
    assert backtester.total_trades == 0
