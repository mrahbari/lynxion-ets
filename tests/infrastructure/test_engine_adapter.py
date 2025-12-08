"""
Unit tests for Engine Adapter.
"""
import unittest
from unittest.mock import Mock, MagicMock
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from decimal import Decimal
from datetime import datetime

from infrastructure.adapters.engine_adapter import EngineManagementToEnginePortAdapter


class TestEngineManagementToEnginePortAdapter(unittest.TestCase):
    """Test cases for EngineManagementToEnginePortAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        # Create a mock engine management service
        self.mock_engine_service = Mock()
        self.adapter = EngineManagementToEnginePortAdapter(self.mock_engine_service)

    def test_init_with_engine_service(self):
        """Test that adapter is initialized with engine management service."""
        self.assertEqual(self.adapter.engine_management_service, self.mock_engine_service)

    def test_process_signal_delegates_to_engine_service(self):
        """Test that process_signal delegates to engine management service."""
        # Create a mock signal
        original_signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal('0.75')),
            score=0.6,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        # Mock the return value of the engine service
        processed_signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.BUY,
            confidence=Percentage(Decimal('0.80')),  # Processed signal might have different confidence
            score=0.7,  # Processed signal might have different score
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        self.mock_engine_service.process_signal_through_all_engines.return_value = processed_signal

        # Call process_signal method
        result = self.adapter.process_signal(original_signal)

        # Verify that the engine service method was called with correct signal
        self.mock_engine_service.process_signal_through_all_engines.assert_called_once_with(original_signal)
        self.assertEqual(result, processed_signal)

    def test_should_process_signal_always_returns_true(self):
        """Test that should_process_signal always returns True."""
        test_signal = Signal(
            symbol=Symbol("BTCUSDT"),
            signal_type=SignalType.SELL,
            confidence=Percentage(Decimal('0.65')),
            score=-0.4,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )

        result = self.adapter.should_process_signal(test_signal)

        self.assertTrue(result)

    def test_get_engine_name_returns_correct_name(self):
        """Test that get_engine_name returns the correct name."""
        result = self.adapter.get_engine_name()
        
        self.assertEqual(result, "EngineManagementAdapter")

    def test_implements_engine_port_interface(self):
        """Test that adapter properly implements EnginePort interface."""
        # Check that the adapter has the required methods
        self.assertTrue(hasattr(self.adapter, 'process_signal'))
        self.assertTrue(hasattr(self.adapter, 'should_process_signal'))
        self.assertTrue(hasattr(self.adapter, 'get_engine_name'))

        # Check method signatures match expected interface
        import inspect
        process_signal_sig = inspect.signature(self.adapter.process_signal)
        self.assertIn('signal', process_signal_sig.parameters)
        
        should_process_sig = inspect.signature(self.adapter.should_process_signal)
        self.assertIn('signal', should_process_sig.parameters)


if __name__ == '__main__':
    unittest.main()