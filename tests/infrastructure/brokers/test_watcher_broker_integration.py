"""
Unit tests for the enhanced watcher-broker integration system.
These tests verify that watchers can be assigned to different brokers as required.
"""
import unittest
import os
import sys
from unittest.mock import Mock, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.configs.hexagonal_settings import config
from infrastructure.brokers.broker_manager import BrokerManager
from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter
from infrastructure.brokers.adapters.binance_adapter import BinanceBrokerAdapter
from infrastructure.brokers.adapters.mexc_adapter import MEXCBrokerAdapter
from infrastructure.brokers.adapters.phemex_adapter import PhemexBrokerAdapter
from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
from infrastructure.watchers.adapters.volatility import VolatilityWatcher
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
from infrastructure.watchers.adapters.orderflow_ws import OrderFlowWSWatcher
from domain.value_objects import Symbol


class TestWatcherBrokerIntegration(unittest.TestCase):
    """Test the watcher-broker integration functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create mock broker configurations
        self.bingx_config = {'api_key': 'test', 'secret_key': 'test', 'testnet': True}
        self.binance_config = {'api_key': 'test', 'secret_key': 'test'}
        self.mexc_config = {'api_key': 'test', 'secret_key': 'test'}
        self.phemex_config = {'api_key': 'test', 'secret_key': 'test'}

        # Create broker instances
        self.bingx_broker = BingXBrokerAdapter(self.bingx_config)
        self.binance_broker = BinanceBrokerAdapter(**self.binance_config)
        self.mexc_broker = MEXCBrokerAdapter(**self.mexc_config)
        self.phemex_broker = PhemexBrokerAdapter(**self.phemex_config)

        # Create broker manager
        self.brokers = {
            "bingx": self.bingx_broker,
            "binance": self.binance_broker,
            "mexc": self.mexc_broker,
            "phemex": self.phemex_broker,
        }
        self.broker_mapping = {
            "futures": "bingx",
            "spot_binance": "binance",
            "spot_mexc": "mexc",
            "futures_phemex": "phemex",
        }
        self.broker_manager = BrokerManager(brokers=self.brokers, broker_mapping=self.broker_mapping)

    def test_config_broker_selection(self):
        """Test that config properly returns broker for each watcher."""
        # Test default broker
        default_broker = config.get_broker_for_watcher("NonExistentWatcher")
        self.assertEqual(default_broker, config.default_broker)
        
        # Test specific broker assignment
        original_config = config.watcher_broker_config.copy()
        config.watcher_broker_config = {"MarketPulse": "Binance"}
        
        broker = config.get_broker_for_watcher("MarketPulse")
        self.assertEqual(broker, "Binance")
        
        # Restore original config
        config.watcher_broker_config = original_config

    def test_environment_variable_config_loading(self):
        """Test environment variable configuration loading."""
        original_env = os.environ.get('WATCHER_BROKER_CONFIG')
        
        # Set environment variable
        os.environ['WATCHER_BROKER_CONFIG'] = 'MarketPulse:Binance,Volatility:MEXC'
        
        # Create new config to test loading
        from application.configs.hexagonal_settings import HexagonalConfig
        test_config = HexagonalConfig()
        
        self.assertEqual(test_config.get_broker_for_watcher("MarketPulse"), "Binance")
        self.assertEqual(test_config.get_broker_for_watcher("Volatility"), "MEXC")
        
        # Restore original
        if original_env is not None:
            os.environ['WATCHER_BROKER_CONFIG'] = original_env
        else:
            if 'WATCHER_BROKER_CONFIG' in os.environ:
                del os.environ['WATCHER_BROKER_CONFIG']

    def test_broker_manager_enhancement(self):
        """Test that broker manager has the new get_broker_by_name method."""
        # Test original functionality
        broker = self.broker_manager.get_broker("futures")
        self.assertEqual(broker, self.bingx_broker)
        
        # Test new functionality
        broker = self.broker_manager.get_broker_by_name("binance")
        self.assertEqual(broker, self.binance_broker)

    def test_watcher_broker_injection(self):
        """Test that watchers can be created with broker service injection."""
        # Create a watcher with specific broker
        watcher = MarketPulseWatcher(
            name="MarketPulse", 
            symbol="BTC-USDT", 
            broker_service=self.broker_manager, 
            target_broker="binance"
        )
        
        # Verify attributes
        self.assertEqual(watcher.target_broker, "binance")
        self.assertEqual(watcher.broker_service, self.broker_manager)
        
        # Test broker retrieval
        broker = watcher.get_broker()
        self.assertEqual(broker, self.binance_broker)

    def test_watcher_default_broker(self):
        """Test that watchers use default broker when none specified."""
        watcher = MarketPulseWatcher(
            name="MarketPulse", 
            symbol="BTC-USDT", 
            broker_service=self.broker_manager
        )
        
        self.assertEqual(watcher.target_broker, "bingx")  # Default
        
        broker = watcher.get_broker()
        self.assertEqual(broker, self.bingx_broker)

    def test_all_watcher_types_support_broker_injection(self):
        """Test that all watcher types support broker injection."""
        watchers = [
            MarketPulseWatcher("MarketPulse", "BTC-USDT", self.broker_manager, "binance"),
            VolatilityWatcher("Volatility", "BTC-USDT", self.broker_manager, "mexc"),
            TrendMTFWatcher("TrendMTF", "BTC-USDT", self.broker_manager, "phemex"),
            AnomalyMLWatcher("AnomalyML", "BTC-USDT", self.broker_manager, "bingx"),
            OrderFlowWSWatcher("OrderFlow", "BTC-USDT", self.broker_manager, "binance")
        ]
        
        expected_brokers = [
            self.binance_broker,
            self.mexc_broker,
            self.phemex_broker,
            self.bingx_broker,
            self.binance_broker
        ]
        
        for i, (watcher, expected_broker) in enumerate(zip(watchers, expected_brokers)):
            with self.subTest(watcher=watcher.name):
                broker = watcher.get_broker()
                self.assertEqual(broker, expected_broker)

    def test_watcher_signal_generation_with_broker(self):
        """Test that watchers can generate signals when configured with brokers."""
        from domain.value_objects import Symbol
        watcher = VolatilityWatcher("Volatility", "BTC-USDT", self.broker_manager, "bingx")

        # Feed data to generate a signal
        for i in range(20):
            mock_data = {'close': 45000.0 + (i * 5 if i < 10 else -i * 3)}
            watcher.update_data(mock_data)

        # This should not raise an exception
        signal = watcher.analyze(Symbol("BTC-USDT"))
        # Signal might be None if conditions aren't met - that's OK for this test

        # Verify watcher still has access to broker
        broker = watcher.get_broker()
        self.assertEqual(broker, self.bingx_broker)

    def test_watcher_with_different_brokers_generates_signals(self):
        """Test that watchers work with different brokers and can generate signals."""
        from domain.value_objects import Symbol
        # Create watchers for different brokers
        bingx_watcher = MarketPulseWatcher("MarketPulse", "BTC-USDT", self.broker_manager, "bingx")
        binance_watcher = MarketPulseWatcher("MarketPulse2", "BTC-USDT", self.broker_manager, "binance")

        # Feed identical data to both watchers
        common_data = [
            {'close': 45000.0 + i * 10, 'volume': 1000.0 + i * 50}
            for i in range(25)
        ]

        for data_point in common_data:
            bingx_watcher.update_data(data_point)
            binance_watcher.update_data(data_point)

        # Both should be able to generate signals independently
        bingx_signal = bingx_watcher.analyze(Symbol("BTC-USDT"))
        binance_signal = binance_watcher.analyze(Symbol("BTC-USDT"))

        # Verify each uses the correct broker
        bingx_broker = bingx_watcher.get_broker()
        binance_broker = binance_watcher.get_broker()

        self.assertEqual(bingx_broker, self.bingx_broker)
        self.assertEqual(binance_broker, self.binance_broker)

    def test_market_pulse_watcher_with_different_brokers(self):
        """Test MarketPulse watcher with different brokers"""
        from domain.value_objects import Symbol

        # Test with BingX (default)
        watcher_bingx = MarketPulseWatcher(
            name="MarketPulse_BingX",
            symbol="BTC-USDT",
            broker_service=self.broker_manager,
            target_broker="bingx"
        )

        # Feed test data
        for i in range(25):
            price = 45000.0 + (i * 10 if i < 15 else 45150.0 - (i-15) * 8)
            data = {'close': price, 'volume': 1000.0 + i * 50}
            watcher_bingx.update_data(data)

        signal = watcher_bingx.analyze(Symbol("BTC-USDT"))
        self.assertIsNotNone(signal)  # Should generate a signal
        print(f"MarketPulse-BingX analyzed BTC-USDT, signal: {signal.signal_type if signal else 'None'}")

        # Test with Binance
        watcher_binance = MarketPulseWatcher(
            name="MarketPulse_Binance",
            symbol="ETH-USDT",
            broker_service=self.broker_manager,
            target_broker="binance"
        )

        for i in range(25):
            price = 3000.0 + (i * 2 if i < 15 else 3030.0 - (i-15) * 1.5)
            data = {'close': price, 'volume': 2000.0 + i * 30}
            watcher_binance.update_data(data)

        signal = watcher_binance.analyze(Symbol("ETH-USDT"))
        self.assertIsNotNone(signal)
        print(f"MarketPulse-Binance analyzed ETH-USDT, signal: {signal.signal_type if signal else 'None'}")

    def test_volatility_watcher_with_different_brokers(self):
        """Test Volatility watcher with different brokers"""
        from domain.value_objects import Symbol

        # Test with BingX (default)
        watcher_bingx = VolatilityWatcher(
            name="Volatility_BingX",
            symbol="BTC-USDT",
            broker_service=self.broker_manager,
            target_broker="bingx"
        )

        # Feed test data with some volatility
        for i in range(50):
            base_price = 45000.0
            if i < 25:
                price = base_price + (i % 5) * 20  # Some variation
            else:
                price = base_price + ((i-25) % 7) * 30  # Different variation
            data = {'close': price}
            watcher_bingx.update_data(data)

        signal = watcher_bingx.analyze(Symbol("BTC-USDT"))
        self.assertIsNotNone(signal)
        print(f"Volatility-BingX analyzed BTC-USDT, signal: {signal.signal_type if signal else 'None'}")

        # Test with MEXC
        watcher_mexc = VolatilityWatcher(
            name="Volatility_MEXC",
            symbol="SOL-USDT",
            broker_service=self.broker_manager,
            target_broker="mexc"
        )

        for i in range(50):
            base_price = 150.0
            if i < 25:
                price = base_price + (i % 3) * 5
            else:
                price = base_price + ((i-25) % 5) * 10
            data = {'close': price}
            watcher_mexc.update_data(data)

        signal = watcher_mexc.analyze(Symbol("SOL-USDT"))
        self.assertIsNotNone(signal)
        print(f"Volatility-MEXC analyzed SOL-USDT, signal: {signal.signal_type if signal else 'None'}")

    def test_trend_mtf_watcher_with_different_brokers(self):
        """Test TrendMTF watcher with different brokers"""
        from domain.value_objects import Symbol

        # Test with BingX (default)
        watcher_bingx = TrendMTFWatcher(
            name="TrendMTF_BingX",
            symbol="BTC-USDT",
            broker_service=self.broker_manager,
            target_broker="bingx"
        )

        # Feed test data - upward then downward trend
        for i in range(40):
            if i < 20:
                price = 45000.0 + i * 100  # Upward trend
            else:
                price = 47000.0 - (i-19) * 80  # Downward trend
            data = {'close': price}
            watcher_bingx.update_data(data)

        signal = watcher_bingx.analyze(Symbol("BTC-USDT"))
        self.assertIsNotNone(signal)
        print(f"TrendMTF-BingX analyzed BTC-USDT, signal: {signal.signal_type if signal else 'None'}")

        # Test with Phemex
        watcher_phemex = TrendMTFWatcher(
            name="TrendMTF_Phemex",
            symbol="SOL-USDT",
            broker_service=self.broker_manager,
            target_broker="phemex"
        )

        # Feed test data - downward then upward (reversal pattern)
        for i in range(40):
            if i < 20:
                price = 150.0 - i * 2  # Downward
            else:
                price = 110.0 + (i-19) * 3  # Upward reversal
            data = {'close': price}
            watcher_phemex.update_data(data)

        signal = watcher_phemex.analyze(Symbol("SOL-USDT"))
        self.assertIsNotNone(signal)
        print(f"TrendMTF-Phemex analyzed SOL-USDT, signal: {signal.signal_type if signal else 'None'}")

    def test_anomaly_ml_watcher_with_different_brokers(self):
        """Test AnomalyML watcher with different brokers"""
        from domain.value_objects import Symbol

        # Test with BingX (default)
        watcher_bingx = AnomalyMLWatcher(
            name="AnomalyML_BingX",
            symbol="BTC-USDT",
            broker_service=self.broker_manager,
            target_broker="bingx"
        )

        # Feed test data with normal patterns first, then anomalous
        for i in range(60):
            if i < 30:
                price = 45000.0 + i * 5  # Normal trend
            else:
                # Create anomalous pattern - sudden jump
                price = 46500.0 + (i-29) * 8 + (i-29) ** 1.5  # Accelerating anomaly
            data = {'close': price}
            watcher_bingx.update_data(data)

        signal = watcher_bingx.analyze(Symbol("BTC-USDT"))
        self.assertIsNotNone(signal)
        print(f"AnomalyML-BingX analyzed BTC-USDT, signal: {signal.signal_type if signal else 'None'}")

        # Test with Binance
        watcher_binance = AnomalyMLWatcher(
            name="AnomalyML_Binance",
            symbol="ETH-USDT",
            broker_service=self.broker_manager,
            target_broker="binance"
        )

        # Feed test data - stable pattern
        for i in range(60):
            price = 3000.0 + (i % 10) * 3  # Stable oscillation
            data = {'close': price}
            watcher_binance.update_data(data)

        signal = watcher_binance.analyze(Symbol("ETH-USDT"))
        self.assertIsNotNone(signal)
        print(f"AnomalyML-Binance analyzed ETH-USDT, signal: {signal.signal_type if signal else 'None'}")

    def test_orderflow_ws_watcher_with_different_brokers(self):
        """Test OrderFlowWS watcher with different brokers"""
        from domain.value_objects import Symbol

        # Test with BingX (default)
        watcher_bingx = OrderFlowWSWatcher(
            name="OrderFlow_BingX",
            symbol="BTC-USDT",
            broker_service=self.broker_manager,
            target_broker="bingx"
        )

        # Simulate order book data
        for i in range(20):
            # Simulate bids and asks
            base_price = 45000.0
            bids = [(base_price - j*10, 100 + j*10) for j in range(5)]  # 5 bid levels
            asks = [(base_price + j*10, 80 + j*8) for j in range(5)]    # 5 ask levels
            data = {'bids': bids, 'asks': asks}
            watcher_bingx.update_data(data)

        signal = watcher_bingx.analyze(Symbol("BTC-USDT"))
        self.assertIsNotNone(signal)
        print(f"OrderFlow-BingX analyzed BTC-USDT, signal: {signal.signal_type if signal else 'None'}")

        # Test with Phemex
        watcher_phemex = OrderFlowWSWatcher(
            name="OrderFlow_Phemex",
            symbol="SOL-USDT",
            broker_service=self.broker_manager,
            target_broker="phemex"
        )

        # Simulate bearish order flow
        for i in range(20):
            base_price = 150.0
            # More aggressive selling pressure
            bids = [(base_price - j*2, 80 + j*8) for j in range(5)]
            asks = [(base_price + j*2, 120 + j*12) for j in range(5)]
            data = {'bids': bids, 'asks': asks}
            watcher_phemex.update_data(data)

        signal = watcher_phemex.analyze(Symbol("SOL-USDT"))
        self.assertIsNotNone(signal)
        print(f"OrderFlow-Phemex analyzed SOL-USDT, signal: {signal.signal_type if signal else 'None'}")


class TestConfigIntegration(unittest.TestCase):
    """Test configuration integration with broker-watcher system."""

    def test_config_defaults(self):
        """Test that configuration has proper defaults."""
        self.assertEqual(config.default_broker, "BingX")
        self.assertIsInstance(config.watcher_broker_config, dict)

    def test_get_broker_for_watcher_method(self):
        """Test the get_broker_for_watcher method."""
        # Should return default when no specific config
        broker = config.get_broker_for_watcher("UnknownWatcher")
        self.assertEqual(broker, config.default_broker)
        
        # Save original config
        original_config = config.watcher_broker_config.copy()
        
        # Test specific assignment
        config.watcher_broker_config = {"TestWatcher": "Binance"}
        broker = config.get_broker_for_watcher("TestWatcher")
        self.assertEqual(broker, "Binance")
        
        # Restore original config
        config.watcher_broker_config = original_config


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)