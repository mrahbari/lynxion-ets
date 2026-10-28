"""An intent's recorded trade must match its signal across bar intervals."""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


class SignalTradeIdentityTests(unittest.TestCase):
    def test_linked_next_bar_trade_matches_without_five_minute_assumption(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from infrastructure.backtest.realistic_backtester import RealisticBacktester

            backtester = RealisticBacktester()
            signal_time = datetime(2026, 1, 1)
            signal_id = backtester.record_strategy_signal(signal_time, 1, 'trend_following', 100)
            trade = {'id': 'trade-1', 'timestamp': signal_time + timedelta(minutes=15)}
            backtester.confirm_trade_attempt(signal_id, trade)
            result = backtester.validate_signal_trade_correspondence(
                [{'signal_id': signal_id, 'timestamp': signal_time, 'signal': 1}], [trade])
            self.assertEqual(result['signals_with_trade_attempts'], 1)
            self.assertTrue(result['validation_passed'])

    def test_unlinked_later_trade_does_not_match(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from infrastructure.backtest.realistic_backtester import RealisticBacktester

            backtester = RealisticBacktester()
            signal_time = datetime(2026, 1, 1)
            signal_id = backtester.record_strategy_signal(signal_time, 1, 'trend_following', 100)
            trade = {'id': 'unrelated', 'timestamp': signal_time + timedelta(minutes=15)}
            result = backtester.validate_signal_trade_correspondence(
                [{'signal_id': signal_id, 'timestamp': signal_time, 'signal': 1}], [trade])
            self.assertEqual(result['signals_with_trade_attempts'], 0)


if __name__ == '__main__':
    unittest.main()
