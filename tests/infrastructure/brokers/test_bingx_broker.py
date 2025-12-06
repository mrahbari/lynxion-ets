import unittest
from unittest.mock import Mock, patch
from decimal import Decimal

from domain.entities.trading_entities import Order, OrderSide, Position, PositionSide
from domain.value_objects import Symbol, Money
from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter


class TestBingXBrokerAdapter(unittest.TestCase):

    def setUp(self):
        self.mock_config = {
            'api_key': 'test_api_key',
            'secret_key': 'test_secret_key',
            'testnet': True
        }
        self.adapter = BingXBrokerAdapter(self.mock_config)
        self.adapter._broker = Mock()

    def test_connect_success(self):
        self.adapter._broker.get_account_balance.return_value = [{'asset': 'USDT', 'balance': '10000'}]
        self.assertTrue(self.adapter.connect())
        self.assertTrue(self.adapter.connected)

    def test_connect_failure(self):
        self.adapter._broker.get_account_balance.side_effect = Exception("Connection failed")
        self.assertFalse(self.adapter.connect())
        self.assertFalse(self.adapter.connected)

    def test_place_order_success(self):
        order = Order(
            symbol=Symbol("BTC-USDT"),
            side=OrderSide.BUY,
            quantity=Decimal("0.001"),
            order_type="MARKET",
            position_side="LONG"
        )
        self.adapter._broker.execute_order.return_value = {'success': True, 'order_id': '12345'}
        order_id = self.adapter.place_order(order)
        self.assertEqual(order_id, '12345')

    def test_place_order_failure(self):
        order = Order(
            symbol=Symbol("BTC-USDT"),
            side=OrderSide.BUY,
            quantity=Decimal("0.001"),
            order_type="MARKET",
            position_side="LONG"
        )
        self.adapter._broker.execute_order.return_value = {'success': False, 'error': 'Invalid order'}
        with self.assertRaisesRegex(Exception, "Failed to place order: Invalid order"):
            self.adapter.place_order(order)

    def test_cancel_order_success(self):
        self.adapter._broker.cancel_order.return_value = True
        self.assertTrue(self.adapter.cancel_order('12345', Symbol('BTC-USDT')))

    def test_get_order_status_filled(self):
        self.adapter._broker.get_order_status.return_value = 'FILLED'
        status = self.adapter.get_order_status('12345', Symbol('BTC-USDT'))
        self.assertEqual(status, 'FILLED')

    def test_get_balance(self):
        self.adapter._broker.get_account_balance.return_value = [
            {'asset': 'USDT', 'balance': '10000.0', 'availableMargin': '9000.0'},
            {'asset': 'BTC', 'balance': '0.1', 'availableMargin': '0.1'}
        ]
        balances = self.adapter.get_balance()
        self.assertEqual(len(balances), 2)
        self.assertEqual(balances[0].asset, 'USDT')
        self.assertEqual(balances[0].total.amount, Decimal('10000.0'))

    def test_get_all_positions(self):
        self.adapter._broker.get_open_positions.return_value = [
            {'symbol': 'BTC-USDT', 'positionAmt': '0.1', 'avgPrice': '50000.0', 'unrealisedPnl': '100.0', 'time': 1672531200000}
        ]
        positions = self.adapter.get_all_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].symbol.value, 'BTCUSDT')
        self.assertEqual(positions[0].quantity, 0.1)
        self.assertEqual(positions[0].side, PositionSide.LONG)


if __name__ == '__main__':
    unittest.main()
