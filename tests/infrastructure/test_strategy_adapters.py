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

# Crypto strategy imports from separate files
from infrastructure.strategies.adapters.crypto_liquidity_strategy_adapter import CryptoLiquidityStrategyAdapter
from infrastructure.strategies.adapters.crypto_mtf_trend_strategy_adapter import CryptoMTFTrendStrategyAdapter
from infrastructure.strategies.adapters.crypto_vwap_reversal_strategy_adapter import CryptoVWAPReversalStrategyAdapter
from infrastructure.strategies.adapters.crypto_oi_footprint_strategy_adapter import CryptoOIFootprintStrategyAdapter
from infrastructure.strategies.adapters.crypto_sweep_scalper_adapter import CryptoSweepScalperAdapter


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


class TestCryptoLiquidityStrategyAdapter(unittest.TestCase):
    """Test cases for CryptoLiquidityStrategyAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = CryptoLiquidityStrategyAdapter()

    def test_init_sets_correct_attributes(self):
        """Test that CryptoLiquidityStrategyAdapter is initialized with correct attributes."""
        self.assertEqual(self.adapter.name, "CryptoLiquidity")
        self.assertEqual(self.adapter.min_oi_trend, 0.04)
        self.assertEqual(self.adapter.max_funding_bias, 0.005)
        self.assertEqual(self.adapter.cvd_divergence_strength, 2.0)
        self.assertIn("3m", self.adapter.timeframes)
        self.assertIn("15m", self.adapter.timeframes)
        self.assertIn("1h", self.adapter.timeframes)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            "min_oi_trend": 0.05,
            "max_funding_bias": 0.01,
            "cvd_divergence_strength": 3.0
        }
        adapter = CryptoLiquidityStrategyAdapter(config)
        self.assertEqual(adapter.min_oi_trend, 0.05)
        self.assertEqual(adapter.max_funding_bias, 0.01)
        self.assertEqual(adapter.cvd_divergence_strength, 3.0)

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns correct name."""
        self.assertEqual(self.adapter.get_strategy_name(), "CryptoLiquidity")

    def test_generate_signal_returns_signal(self):
        """Test that generate_signal returns a valid signal."""
        symbol = Symbol("BTCUSDT")

        signal = self.adapter.generate_signal(symbol)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL, SignalType.HOLD, SignalType.NEUTRAL])
        self.assertIsInstance(signal.confidence, Percentage)
        self.assertIsInstance(signal.score, float)
        self.assertEqual(signal.strategy_name, "CryptoLiquidity")

    def test_detect_funding_bias(self):
        """Test funding bias detection logic."""
        # Test negative funding (long bias)
        result = self.adapter.detect_funding_bias(-0.01)
        self.assertEqual(result, 1)  # Long bias

        # Test positive funding (short bias)
        result = self.adapter.detect_funding_bias(0.01)
        self.assertEqual(result, -1)  # Short bias

        # Test neutral funding
        result = self.adapter.detect_funding_bias(0.002)  # Below threshold
        self.assertEqual(result, 0)  # Neutral


class TestCryptoMTFTrendStrategyAdapter(unittest.TestCase):
    """Test cases for CryptoMTFTrendStrategyAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = CryptoMTFTrendStrategyAdapter()

    def test_init_sets_correct_attributes(self):
        """Test that CryptoMTFTrendStrategyAdapter is initialized with correct attributes."""
        self.assertEqual(self.adapter.name, "CryptoMTFTrend")
        self.assertIn("3m", self.adapter.timeframes)
        self.assertIn("15m", self.adapter.timeframes)
        self.assertIn("1h", self.adapter.timeframes)
        self.assertIn("4h", self.adapter.timeframes)
        self.assertIn("1D", self.adapter.timeframes)
        self.assertEqual(self.adapter.trend_period, 50)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            "trend_period": 80,
            "tf_weights": {
                "3m": 0.15,
                "15m": 0.25,
                "1h": 0.30,
                "4h": 0.20,
                "1D": 0.10
            }
        }
        adapter = CryptoMTFTrendStrategyAdapter(config)
        self.assertEqual(adapter.trend_period, 80)
        self.assertEqual(adapter.weighting, config["tf_weights"])

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns correct name."""
        self.assertEqual(self.adapter.get_strategy_name(), "CryptoMTFTrend")

    def test_generate_signal_returns_signal(self):
        """Test that generate_signal returns a valid signal."""
        symbol = Symbol("BTCUSDT")

        signal = self.adapter.generate_signal(symbol)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL, SignalType.HOLD, SignalType.NEUTRAL])
        self.assertIsInstance(signal.confidence, Percentage)
        self.assertIsInstance(signal.score, float)
        self.assertEqual(signal.strategy_name, "CryptoMTFTrend")


class TestCryptoVWAPReversalStrategyAdapter(unittest.TestCase):
    """Test cases for CryptoVWAPReversalStrategyAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = CryptoVWAPReversalStrategyAdapter()

    def test_init_sets_correct_attributes(self):
        """Test that CryptoVWAPReversalStrategyAdapter is initialized with correct attributes."""
        self.assertEqual(self.adapter.name, "CryptoVWAPReversal")
        self.assertEqual(self.adapter.lookback, 200)
        self.assertEqual(self.adapter.std_mult, 2.0)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            "lookback": 250,
            "std_mult": 2.5
        }
        adapter = CryptoVWAPReversalStrategyAdapter(config)
        self.assertEqual(adapter.lookback, 250)
        self.assertEqual(adapter.std_mult, 2.5)

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns correct name."""
        self.assertEqual(self.adapter.get_strategy_name(), "CryptoVWAPReversal")

    def test_generate_signal_returns_signal(self):
        """Test that generate_signal returns a valid signal."""
        symbol = Symbol("BTCUSDT")

        signal = self.adapter.generate_signal(symbol)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL, SignalType.HOLD, SignalType.NEUTRAL])
        self.assertIsInstance(signal.confidence, Percentage)
        self.assertIsInstance(signal.score, float)
        self.assertEqual(signal.strategy_name, "CryptoVWAPReversal")


class TestCryptoOIFootprintStrategyAdapter(unittest.TestCase):
    """Test cases for CryptoOIFootprintStrategyAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = CryptoOIFootprintStrategyAdapter()

    def test_init_sets_correct_attributes(self):
        """Test that CryptoOIFootprintStrategyAdapter is initialized with correct attributes."""
        self.assertEqual(self.adapter.name, "CryptoOIFootprint")
        self.assertEqual(self.adapter.oi_expansion, 0.05)
        self.assertEqual(self.adapter.delta_strength, 5)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            "oi_expansion": 0.08,
            "delta_strength": 7
        }
        adapter = CryptoOIFootprintStrategyAdapter(config)
        self.assertEqual(adapter.oi_expansion, 0.08)
        self.assertEqual(adapter.delta_strength, 7)

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns correct name."""
        self.assertEqual(self.adapter.get_strategy_name(), "CryptoOIFootprint")

    def test_generate_signal_returns_signal(self):
        """Test that generate_signal returns a valid signal."""
        symbol = Symbol("BTCUSDT")

        signal = self.adapter.generate_signal(symbol)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL, SignalType.HOLD, SignalType.NEUTRAL])
        self.assertIsInstance(signal.confidence, Percentage)
        self.assertIsInstance(signal.score, float)
        self.assertEqual(signal.strategy_name, "CryptoOIFootprint")


class TestCryptoSweepScalperAdapter(unittest.TestCase):
    """Test cases for CryptoSweepScalperAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.adapter = CryptoSweepScalperAdapter()

    def test_init_sets_correct_attributes(self):
        """Test that CryptoSweepScalperAdapter is initialized with correct attributes."""
        self.assertEqual(self.adapter.name, "CryptoSweepScalper")
        self.assertIn("UTC-13:00", self.adapter.killzone)
        self.assertIn("UTC-01:00", self.adapter.killzone)
        self.assertEqual(self.adapter.lookback, 4)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            "killzone": ["UTC-05:00", "UTC-17:00"],
            "lookback": 5
        }
        adapter = CryptoSweepScalperAdapter(config)
        self.assertIn("UTC-05:00", adapter.killzone)
        self.assertEqual(adapter.lookback, 5)

    def test_get_strategy_name_returns_correct_name(self):
        """Test that get_strategy_name returns correct name."""
        self.assertEqual(self.adapter.get_strategy_name(), "CryptoSweepScalper")

    def test_generate_signal_returns_signal(self):
        """Test that generate_signal returns a valid signal."""
        symbol = Symbol("BTCUSDT")

        signal = self.adapter.generate_signal(symbol)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL, SignalType.HOLD, SignalType.NEUTRAL])
        self.assertIsInstance(signal.confidence, Percentage)
        self.assertIsInstance(signal.score, float)
        self.assertEqual(signal.strategy_name, "CryptoSweepScalper")


if __name__ == '__main__':
    unittest.main()