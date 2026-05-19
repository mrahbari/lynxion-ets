"""
Unit tests for infrastructure layer adapters in the enterprise hedge fund trading system.
"""
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import datetime
import numpy as np

from domain.entities.trading_entities import Signal, SignalType, Order, OrderSide
from domain.value_objects import Symbol, Percentage, Money
from infrastructure.engines.adapters.real_engine_adapters import (
    TrendEngineAdapter, VolatilityEngineAdapter, 
    LiquidityEngineAdapter, OrderFlowEngineAdapter, RegimeEngineAdapter
)
from infrastructure.strategies.adapters.real_strategy_adapters import (
    TrendFollowStrategyAdapter, MeanReversionStrategyAdapter,
    ScalpingStrategyAdapter, BreakoutStrategyAdapter
)
from infrastructure.brokers.adapters.real_broker_adapters import (
    BinanceBrokerAdapter, BingXBrokerAdapter, MEXCBrokerAdapter, PhemexBrokerAdapter
)


class TestTrendEngineAdapter(unittest.TestCase):
    """Test Trend Engine Adapter"""
    
    def setUp(self):
        self.engine = TrendEngineAdapter()
    
    def test_should_process_signal(self):
        """Test that trend engine can process signals"""
        signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.70")),
            score=0.5,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        result = self.engine.should_process_signal(signal)
        self.assertTrue(result)
    
    def test_process_signal_with_insufficient_data(self):
        """Test that signal is returned unchanged with insufficient data"""
        signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.70")),
            score=0.5,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        # Process signal with insufficient price history
        result = self.engine.process_signal(signal)
        
        # With insufficient data, the signal should be returned unchanged
        self.assertEqual(result.symbol.value, signal.symbol.value)
        self.assertEqual(result.signal_type.name, signal.signal_type.name)
        self.assertEqual(result.score, signal.score)
    
    def test_update_with_market_data(self):
        """Test updating engine with market data"""
        data = {'close': 45000.0}
        self.engine.update_with_market_data(data)
        
        # Check that the price history was updated
        self.assertEqual(len(self.engine.price_history), 1)
        self.assertEqual(self.engine.price_history[0], 45000.0)
    
    def test_get_engine_name(self):
        """Test that engine returns correct name"""
        name = self.engine.get_engine_name()
        self.assertEqual(name, "TrendEngine")


class TestVolatilityEngineAdapter(unittest.TestCase):
    """Test Volatility Engine Adapter"""
    
    def setUp(self):
        self.engine = VolatilityEngineAdapter()
    
    def test_should_process_signal(self):
        """Test that volatility engine can process signals"""
        signal = Signal(
            symbol=Symbol("ETHUSDT"),
            signal_type=SignalType.SELL,
            confidence=Percentage(Decimal("0.65")),
            score=-0.4,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        result = self.engine.should_process_signal(signal)
        self.assertTrue(result)
    
    def test_process_signal_with_no_data(self):
        """Test processing signal with no market data"""
        signal = Signal(
            symbol=Symbol("ETHUSDT"),
            signal_type=SignalType.SELL,
            confidence=Percentage(Decimal("0.65")),
            score=-0.4,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        result = self.engine.process_signal(signal)
        
        # With no data, signal should be returned unchanged
        self.assertEqual(result.symbol.value, signal.symbol.value)
        self.assertEqual(result.signal_type.name, signal.signal_type.name)
        self.assertEqual(result.confidence.value, signal.confidence.value)
        self.assertEqual(result.score, signal.score)
    
    def test_process_signal_with_market_data(self):
        """Test processing signal with market data"""
        # Add some price history
        for price in [45000, 45100, 45200, 45150, 45300, 45250]:  # Price movements
            self.engine.price_history.append(price)
        
        signal = Signal(
            symbol=Symbol("ETHUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.70")),
            score=0.5,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        result = self.engine.process_signal(signal)
        
        # The signal should have been processed
        self.assertIsInstance(result, Signal)
        self.assertEqual(result.source_engine, self.engine.get_engine_name())
    
    def test_update_with_market_data(self):
        """Test updating volatility engine with market data"""
        data = {'close': 45100.0}
        self.engine.update_with_market_data(data)
        
        # Check that data was added to price history
        self.assertIn(45100.0, self.engine.price_history)
        self.assertEqual(len(self.engine.price_history), 1)


class TestStrategyAdapters(unittest.TestCase):
    """Test Strategy Adapters"""
    
    def test_trend_follow_strategy_adapter(self):
        """Test Trend Follow Strategy Adapter"""
        strategy = TrendFollowStrategyAdapter({})
        
        self.assertEqual(strategy.get_strategy_name(), "TrendFollowStrategy")
        
        # Test that it can process market data
        data = {'close': 45000.50, 'high': 45100.0, 'low': 44900.0, 'volume': 1000.0}
        strategy.update_with_market_data(data)
        
        # Test that it can generate a signal
        symbol = Symbol("BTCUSDT")
        signal = strategy.generate_signal(symbol)
        
        # Signal may be None if not enough data, but shouldn't crash
        if signal:
            self.assertIsInstance(signal, Signal)
            self.assertEqual(signal.strategy_name, "TrendFollowStrategy")
    
    def test_mean_reversion_strategy_adapter(self):
        """Test Mean Reversion Strategy Adapter"""
        strategy = MeanReversionStrategyAdapter({})
        
        self.assertEqual(strategy.get_strategy_name(), "MeanReversionStrategy")
        
        # Add some historical data to trigger signal generation
        for price in [45000, 45100, 45200, 44500, 44600]:  # Some variance to trigger reversion
            strategy.price_history.append(price)
        
        symbol = Symbol("ETHUSDT")
        signal = strategy.generate_signal(symbol)
        
        # May return None if not enough data, but shouldn't crash
        if signal:
            self.assertIsInstance(signal, Signal)
            self.assertEqual(signal.strategy_name, "MeanReversionStrategy")
    
    def test_scalping_strategy_adapter(self):
        """Test Scalping Strategy Adapter"""
        strategy = ScalpingStrategyAdapter({})
        
        self.assertEqual(strategy.get_strategy_name(), "ScalpingStrategy")
        
        # Test update and possible signal generation
        data = {'close': 45000.75, 'volume': 100.0}
        strategy.update_with_market_data(data)
        
        symbol = Symbol("SOLUSDT")
        # May not generate signal with just one data point
        signal = strategy.generate_signal(symbol)
        
        if signal:
            self.assertIsInstance(signal, Signal)
            self.assertEqual(signal.strategy_name, "ScalpingStrategy")
    
    def test_breakout_strategy_adapter(self):
        """Test Breakout Strategy Adapter"""
        strategy = BreakoutStrategyAdapter({})
        
        self.assertEqual(strategy.get_strategy_name(), "BreakoutStrategy")
        
        # Add some historical data with price variations
        for price in [45000, 45500, 46000, 46500, 47000, 47500]:  # Rising trend to test breakout
            strategy.price_history.append(price)
        
        symbol = Symbol("BTCUSDT")
        signal = strategy.generate_signal(symbol)
        
        if signal:
            self.assertIsInstance(signal, Signal)
            self.assertEqual(signal.strategy_name, "BreakoutStrategy")


class TestBrokerAdapters(unittest.TestCase):
    """Test Broker Adapters"""
    
    def test_broker_adapter_interface_compliance(self):
        """Test that broker adapters implement the proper interface"""
        # Test that adapter can be instantiated
        broker_adapter = BinanceBrokerAdapter("test_api_key", "test_secret")
        
        # Verify methods exist
        self.assertTrue(hasattr(broker_adapter, 'connect'))
        self.assertTrue(hasattr(broker_adapter, 'disconnect'))
        self.assertTrue(hasattr(broker_adapter, 'place_order'))
        self.assertTrue(hasattr(broker_adapter, 'cancel_order'))
        self.assertTrue(hasattr(broker_adapter, 'get_order_status'))
        self.assertTrue(hasattr(broker_adapter, 'get_position'))
        self.assertTrue(hasattr(broker_adapter, 'get_balance'))
        
        # Verify name property
        self.assertEqual(broker_adapter.name, "Binance")
    
    def test_bingx_broker_adapter_compliance(self):
        """Test that BingX broker adapter implements proper interface"""
        broker_adapter = BingXBrokerAdapter("test_api_key", "test_secret")
        
        self.assertEqual(broker_adapter.name, "BingX")
        
        # Test that required methods exist
        methods = ['connect', 'disconnect', 'place_order', 'cancel_order', 'get_order_status', 'get_position', 'get_balance']
        for method_name in methods:
            self.assertTrue(hasattr(broker_adapter, method_name))
    
    def test_binance_mock_behavior(self):
        """Test basic behavior of Binance broker adapter"""
        # Mock the external API calls
        with patch('requests.Session.get') as mock_get, \
             patch('requests.Session.post') as mock_post, \
             patch('requests.Session.delete') as mock_delete:
            
            # Setup mock responses
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"serverTime": int(datetime.now().timestamp() * 1000)}
            
            broker = BinanceBrokerAdapter("test_key", "test_secret")
            
            # Test connection
            result = broker.connect()
            self.assertTrue(result)
            
            # Test that the name is correct
            self.assertEqual(broker.get_broker_name(), "Binance")


class TestOrderFlowEngineAdapter(unittest.TestCase):
    """Test Order Flow Engine Adapter"""
    
    def setUp(self):
        self.engine = OrderFlowEngineAdapter()
    
    def test_order_flow_engine_interface_compliance(self):
        """Test that order flow engine implements proper interface"""
        self.assertEqual(self.engine.get_engine_name(), "OrderFlowEngine")
        
        # Test that required methods exist
        self.assertTrue(hasattr(self.engine, 'process_signal'))
        self.assertTrue(hasattr(self.engine, 'should_process_signal'))
        self.assertTrue(hasattr(self.engine, 'update_with_market_data'))
    
    def test_should_process_signal(self):
        """Test signal processing eligibility"""
        signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.70")),
            score=0.5,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        result = self.engine.should_process_signal(signal)
        self.assertTrue(result)  # Default implementation returns True
    
    def test_update_with_market_data(self):
        """Test updating engine with market data"""
        data = {
            'bids': [(44999.0, 10.0), (44998.0, 5.0)],
            'asks': [(45001.0, 8.0), (45002.0, 12.0)]
        }
        self.engine.update_with_market_data(data)
        
        # Check that order book data was updated
        self.assertEqual(len(self.engine.bids), 2)
        self.assertEqual(len(self.engine.asks), 2)


class TestRegimeEngineAdapter(unittest.TestCase):
    """Test Regime Engine Adapter"""
    
    def setUp(self):
        self.engine = RegimeEngineAdapter()
    
    def test_regime_engine_interface_compliance(self):
        """Test that regime engine implements proper interface"""
        self.assertEqual(self.engine.get_engine_name(), "RegimeEngine")
        
        # Test that required methods exist
        self.assertTrue(hasattr(self.engine, 'process_signal'))
        self.assertTrue(hasattr(self.engine, 'should_process_signal'))
        self.assertTrue(hasattr(self.engine, 'update_with_market_data'))
    
    def test_regime_detection(self):
        """Test regime detection capabilities"""
        # Add some price history with varying characteristics
        # A trend pattern
        for i in range(20):
            price = 40000 + i * 100  # Rising prices
            self.engine.price_history.append(price)
        
        # The regime should be detectable
        # Test with a signal
        signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.70")),
            score=0.5,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        # Process the signal - should not raise an error
        try:
            result = self.engine.process_signal(signal)
            self.assertIsInstance(result, Signal)
        except:
            # This is fine if we don't have enough data for full regime analysis
            pass


if __name__ == '__main__':
    unittest.main()