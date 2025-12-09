"""
Unit tests for BingX broker implementation.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime

from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter
from domain.entities.trading_entities import Order, Position
from domain.value_objects import Symbol, Money, Percentage
from domain.entities.trading_entities import OrderSide, PositionSide


class TestBingXBrokerAdapter(unittest.TestCase):
    """Test cases for BingXBrokerAdapter"""

    def setUp(self):
        """Setup test fixtures before each test method."""
        self.api_key = "test_api_key"
        self.secret_key = "test_secret_key"
        self.base_url = "https://open-api.bingx.com"
        self.broker = BingXBrokerAdapter(self.api_key, self.secret_key, self.base_url)
        # Don't connect by default - let individual tests handle connection status

    @patch('requests.Session.get')
    def test_connect_success(self, mock_get):
        """Test successful connection to BingX API."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': []
        }
        mock_get.return_value = mock_response

        result = self.broker.connect()
        
        self.assertTrue(result)
        self.assertTrue(self.broker.connected)
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_connect_failure(self, mock_get):
        """Test connection failure to BingX API."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = self.broker.connect()
        
        self.assertFalse(result)
        self.assertFalse(self.broker.connected)

    def test_disconnect(self):
        """Test disconnection from BingX API."""
        self.broker.connected = True
        self.broker.disconnect()
        
        self.assertFalse(self.broker.connected)

    @patch('requests.Session.post')
    def test_place_order_success(self, mock_post):
        """Test successful order placement."""
        # Connect the broker first
        self.broker.connected = True

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': {
                'order': {'orderId': 'BINGX_TEST_ORDER_123'}
            }
        }
        mock_post.return_value = mock_response

        # Create test order
        order = Order(
            symbol=Symbol("BTCUSDT"),
            side=OrderSide.BUY,
            order_type="MARKET",
            quantity=Decimal('0.1'),
            timestamp=datetime.now()
        )

        result = self.broker.place_order(order)

        self.assertEqual(result, 'BINGX_TEST_ORDER_123')
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_place_order_limit_success(self, mock_post):
        """Test successful limit order placement."""
        # Connect the broker first
        self.broker.connected = True

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': {
                'order': {'orderId': 'BINGX_TEST_ORDER_456'},
                'status': 'NEW'
            }
        }
        mock_post.return_value = mock_response

        # Create test order with price (limit order)
        order = Order(
            symbol=Symbol("BTCUSDT"),
            side=OrderSide.BUY,
            order_type="LIMIT",
            quantity=Decimal('0.1'),
            price=Money(Decimal('40000'), 'USDT'),
            timestamp=datetime.now()
        )

        result = self.broker.place_order(order)

        self.assertEqual(result, 'BINGX_TEST_ORDER_456')
        mock_post.assert_called_once()

    @patch('requests.Session.delete')
    def test_cancel_order_success(self, mock_delete):
        """Test successful order cancellation."""
        # Connect the broker first
        self.broker.connected = True

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': {'status': 'CANCELED'}
        }
        mock_delete.return_value = mock_response

        symbol = Symbol("BTCUSDT")
        result = self.broker.cancel_order('BINGX_TEST_ORDER_123', symbol)

        self.assertTrue(result)
        mock_delete.assert_called_once()

    @patch('requests.Session.get')
    def test_get_order_status(self, mock_get):
        """Test getting order status."""
        # Connect the broker first
        self.broker.connected = True

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': {
                'order': {'status': 'FILLED'}
            }
        }
        mock_get.return_value = mock_response

        symbol = Symbol("BTCUSDT")
        result = self.broker.get_order_status('BINGX_TEST_ORDER_123', symbol)

        self.assertEqual(result, 'FILLED')
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_get_position(self, mock_get):
        """Test getting position."""
        # Connect the broker first
        self.broker.connected = True

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': [
                {
                    'symbol': 'BTCUSDT',
                    'positionAmt': '0.5',
                    'entryPrice': '40000',
                    'unrealizedProfit': '1000'
                }
            ]
        }
        mock_get.return_value = mock_response

        symbol = Symbol("BTCUSDT")
        position = self.broker.get_position(symbol)

        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, Decimal('0.5'))
        self.assertEqual(position.entry_price.amount, Decimal('40000'))
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_get_balance(self, mock_get):
        """Test getting account balance."""
        # Connect the broker first
        self.broker.connected = True

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': [
                {
                    'asset': 'USDT',
                    'balance': '10000',
                    'availableBalance': '9000',
                    'positionMargin': '1000'
                }
            ]
        }
        mock_get.return_value = mock_response

        balances = self.broker.get_balance()

        self.assertEqual(len(balances), 1)
        self.assertEqual(balances[0].asset, 'USDT')
        self.assertEqual(balances[0].total, Decimal('10000'))
        self.assertEqual(balances[0].available, Decimal('9000'))
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_get_balance_for_specific_asset(self, mock_get):
        """Test getting balance for specific asset."""
        # Connect the broker first
        self.broker.connected = True

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': [
                {
                    'asset': 'BTC',
                    'balance': '1.5',
                    'availableBalance': '1.0',
                    'positionMargin': '0.5'
                },
                {
                    'asset': 'USDT',
                    'balance': '10000',
                    'availableBalance': '9000',
                    'positionMargin': '1000'
                }
            ]
        }
        mock_get.return_value = mock_response

        balances = self.broker.get_balance('BTC')

        self.assertEqual(len(balances), 1)
        self.assertEqual(balances[0].asset, 'BTC')
        self.assertEqual(balances[0].total, Decimal('1.5'))
        mock_get.assert_called_once()

    def test_sign_request_get_method(self):
        """Test signing GET request."""
        # Test the signing method with GET request
        params = {
            'timestamp': '1234567890',
            'symbol': 'BTCUSDT'
        }
        
        signature = self.broker._sign_request("GET", "/test/endpoint", params)
        
        # Should return a valid signature string
        self.assertIsInstance(signature, str)
        self.assertEqual(len(signature), 64)  # SHA256 hash length

    def test_sign_request_post_method(self):
        """Test signing POST request."""
        # Test the signing method with POST request
        params = {
            'timestamp': '1234567890',
            'symbol': 'BTCUSDT',
            'quantity': '0.1'
        }
        
        signature = self.broker._sign_request("POST", "/test/endpoint", params)
        
        # Should return a valid signature string
        self.assertIsInstance(signature, str)
        self.assertEqual(len(signature), 64)  # SHA256 hash length

    @patch('requests.Session.post')
    def test_place_order_failure(self, mock_post):
        """Test order placement failure."""
        # Connect the broker first
        self.broker.connected = True

        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'code': -1,
            'msg': 'Invalid order parameters'
        }
        mock_post.return_value = mock_response

        order = Order(
            symbol=Symbol("BTCUSDT"),
            side=OrderSide.BUY,
            order_type="MARKET",
            quantity=Decimal('0.1'),
            timestamp=datetime.now()
        )

        result = self.broker.place_order(order)

        self.assertIsNone(result)

    @patch('requests.Session.get')
    def test_get_position_not_found(self, mock_get):
        """Test getting position when not found."""
        # Connect the broker first
        self.broker.connected = True

        # Mock response with no matching position
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': []
        }
        mock_get.return_value = mock_response

        symbol = Symbol("BTCUSDT")
        position = self.broker.get_position(symbol)

        # Should return flat position when not found
        self.assertIsNotNone(position)
        self.assertEqual(position.side, PositionSide.FLAT)
        self.assertEqual(position.quantity, Decimal('0'))
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_get_order_status_error(self, mock_get):
        """Test getting order status when API returns error."""
        # Connect the broker first
        self.broker.connected = True

        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 200  # Still 200 but with error code
        mock_response.json.return_value = {
            'code': -1,
            'msg': 'Order not found'
        }
        mock_get.return_value = mock_response

        symbol = Symbol("BTCUSDT")
        result = self.broker.get_order_status('INVALID_ORDER_ID', symbol)

        self.assertEqual(result, 'ERROR')
        mock_get.assert_called_once()

    def test_broker_not_connected_operations(self):
        """Test operations when broker is not connected."""
        # Ensure broker is disconnected
        self.broker.connected = False
        
        result = self.broker.place_order(
            Order(
                symbol=Symbol("BTCUSDT"),
                side=OrderSide.BUY,
                order_type="MARKET",
                quantity=Decimal('0.1'),
                timestamp=datetime.now()
            )
        )
        self.assertIsNone(result)

        result = self.broker.cancel_order('TEST_ORDER', Symbol("BTCUSDT"))
        self.assertFalse(result)

        result = self.broker.get_order_status('TEST_ORDER', Symbol("BTCUSDT"))
        self.assertEqual(result, 'DISCONNECTED')

        result = self.broker.get_position(Symbol("BTCUSDT"))
        self.assertIsNone(result)

        result = self.broker.get_balance()
        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main()