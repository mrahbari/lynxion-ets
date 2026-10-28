"""EPIC-01: ambiguous OHLC bars must use conservative SL-first exits."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd

class CollisionPriorityTests(unittest.TestCase):
    def test_both_sides_stop_precedes_nearer_target(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "shared.log_paths.logs_dir", return_value=Path(directory)
        ), patch("shared.log_paths.log_path", return_value=str(Path(directory) / "system.log")):
            from infrastructure.backtest.realistic_backtester import RealisticBacktester

            for direction, stop, target in ((1, 90.0, 105.0), (-1, 110.0, 95.0)):
                with self.subTest(direction=direction):
                    backtester = RealisticBacktester(fee_rate=0, slippage_factor=0)
                    backtester.position = direction
                    backtester.active_positions = [{
                        "entry_price": 100.0, "size": 1.0, "direction": direction,
                        "stop_loss": stop, "take_profit": target,
                    }]
                    candle = pd.Series({"open": 100.0, "high": 111.0, "low": 89.0, "close": 100.0})
                    backtester._check_stop_loss_take_profit(candle, datetime(2026, 1, 1))
                    self.assertEqual(backtester.trades[-1]["exit_type"], "SL")
                    self.assertEqual(backtester.trades[-1]["price"], stop)
                    self.assertTrue(backtester.trades[-1]["same_bar_collision"])


if __name__ == "__main__":
    unittest.main()
