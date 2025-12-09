"""
Unit tests for application layer services in the enterprise hedge fund trading system.
"""
import unittest
from unittest.mock import Mock, MagicMock
from decimal import Decimal
from datetime import datetime
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage, Money
from application.services.engine_services import EngineManagementService
from application.services.strategy_services import StrategySelectionService
from application.services.trading_services import SignalProcessingService, OrderManagementService
from application.services.risk_services_app import RiskManagementService


class TestEngineManagementService(unittest.TestCase):
    """Test Engine Management Service"""
    
    def setUp(self):
        """Setup test engines for engine management"""
        self.mock_engine_1 = Mock()
        self.mock_engine_1.name = "MockEngine1"
        self.mock_engine_1.process_signal.return_value = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.75")),
            score=0.6,
            strategy_name="TestStrategy",
            timestamp=datetime.now(),
            source_engine="MockEngine1"
        )
        self.mock_engine_1.should_process_signal.return_value = True
        
        self.mock_engine_2 = Mock()
        self.mock_engine_2.name = "MockEngine2"
        self.mock_engine_2.process_signal.return_value = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.80")),
            score=0.7,
            strategy_name="TestStrategy",
            timestamp=datetime.now(),
            source_engine="MockEngine2"
        )
        self.mock_engine_2.should_process_signal.return_value = True
        
        self.engines = [self.mock_engine_1, self.mock_engine_2]
        self.service = EngineManagementService(self.engines)
    
    def test_process_signal_through_all_engines(self):
        """Test processing a signal through all engines"""
        original_signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.70")),
            score=0.5,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        # Process through engines
        processed_signal = self.service.process_signal_through_all_engines(original_signal)
        
        # Verify that all engines were called appropriately
        self.mock_engine_1.process_signal.assert_called_once()
        self.mock_engine_2.process_signal.assert_called_once()
        
        # The processed signal should have been updated by the last engine
        self.assertEqual(processed_signal.source_engine, "MockEngine2")
    
    def test_process_signal_with_none_engines(self):
        """Test processing when engines return None"""
        self.mock_engine_1.process_signal.return_value = None
        self.mock_engine_2.process_signal.return_value = None
        
        original_signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.70")),
            score=0.5,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        processed_signal = self.service.process_signal_through_all_engines(original_signal)
        
        # Should return original signal when all engines return None
        self.assertEqual(processed_signal.score, original_signal.score)


class TestStrategySelectionService(unittest.TestCase):
    """Test Strategy Selection Service"""
    
    def setUp(self):
        """Setup test strategies for strategy selection"""
        self.mock_strategy_1 = Mock()
        self.mock_strategy_1.get_strategy_name.return_value = "TestStrategy1"
        self.mock_strategy_1.generate_signal.return_value = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.70")),
            score=0.5,
            strategy_name="TestStrategy1",
            timestamp=datetime.now()
        )
        
        self.mock_strategy_2 = Mock()
        self.mock_strategy_2.get_strategy_name.return_value = "TestStrategy2"
        self.mock_strategy_2.generate_signal.return_value = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.SELL,
            confidence=Percentage(Decimal("0.80")),
            score=-0.6,
            strategy_name="TestStrategy2",
            timestamp=datetime.now()
        )
        
        self.strategies = [self.mock_strategy_1, self.mock_strategy_2]
        self.service = StrategySelectionService(self.strategies)
    
    def test_select_strategy_by_index(self):
        """Test selecting a strategy by index"""
        strategy = self.service.select_strategy_by_index(0)
        self.assertIs(strategy, self.mock_strategy_1)
        
        strategy = self.service.select_strategy_by_index(1)
        self.assertIs(strategy, self.mock_strategy_2)
    
    def test_generate_signal_with_selected_strategy(self):
        """Test generating a signal with a selected strategy"""
        symbol = Symbol("BTCUSDT")
        
        signal = self.service.generate_signal_with_strategy(0, symbol)
        
        self.assertIsNotNone(signal)
        self.assertEqual(signal.strategy_name, "TestStrategy1")
        self.mock_strategy_1.generate_signal.assert_called_once_with(symbol)
    
    def test_get_all_strategy_names(self):
        """Test getting all strategy names"""
        names = self.service.get_all_strategy_names()
        self.assertEqual(names, ["TestStrategy1", "TestStrategy2"])


class TestSignalProcessingService(unittest.TestCase):
    """Test Signal Processing Service"""
    
    def setUp(self):
        """Setup service for testing"""
        self.mock_strategy_service = Mock()
        self.mock_engine_service = Mock()
        self.mock_fusion_service = Mock()
        
        self.service = SignalProcessingService(
            self.mock_strategy_service,
            self.mock_engine_service,
            self.mock_fusion_service
        )
    
    def test_generate_and_process_signal(self):
        """Test complete signal generation and processing flow"""
        symbol = Symbol("BTCUSDT")
        mock_signal = Signal(
            symbol=symbol,
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.75")),
            score=0.6,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        # Setup mocks
        self.mock_strategy_service.generate_and_process_signal.return_value = mock_signal
        self.mock_engine_service.process_signal_through_all_engines.return_value = mock_signal
        self.mock_fusion_service.process_multiple_signals.return_value = mock_signal
        
        # Execute the service
        result = self.service.generate_and_process_signal(symbol)
        
        # Verify methods were called
        self.mock_strategy_service.generate_and_process_signal.assert_called_once_with(symbol)
        self.mock_engine_service.process_signal_through_all_engines.assert_called_once_with(mock_signal)
    
    def test_fuse_multiple_signals(self):
        """Test fusing multiple signals"""
        signals = [
            Signal(
                symbol=Symbol("BTCUSDT"),
                signal_type=SignalType.BUY,
                confidence=Percentage(Decimal("0.70")),
                score=0.5,
                strategy_name="Strategy1",
                timestamp=datetime.now()
            ),
            Signal(
                symbol=Symbol("BTCUSDT"),
                signal_type=SignalType.SELL,
                confidence=Percentage(Decimal("0.60")),
                score=-0.4,
                strategy_name="Strategy2",
                timestamp=datetime.now()
            )
        ]
        
        fused_signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.NEUTRAL,
            confidence=Percentage(Decimal("0.65")),
            score=0.1,
            strategy_name="FusionStrategy",
            timestamp=datetime.now()
        )
        self.mock_fusion_service.process_multiple_signals.return_value = fused_signal
        
        result = self.service.fuse_multiple_signals(signals)
        
        self.mock_fusion_service.process_multiple_signals.assert_called_once_with(signals)
        self.assertEqual(result, fused_signal)


class TestOrderManagementService(unittest.TestCase):
    """Test Order Management Service"""
    
    def setUp(self):
        """Setup service for testing"""
        self.mock_broker = Mock()
        self.mock_risk_service = Mock()
        
        self.service = OrderManagementService(
            self.mock_broker,
            self.mock_risk_service
        )
    
    def test_place_order_with_risk_validation(self):
        """Test placing an order with risk validation"""
        order = Mock()
        order.symbol = Symbol("BTCUSDT")
        order.id = "test_order_123"
        
        # Setup mocks
        self.mock_risk_service.validate_order_risk.return_value = True
        self.mock_broker.place_order.return_value = "broker_order_123"
        
        result = self.service.place_order_with_validation(order)
        
        # Verify that risk validation was called
        self.mock_risk_service.validate_order_risk.assert_called_once_with(order)
        # Verify that order placement was called
        self.mock_broker.place_order.assert_called_once_with(order)
        self.assertEqual(result, "broker_order_123")
    
    def test_place_order_rejected_by_risk(self):
        """Test that orders rejected by risk validation are not placed"""
        order = Mock()
        order.symbol = Symbol("BTCUSDT")
        
        # Setup mocks
        self.mock_risk_service.validate_order_risk.return_value = False
        
        result = self.service.place_order_with_validation(order)
        
        # Verify that risk validation was called
        self.mock_risk_service.validate_order_risk.assert_called_once_with(order)
        # Verify that order placement was NOT called
        self.mock_broker.place_order.assert_not_called()
        self.assertIsNone(result)


class TestRiskManagementService(unittest.TestCase):
    """Test Risk Management Service"""
    
    def setUp(self):
        """Setup service for testing"""
        self.mock_risk_governor = Mock()
        self.service = RiskManagementService(self.mock_risk_governor)
    
    def test_validate_signal_risk(self):
        """Test validating signal risk"""
        signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.70")),
            score=0.5,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        # Setup mocks
        self.mock_risk_governor.validate_signal.return_value = True
        
        result = self.service.validate_signal_risk(signal)
        
        self.mock_risk_governor.validate_signal.assert_called_once_with(signal)
        self.assertTrue(result)
    
    def test_check_portfolio_risk(self):
        """Test checking portfolio risk"""
        self.mock_risk_governor.check_portfolio_risk.return_value = True
        result = self.service.check_portfolio_risk()
        
        self.assertTrue(result)
        self.mock_risk_governor.check_portfolio_risk.assert_called_once()


if __name__ == '__main__':
    unittest.main()