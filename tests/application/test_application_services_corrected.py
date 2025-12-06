"""
Unit tests for application layer services in the enterprise hedge fund trading system.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from datetime import datetime
from domain.entities.trading_entities import Signal, Order, Position, SignalType
from domain.value_objects import Symbol, Money, Percentage
from application.services.trading_services import SignalProcessingService, TradingExecutionService
from application.services.engine_services import EngineManagementService
from application.services.strategy_services import StrategySelectionService
from application.services.risk_services_app import RiskManagementService


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
        self.mock_strategy_service.generate_signal.return_value = mock_signal
        self.mock_engine_service.process_signal_through_all_engines.return_value = mock_signal
        self.mock_fusion_service.process_multiple_signals.return_value = mock_signal
        
        # Execute the service
        result = self.service.generate_and_process_signal(symbol)
        
        # Verify methods were called
        self.mock_strategy_service.generate_signal.assert_called_once_with(symbol)
        self.mock_engine_service.process_signal_through_all_engines.assert_called_once_with(mock_signal)
    
    def test_process_multiple_signals(self):
        """Test processing multiple signals"""
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
        
        result = self.service.process_multiple_signals(signals)
        
        self.mock_fusion_service.process_multiple_signals.assert_called_once_with(signals)
        self.assertEqual(result, fused_signal)


class TestEngineManagementService(unittest.TestCase):
    """Test Engine Management Service"""
    
    def setUp(self):
        """Setup test engines for engine management"""
        self.mock_engine_1 = Mock()
        self.mock_engine_1.get_engine_name.return_value = "MockEngine1"
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
        self.mock_engine_2.get_engine_name.return_value = "MockEngine2"
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
        # (this would depend on how the service processes the signal)
    
    def test_get_engine_status(self):
        """Test getting engine status"""
        status = self.service.get_engine_status()
        self.assertEqual(len(status), 2)
        self.assertIn('engine_name', status[0])
        self.assertIn('can_process_signal', status[0])


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
    
    def test_execute_strategy_cycle(self):
        """Test executing a complete strategy cycle"""
        symbol = Symbol("BTCUSDT")
        
        result = self.service.execute_strategy_cycle(symbol)
        
        # Verify method was called
        self.assertIsNotNone(result)
        self.mock_strategy_1.generate_signal.assert_called_once()
        self.assertIn(result.strategy_name, ["TestStrategy1", "TestStrategy2"])


class TestRiskManagementService(unittest.TestCase):
    """Test Risk Management Service"""
    
    def setUp(self):
        """Setup service for testing"""
        self.mock_risk_governor = Mock()
        self.service = RiskManagementService(
            self.mock_risk_governor
        )
    
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


class TestTradingExecutionService(unittest.TestCase):
    """Test Trading Execution Service"""
    
    def setUp(self):
        """Setup service for testing"""
        self.mock_order_service = Mock()
        self.mock_execution_algorithms = [Mock(), Mock()]
        
        self.service = TradingExecutionService(
            self.mock_order_service,
            self.mock_execution_algorithms
        )
    
    def test_execute_signal(self):
        """Test executing a trading signal"""
        signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal("0.75")),
            score=0.6,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        # Setup mocks
        self.mock_order_service.create_order_from_signal.return_value = Order(
            symbol=Symbol("BTCUSDT"),
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            order_type="MARKET",
            timestamp=datetime.now()
        )
        self.mock_execution_algorithms[0].execute_order.return_value = "EXEC_ID_123"
        
        result = self.service.execute_signal(signal)
        
        self.assertIsNotNone(result)
        self.mock_order_service.create_order_from_signal.assert_called_once_with(signal)
    
    def test_execute_signal_with_algorithm(self):
        """Test executing a signal with specific algorithm"""
        signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.SELL,
            confidence=Percentage(Decimal("0.65")),
            score=-0.4,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        # Setup mocks
        order = Order(
            symbol=Symbol("BTCUSDT"),
            side=OrderSide.SELL,
            quantity=Decimal("0.05"),
            order_type="LIMIT",
            price=Money(Decimal("44000"), "USDT"),
            timestamp=datetime.now()
        )
        self.mock_order_service.create_order_from_signal.return_value = order
        self.mock_execution_algorithms[1].execute_order.return_value = "EXEC_ID_456"
        
        result = self.service.execute_signal_with_algorithm(signal, "ALGORITHM_2")
        
        self.assertIsNotNone(result)
        # Second execution algorithm should be called if algorithm selection logic is implemented


if __name__ == '__main__':
    unittest.main()