"""Expected-failing causal execution contract for the canonical backtester."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd


class NextAvailableExecutionTests(unittest.TestCase):
    def test_complete_signal_bar_cannot_fill_at_its_own_close(self):
        # Independently specified fixture: the signal is knowable only after
        # bar 60 closes at 100; the first later executable open is 110.
        index = pd.date_range('2026-01-01', periods=62, freq='h', tz='UTC')
        closes = [100.0] * 61 + [110.0]
        bars = pd.DataFrame({
            'open': [100.0] * 61 + [110.0],
            'high': [101.0] * 61 + [111.0],
            'low': [99.0] * 61 + [109.0],
            'close': closes,
            'volume': [1000.0] * 62,
        }, index=index)
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from infrastructure.backtest.execution_intent import OrderSide, create_execution_intent
            from infrastructure.backtest.realistic_backtester import RealisticBacktester

            def strategy(row, _params):
                if row.name != index[60]:
                    return None
                return create_execution_intent(
                    side=OrderSide.BUY, size=1.0, price=float(row['close']),
                    timestamp=row.name.to_pydatetime(), symbol='BTCUSDT')

            backtester = RealisticBacktester(fee_rate=0, slippage_factor=0,
                                             spread_bps=0, latency_slippage_bps=0)
            result = backtester.run_backtest(bars, strategy, {'symbol': 'BTCUSDT'})
            entry = next(trade for trade in result['trades'] if trade.get('intent_id'))
            self.assertGreaterEqual(pd.Timestamp(entry['timestamp']), index[61])
            self.assertEqual(entry['price'], 110.0)

    def test_last_closed_bar_intent_has_no_executable_future_bar(self):
        # A signal on the final closed candle has no later bar on which a fill
        # can be observed; force-closing must not invent a same-bar entry.
        index = pd.date_range('2026-01-01', periods=62, freq='h', tz='UTC')
        bars = pd.DataFrame({
            'open': [100.0] * 62,
            'high': [101.0] * 62,
            'low': [99.0] * 62,
            'close': [100.0] * 62,
            'volume': [1000.0] * 62,
        }, index=index)
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from infrastructure.backtest.execution_intent import OrderSide, create_execution_intent
            from infrastructure.backtest.realistic_backtester import RealisticBacktester

            def strategy(row, _params):
                if row.name != index[-1]:
                    return None
                return create_execution_intent(
                    side=OrderSide.BUY, size=1.0, price=float(row['close']),
                    timestamp=row.name.to_pydatetime(), symbol='BTCUSDT')

            backtester = RealisticBacktester(fee_rate=0, slippage_factor=0,
                                             spread_bps=0, latency_slippage_bps=0)
            backtester.run_backtest(bars, strategy, {'symbol': 'BTCUSDT'})
            self.assertEqual(backtester.total_trades, 0)

    def test_next_open_slippage_uses_only_prior_closed_bar_volume(self):
        index = pd.date_range('2026-01-01', periods=62, freq='h', tz='UTC')
        bars = pd.DataFrame({
            'open': [100.0] * 61 + [110.0],
            'high': [101.0] * 61 + [111.0],
            'low': [99.0] * 61 + [109.0],
            'close': [100.0] * 61 + [110.0],
            'volume': [1000.0] * 60 + [10.0, 1000000.0],
        }, index=index)
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from infrastructure.backtest.execution_intent import OrderSide, create_execution_intent
            from infrastructure.backtest.realistic_backtester import RealisticBacktester

            def strategy(row, _params):
                if row.name != index[60]:
                    return None
                return create_execution_intent(
                    side=OrderSide.BUY, size=1.0, price=100.0,
                    timestamp=row.name.to_pydatetime(), symbol='BTCUSDT')

            backtester = RealisticBacktester(fee_rate=0, slippage_factor=0.01,
                                             spread_bps=0, latency_slippage_bps=0)
            result = backtester.run_backtest(bars, strategy, {'symbol': 'BTCUSDT'})
            entry = next(trade for trade in result['trades'] if trade.get('intent_id'))
            # 110 + (1% * 110) * (1 + 2 * 1 / 10) = 111.32.
            self.assertAlmostEqual(entry['price'], 111.32)
            self.assertEqual(entry['signal_timestamp'], index[60])
            self.assertEqual(pd.Timestamp(entry['timestamp']), index[61])

    def test_same_direction_cooldown_uses_fill_time(self):
        index = pd.date_range('2026-01-01', periods=63, freq='h', tz='UTC')
        bars = pd.DataFrame({
            'open': [100.0] * 63, 'high': [101.0] * 63,
            'low': [99.0] * 63, 'close': [100.0] * 63,
            'volume': [1000.0] * 63,
        }, index=index)
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from infrastructure.backtest.execution_intent import OrderSide, create_execution_intent
            from infrastructure.backtest.realistic_backtester import RealisticBacktester

            def strategy(row, _params):
                if row.name not in (index[60], index[61]):
                    return None
                return create_execution_intent(
                    side=OrderSide.BUY, size=1.0, price=100.0,
                    timestamp=row.name.to_pydatetime(), symbol='BTCUSDT')

            backtester = RealisticBacktester(fee_rate=0, slippage_factor=0,
                                             spread_bps=0, latency_slippage_bps=0)
            result = backtester.run_backtest(
                bars, strategy, {'symbol': 'BTCUSDT', 'order_cooldown_seconds': 7200}
            )
            entries = [trade for trade in result['trades'] if trade.get('intent_id')]
            self.assertEqual(len(entries), 1)
            self.assertEqual(pd.Timestamp(entries[0]['timestamp']), index[61])


if __name__ == '__main__':
    unittest.main()
