"""
Unit tests for Signal Adapter.
"""
import unittest
from unittest.mock import Mock, MagicMock
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from decimal import Decimal
from datetime import datetime

from infrastructure.adapters.signal_adapter import StrategyToSignalPortAdapter


class TestStrategyToSignalPortAdapter(unittest.TestCase):
    """Test cases for StrategyToSignalPortAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        # Create a mock strategy selection service
        self.mock_strategy_service = Mock()
        self.adapter = StrategyToSignalPortAdapter(self.mock_strategy_service)

    def test_init_with_strategy_service(self):
        """Test that adapter is initialized with strategy selection service."""
        self.assertEqual(self.adapter.strategy_selection_service, self.mock_strategy_service)

    def test_generate_signal_calls_strategy_service(self):
        """Test that generate_signal delegates to strategy selection service."""
        # Create a test symbol
        symbol = Symbol("BTCUSDT")
        
        # Mock return value for the strategy service
        mock_signal = Signal(
            symbol=symbol,
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal('0.75')),
            score=0.6,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        self.mock_strategy_service.generate_signal_with_optimal_strategy.return_value = mock_signal

        # Call generate_signal method
        result = self.adapter.generate_signal(symbol)

        # Verify that the strategy service method was called with correct symbol
        self.mock_strategy_service.generate_signal_with_optimal_strategy.assert_called_once_with(symbol)
        self.assertEqual(result, mock_signal)

    def test_generate_signal_returns_none_when_strategy_service_returns_none(self):
        """Test that generate_signal returns None when strategy service returns None."""
        symbol = Symbol("BTCUSDT")
        self.mock_strategy_service.generate_signal_with_optimal_strategy.return_value = None

        result = self.adapter.generate_signal(symbol)

        self.assertIsNone(result)
        self.mock_strategy_service.generate_signal_with_optimal_strategy.assert_called_once_with(symbol)

    def test_process_signal_returns_same_signal(self):
        """Test that process_signal returns the same signal (no processing by strategy service)."""
        # Create a mock signal
        original_signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.SELL,
            confidence=Percentage(Decimal('0.65')),
            score=-0.4,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )

        result = self.adapter.process_signal(original_signal)

        # The signal should be returned as is, unchanged
        self.assertEqual(result, original_signal)

    def test_implements_signal_port_interface(self):
        """Test that adapter properly implements SignalPort interface."""
        # Check that the adapter has the required methods
        self.assertTrue(hasattr(self.adapter, 'generate_signal'))
        self.assertTrue(hasattr(self.adapter, 'process_signal'))

        # Check method signatures match expected interface
        import inspect
        generate_signal_sig = inspect.signature(self.adapter.generate_signal)
        self.assertIn('symbol', generate_signal_sig.parameters)
        
        process_signal_sig = inspect.signature(self.adapter.process_signal)
        self.assertIn('signal', process_signal_sig.parameters)


if __name__ == '__main__':
    unittest.main()