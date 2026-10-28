"""A report with no out-of-sample window is not validation evidence."""

from unittest.mock import patch

import pandas as pd
import pytest

from infrastructure.backtest.adapters.walk_forward import WalkForwardAnalyzer


def test_no_valid_windows_fails_instead_of_reporting_zero_performance():
    data = pd.DataFrame({'close': [100.0]},
                        index=pd.date_range('2026-01-01', periods=1, tz='UTC'))
    analyzer = WalkForwardAnalyzer({'train_size': 90, 'test_size': 30,
                                    'step': 30, 'size_unit': 'days'})
    with patch('infrastructure.backtest.adapters.walk_forward.SlidingWindowSplitter') as splitter:
        splitter.return_value.validate_split.return_value = {
            'has_sufficient_data': False, 'required_points': 120,
            'total_data_points': 1,
        }
        splitter.return_value.split.return_value = []
        with pytest.raises(ValueError, match='No valid walk-forward windows'):
            analyzer.run_walk_forward_analysis(
                {'BTCUSDT': data}, strategy_optimizer=lambda train: {},
                strategy_function=lambda row, params: 0,
            )
