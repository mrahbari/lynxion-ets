"""EPIC-01: configured WFO days must not silently become bar counts."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from application.walk_forward.sliding_window_splitter import SlidingWindowSplitter


class CalendarWindowTests(unittest.TestCase):
    def test_hourly_bars_do_not_turn_120_rows_into_120_days(self):
        bars = pd.DataFrame({'close': range(120)}, index=pd.date_range(
            '2026-01-01', periods=120, freq='h', tz='UTC'))
        splitter = SlidingWindowSplitter(90, 30, 30, size_unit='days')
        self.assertEqual(splitter.split(bars), [])
        self.assertFalse(splitter.validate_split(bars)['has_sufficient_data'])

    def test_calendar_windows_are_half_open_and_chronological(self):
        index = pd.date_range('2026-01-01', periods=121 * 24 + 1, freq='h', tz='UTC')
        bars = pd.DataFrame({'close': range(len(index))}, index=index)
        splitter = SlidingWindowSplitter(90, 30, 30, size_unit='days')
        windows = splitter.split(bars)
        self.assertEqual(len(windows), 1)
        window = windows[0]
        self.assertEqual(len(window.train_data), 90 * 24)
        self.assertEqual(len(window.test_data), 30 * 24)
        self.assertLess(window.train_end, window.test_start)
        self.assertEqual(window.test_start, index[90 * 24])
        self.assertTrue(splitter.validate_split(bars)['has_sufficient_data'])

    def test_duplicate_timestamps_fail_closed(self):
        bars = pd.DataFrame({'close': [1, 2]}, index=pd.DatetimeIndex([
            '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z']))
        with self.assertRaisesRegex(ValueError, 'unique timestamps'):
            SlidingWindowSplitter(size_unit='days').split(bars)

    def test_walk_forward_analyzer_uses_calendar_mode_when_configured(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from infrastructure.backtest.adapters.walk_forward import WalkForwardAnalyzer

            analyzer = WalkForwardAnalyzer({'train_size': 90, 'test_size': 30,
                                            'step': 30, 'size_unit': 'days'})
            with patch('infrastructure.backtest.adapters.walk_forward.SlidingWindowSplitter') as splitter:
                splitter.return_value.validate_split.return_value = {'has_sufficient_data': False,
                                                                      'required_points': None,
                                                                      'total_data_points': 0}
                splitter.return_value.split.return_value = []
                with self.assertRaisesRegex(ValueError, 'No valid walk-forward windows'):
                    analyzer.run_walk_forward_analysis({'BTCUSDT': pd.DataFrame({'close': []},
                                                        index=pd.DatetimeIndex([], tz='UTC'))},
                                                       strategy_optimizer=lambda _: {},
                                                       strategy_function=lambda row, params: 0)
                self.assertEqual(splitter.call_args.kwargs['size_unit'], 'days')

    def test_orchestrator_passes_days_to_outer_split_and_analyzer(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from application.walk_forward.wfo_orchestrator import WFOOrchestrator

            with patch('application.walk_forward.wfo_orchestrator.CSVHistoryLoader'), patch(
                'application.walk_forward.wfo_orchestrator.MultiAssetHyperoptAdapter'
            ), patch('application.walk_forward.wfo_orchestrator.CrossValidationEngine'), patch(
                'application.walk_forward.wfo_orchestrator.WalkForwardAnalyzer'
            ) as analyzer:
                orchestrator = WFOOrchestrator({'results_dir': directory})
                self.assertEqual(orchestrator.splitter.size_unit, 'days')
                self.assertEqual(analyzer.call_args.args[0]['size_unit'], 'days')


if __name__ == '__main__':
    unittest.main()
