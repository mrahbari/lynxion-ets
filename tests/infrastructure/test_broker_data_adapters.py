"""
Unit tests for Broker Data Adapters.
"""
import unittest
from unittest.mock import Mock, MagicMock
from domain.entities.trading_entities import Order, Position, OrderSide, PositionSide
from domain.value_objects import Symbol, Money
from decimal import Decimal
from datetime import datetime

from infrastructure.adapters.broker_data_adapters import MockBrokerAdapter, MockDataAdapter


class TestMockBrokerAdapter(unittest.TestCase):
    """Test cases for MockBrokerAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.broker = MockBrokerAdapter()

    def test_init_creates_empty_orders_and_positions(self):
        """Test that MockBrokerAdapter is initialized with empty orders and positions."""
        self.assertEqual(self.broker.orders, {})
        self.assertEqual(self.broker.positions, {})
        self.assertEqual(self.broker.order_id_counter, 1000)

    def test_place_order_creates_new_order(self):
        """Test that place_order creates a new order with a unique ID."""
        order = Order(
            symbol=Symbol("BTCUSDT"),
            side=OrderSide.BUY,
            order_type="MARKET",
            quantity=Decimal('0.1'),
            timestamp=datetime.now()
        )

        order_id = self.broker.place_order(order)

        self.assertTrue(order_id.startswith("MOCK_ORDER_"))
        self.assertIn(order_id, self.broker.orders)
        self.assertEqual(self.broker.orders[order_id]['status'], 'NEW')

    def test_cancel_order_updates_status(self):
        """Test that cancel_order updates the order status to CANCELED."""
        # First place an order to cancel
        order = Order(
            symbol=Symbol("BTCUSDT"),
            side=OrderSide.BUY,
            order_type="MARKET",
            quantity=Decimal('0.1'),
            timestamp=datetime.now()
        )
        order_id = self.broker.place_order(order)

        # Cancel the order
        result = self.broker.cancel_order(order_id, Symbol("BTCUSDT"))

        self.assertTrue(result)
        self.assertEqual(self.broker.orders[order_id]['status'], 'CANCELED')

    def test_cancel_order_returns_false_for_invalid_order(self):
        """Test that cancel_order returns False for invalid order ID."""
        result = self.broker.cancel_order("NONEXISTENT_ORDER", Symbol("BTCUSDT"))

        self.assertFalse(result)

    def test_get_order_status_returns_correct_status(self):
        """Test that get_order_status returns the correct status."""
        # Place and cancel an order
        order = Order(
            symbol=Symbol("BTCUSDT"),
            side=OrderSide.BUY,
            order_type="MARKET",
            quantity=Decimal('0.1'),
            timestamp=datetime.now()
        )
        order_id = self.broker.place_order(order)
        self.broker.cancel_order(order_id, Symbol("BTCUSDT"))

        status = self.broker.get_order_status(order_id, Symbol("BTCUSDT"))

        self.assertEqual(status, 'CANCELED')

    def test_get_order_status_returns_not_found_for_invalid_order(self):
        """Test that get_order_status returns NOT_FOUND for invalid order ID."""
        status = self.broker.get_order_status("NONEXISTENT_ORDER", Symbol("BTCUSDT"))

        self.assertEqual(status, 'NOT_FOUND')

    def test_get_position_returns_mock_position(self):
        """Test that get_position returns a mock position."""
        symbol = Symbol("BTCUSDT")
        position = self.broker.get_position(symbol)

        self.assertIsNotNone(position)
        self.assertEqual(position.symbol, symbol)
        self.assertEqual(position.side, PositionSide.FLAT)
        self.assertEqual(position.quantity, Decimal('0'))

    def test_get_all_positions_returns_mock_positions(self):
        """Test that get_all_positions returns mock positions."""
        positions = self.broker.get_all_positions()

        self.assertEqual(len(positions), 2)  # Mock positions for BTC and ETH
        # Check first position
        btc_position = positions[0]
        self.assertEqual(btc_position.symbol.value, "BTCUSDT")
        self.assertEqual(btc_position.side, PositionSide.LONG)
        self.assertEqual(btc_position.quantity, Decimal('0.5'))

        # Check second position
        eth_position = positions[1]
        self.assertEqual(eth_position.symbol.value, "ETHUSDT")
        self.assertEqual(eth_position.side, PositionSide.SHORT)
        self.assertEqual(eth_position.quantity, Decimal('2.0'))


class TestMockDataAdapter(unittest.TestCase):
    """Test cases for MockDataAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.data_adapter = MockDataAdapter()

    def test_init_creates_mock_price_data(self):
        """Test that MockDataAdapter is initialized with mock price data."""
        self.assertIn("BTCUSDT", self.data_adapter.mock_prices)
        self.assertIn("ETHUSDT", self.data_adapter.mock_prices)
        self.assertIn("BTCUSDT", self.data_adapter.mock_historical)
        self.assertIn("ETHUSDT", self.data_adapter.mock_historical)

    def test_get_current_price_returns_mock_price(self):
        """Test that get_current_price returns mock price for symbol."""
        price = self.data_adapter.get_current_price(Symbol("BTCUSDT"))

        self.assertEqual(price, 45123.45)

    def test_get_current_price_returns_zero_for_unknown_symbol(self):
        """Test that get_current_price returns 0.0 for unknown symbol."""
        price = self.data_adapter.get_current_price(Symbol("UNKNOWNUSDT"))

        self.assertEqual(price, 0.0)

    def test_get_historical_data_returns_mock_data(self):
        """Test that get_historical_data returns mock historical data."""
        hist_data = self.data_adapter.get_historical_data(Symbol("BTCUSDT"), "1d")

        self.assertEqual(len(hist_data), 100)  # Mock data has 100 points
        self.assertEqual(hist_data[0], 45000)  # First value in mock data
        self.assertEqual(hist_data[1], 45010)  # Second value in mock data

    def test_subscribe_to_market_data_starts_thread(self):
        """Test that subscribe_to_market_data starts a data feed thread."""
        # Mock the callback function
        callback = Mock()
        
        # This test is tricky because the method starts a thread
        # For now, just check that it doesn't raise an exception
        try:
            self.data_adapter.subscribe_to_market_data(Symbol("BTCUSDT"), callback)
            # The thread is daemon, so it should run in background
            success = True
        except Exception as e:
            success = False
            
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()