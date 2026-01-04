from typing import Dict, Optional, List, Any
from datetime import datetime
import logging

from domain.entities.trading_entities import Order, Position, Balance, OrderSide
from domain.ports.broker_ports import BrokerPort
from domain.value_objects import Symbol, Money
from infrastructure.data.adapters.rest_client import RestClient
from infrastructure.brokers.symbol_format_helper import SymbolFormatHelper


class BinanceBrokerAdapter(BrokerPort):
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.client = RestClient(api_key, secret_key)
        self.connected = False

    def connect(self) -> bool:
        """Connect to Binance API"""
        try:
            # Test connection by getting server time
            server_time = self.client.get_server_time()
            if server_time:
                self.connected = True
                logging.info("Connected to Binance")
                return True
            else:
                logging.error("Failed to connect to Binance")
                return False
        except Exception as e:
            logging.error(f"Error connecting to Binance: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from Binance"""
        self.connected = False
        logging.info("Disconnected from Binance")
        return True

    def get_balance(self, asset: str = None) -> Optional[Balance]:
        """Get account balance"""
        if not self.connected:
            logging.error("Not connected to Binance")
            return None

        balances = self.client.get_balance(asset)
        if balances and asset:
            return Balance(
                asset=asset.upper(),
                total=balances['total'],
                available=balances['free'],
                reserved=balances['locked'],
                timestamp=datetime.now()
            )
        return None

    def get_all_balances(self) -> List[Balance]:
        """Get all account balances"""
        if not self.connected:
            logging.error("Not connected to Binance")
            return []

        balances = self.client.get_balance()
        result = []

        if balances:
            for asset, balance_info in balances.items():
                result.append(Balance(
                    asset=asset,
                    total=balance_info['total'],
                    available=balance_info['free'],
                    reserved=balance_info['locked'],
                    timestamp=datetime.now()
                ))

        return result

    def place_order(self, order: Order) -> Optional[str]:
        """Place an order and return order ID"""
        if not self.connected:
            logging.error("Not connected to Binance")
            return None

        try:
            # Convert our Order type to Binance format
            binance_side = "BUY" if order.side == OrderSide.BUY else "SELL"

            response = self.client.place_order(
                symbol=order.symbol.value,
                side=binance_side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                time_in_force=order.time_in_force,
                stop_price=order.stop_price
            )

            if response and 'orderId' in response:
                order_id = str(response['orderId'])
                logging.info(f"Order placed successfully: {order_id}")
                return order_id
            else:
                logging.error(f"Failed to place order: {response}")
                return None

        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return None

    def get_open_orders(self, symbol: str = None) -> List[Order]:
        """Get open orders"""
        if not self.connected:
            logging.error("Not connected to Binance")
            return []

        try:
            response = self.client.get_open_orders(symbol)
            orders = []

            if response:
                for item in response:
                    side = OrderSide.BUY if item['side'] == 'BUY' else OrderSide.SELL

                    orders.append(Order(
                        symbol=Symbol(item['symbol']),
                        side=side,
                        quantity=float(item['origQty']),
                        order_type=item['type'].upper(),
                        price=float(item['price']) if item['price'] != '' else None,
                        stop_price=float(item['stopPrice']) if item['stopPrice'] != '' else None,
                        time_in_force=item['timeInForce'],
                        client_order_id=item.get('clientOrderId')
                    ))

            return orders
        except Exception as e:
            logging.error(f"Error getting open orders: {e}")
            return []

    def cancel_order(self, order_id: str, symbol: Symbol = None) -> bool:
        """Cancel an order"""
        if not self.connected or not symbol:
            logging.error("Not connected to Binance or symbol not provided")
            return False

        try:
            response = self.client.cancel_order(symbol.value, int(order_id))
            if response:
                logging.info(f"Order {order_id} cancelled successfully")
                return True
            else:
                logging.error(f"Failed to cancel order {order_id}")
                return False
        except Exception as e:
            logging.error(f"Error cancelling order {order_id}: {e}")
            return False

    def get_order_status(self, order_id: str, symbol: Symbol = None) -> Optional[Dict[str, Any]]:
        """Get order status - Binance doesn't have a direct API for this,
        so we get all open orders and check if the order is there"""
        if not self.connected or not symbol:
            logging.error("Not connected to Binance or symbol not provided")
            return None

        open_orders = self.get_open_orders(symbol.value)

        for order in open_orders:
            if (order.client_order_id and order.client_order_id == order_id):
                return {
                    'status': 'OPEN',
                    'order': order
                }

        # If not in open orders, it might be filled or cancelled
        # For now, we'll return FILLED status as a fallback
        return {
            'status': 'FILLED',  # Simplified for this example
            'order': None
        }

    def get_positions(self) -> List[Position]:
        """Get all positions - Binance futures positions"""
        # Binance spot doesn't have positions, only futures does
        # This is a simplified implementation for spot trading
        logging.warning("Binance spot trading doesn't have positions. Only futures positions are available.")
        return []

    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get specific position"""
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None

    def get_available_symbols(self) -> set:
        """Get set of available symbols on Binance."""
        try:
            import requests
            # Use direct API call to get exchange info from Binance
            response = requests.get('https://api.binance.com/api/v3/exchangeInfo', timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'symbols' in data:
                    symbols = set()
                    for symbol_info in data['symbols']:
                        if symbol_info.get('status') == 'TRADING':  # Only include active trading pairs
                            # Ensure symbol is in the correct format (e.g., BTCUSDT)
                            symbol = symbol_info['symbol']
                            # Binance symbols are already in format like BTCUSDT, but normalize just in case
                            symbols.add(symbol.upper())
                    return symbols
        except Exception as e:
            # If API call fails, return empty set
            pass

        # Return empty set if all attempts fail
        return set()

    def get_all_positions(self) -> List[Position]:
        return self.get_positions()
