"""
Unit tests for Strategy Adapters.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from decimal import Decimal
from datetime import datetime

from infrastructure.strategies.strategy_adapters import (
    TrendFollowStrategyAdapter, 
    MeanReversionStrategyAdapter,
    ScalpingStrategyAdapter, 
    BreakoutStrategyAdapter,
    BaseStrategyAdapter
)


class TestBaseStrategyAdapter(unittest.TestCase):
    """Test cases for BaseStrategyAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = BaseStrategyAdapter("TestStrategy")

    def test_init_sets_name(self):
        """Test that BaseStrategyAdapter is initialized with correct name."""
        self.assertEqual(self.adapter.name, "TestStrategy")

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns the strategy name."""
        self.assertEqual(self.adapter.get_strategy_name(), "TestStrategy")

    def test_update_with_market_data_does_nothing_by_default(self):
        """Test that update_with_market_data has base implementation."""
        data = {"price": 45000, "volume": 100}
        
        # This shouldn't raise an exception
        try:
            self.adapter.update_with_market_data(data)
            success = True
        except NotImplementedError:
            success = False

        self.assertTrue(success)

    def test_calculate_position_size_basic_calculation(self):
        """Test basic position size calculation."""
        signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal('0.5')),
            score=0.6,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )

        account_balance = 10000.0
        # The calculation in the code is: account_balance * 0.02 * float(signal.confidence)
        # Since Percentage value is 0.5, it should be converted to float properly
        expected_position_size = account_balance * 0.02 * float(signal.confidence.value)  # Risk 2% * confidence 50%

        result = self.adapter.calculate_position_size(signal, account_balance)

        self.assertEqual(result, expected_position_size)


class TestTrendFollowStrategyAdapter(unittest.TestCase):
    """Test cases for TrendFollowStrategyAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = TrendFollowStrategyAdapter()

    def test_init_sets_correct_attributes(self):
        """Test that TrendFollowStrategyAdapter is initialized with correct attributes."""
        self.assertEqual(self.adapter.name, "TrendFollow")
        self.assertEqual(self.adapter.lookback_period, 50)
        self.assertEqual(self.adapter.moving_average_type, "EMA")

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns correct name."""
        self.assertEqual(self.adapter.get_strategy_name(), "TrendFollow")

    def test_generate_signal_returns_signal(self):
        """Test that generate_signal returns a valid signal."""
        symbol = Symbol("BTCUSDT")
        
        signal = self.adapter.generate_signal(symbol)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL])
        self.assertIsInstance(signal.confidence, Percentage)
        self.assertIsInstance(signal.score, float)
        self.assertEqual(signal.strategy_name, "TrendFollow")


class TestMeanReversionStrategyAdapter(unittest.TestCase):
    """Test cases for MeanReversionStrategyAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = MeanReversionStrategyAdapter()

    def test_init_sets_correct_attributes(self):
        """Test that MeanReversionStrategyAdapter is initialized with correct attributes."""
        self.assertEqual(self.adapter.name, "MeanReversion")
        self.assertEqual(self.adapter.lookback_period, 20)
        self.assertEqual(self.adapter.std_dev_threshold, 2.0)

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns correct name."""
        self.assertEqual(self.adapter.get_strategy_name(), "MeanReversion")

    def test_generate_signal_returns_signal(self):
        """Test that generate_signal returns a valid signal."""
        symbol = Symbol("BTCUSDT")
        
        signal = self.adapter.generate_signal(symbol)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL])
        self.assertIsInstance(signal.confidence, Percentage)
        self.assertIsInstance(signal.score, float)
        self.assertEqual(signal.strategy_name, "MeanReversion")


class TestScalpingStrategyAdapter(unittest.TestCase):
    """Test cases for ScalpingStrategyAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = ScalpingStrategyAdapter()

    def test_init_sets_correct_attributes(self):
        """Test that ScalpingStrategyAdapter is initialized with correct attributes."""
        self.assertEqual(self.adapter.name, "Scalper")
        self.assertEqual(self.adapter.lookback_period, 5)
        self.assertEqual(self.adapter.profit_target, 0.005)
        self.assertEqual(self.adapter.stop_loss, 0.003)

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns correct name."""
        self.assertEqual(self.adapter.get_strategy_name(), "Scalper")

    def test_generate_signal_returns_signal(self):
        """Test that generate_signal returns a valid signal."""
        symbol = Symbol("BTCUSDT")
        
        signal = self.adapter.generate_signal(symbol)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL])
        self.assertIsInstance(signal.confidence, Percentage)
        self.assertIsInstance(signal.score, float)
        self.assertEqual(signal.strategy_name, "Scalper")


class TestBreakoutStrategyAdapter(unittest.TestCase):
    """Test cases for BreakoutStrategyAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = BreakoutStrategyAdapter()

    def test_init_sets_correct_attributes(self):
        """Test that BreakoutStrategyAdapter is initialized with correct attributes."""
        self.assertEqual(self.adapter.name, "Breakout")
        self.assertEqual(self.adapter.lookback_period, 20)
        self.assertEqual(self.adapter.consolidation_period, 10)
        self.assertEqual(self.adapter.breakout_threshold, 0.02)

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns correct name."""
        self.assertEqual(self.adapter.get_strategy_name(), "Breakout")

    def test_generate_signal_returns_signal(self):
        """Test that generate_signal returns a valid signal."""
        symbol = Symbol("BTCUSDT")
        
        signal = self.adapter.generate_signal(symbol)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL])
        self.assertIsInstance(signal.confidence, Percentage)
        self.assertIsInstance(signal.score, float)
        self.assertEqual(signal.strategy_name, "Breakout")


if __name__ == '__main__':
    unittest.main()