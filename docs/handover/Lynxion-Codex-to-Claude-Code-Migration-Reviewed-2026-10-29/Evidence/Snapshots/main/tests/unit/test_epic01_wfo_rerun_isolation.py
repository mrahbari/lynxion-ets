"""Repeated offline WFO runs must not inherit prior result state."""

from unittest.mock import patch

import pandas as pd

from application.walk_forward.sliding_window_splitter import WalkForwardWindow
from infrastructure.backtest.adapters.walk_forward import WalkForwardAnalyzer


def test_repeated_run_does_not_accumulate_oos_windows_or_metrics():
    index = pd.date_range('2026-01-01', periods=2, freq='h', tz='UTC')
    data = pd.DataFrame({'close': [100.0, 101.0]}, index=index)
    window = WalkForwardWindow(index[0], index[0], index[1], index[1],
                               data.iloc[:1], data.iloc[1:], 0)

    class FakeBacktester:
        def run_backtest(self, **kwargs):
            return {'sharpe_ratio': 1.0, 'max_drawdown': 0.0,
                    'total_return': 0.01, 'win_rate': 0.5, 'profit_factor': 1.1}

    analyzer = WalkForwardAnalyzer({'train_size': 1, 'test_size': 1, 'step': 1})
    with patch('infrastructure.backtest.adapters.walk_forward.SlidingWindowSplitter') as splitter:
        splitter.return_value.validate_split.return_value = {
            'has_sufficient_data': True, 'required_points': 2, 'total_data_points': 2,
        }
        splitter.return_value.split.return_value = [window]
        kwargs = {
            'data': {'BTCUSDT': data},
            'strategy_optimizer': lambda train: {'a': len(train)},
            'backtester_class': FakeBacktester,
            'strategy_function': lambda row, params: 0,
        }
        first = analyzer.run_walk_forward_analysis(**kwargs)
        second = analyzer.run_walk_forward_analysis(**kwargs)

    assert first == second
    assert len(analyzer.out_of_sample_results) == 1
    assert len(analyzer.windows) == 1
