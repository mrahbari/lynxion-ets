from typing import Dict, Optional, List, Any
import hmac
import hashlib
import time
import requests
from datetime import datetime
import logging

from domain.entities.trading_entities import Order, Position, Balance, OrderSide
from domain.ports.broker_ports import BrokerPort
from domain.value_objects import Symbol, Money


class MEXCBrokerAdapter(BrokerPort):
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://api.mexc.com"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'ApiKey': api_key
        })
        self.connected = False

    def _sign_request(self, method: str, path: str, params: Dict = None, body: str = "") -> str:
        """Sign request for MEXC API"""
        timestamp = str(int(time.time() * 1000))

        # Prepare query string for GET requests
        if method == "GET" and params:
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            payload = f"{path}?{query_string}{timestamp}"
        elif body:  # POST requests with body
            payload = f"{path}{body}{timestamp}"
        else:  # Other requests
            payload = f"{path}{timestamp}"

        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature, timestamp

    def _make_request(self, method: str, path: str, params: Dict = None, body: str = "") -> Optional[Dict]:
        """Make API request to MEXC"""
        if not self.connected:
            logging.error("Not connected to MEXC")
            return None

        signature, timestamp = self._sign_request(method, path, params, body)

        # Update headers with signature and timestamp
        headers = {
            'ApiKey': self.api_key,
            'Request-Time': timestamp,
            'Signature': signature,
            'Content-Type': 'application/json'
        }

        url = f"{self.base_url}{path}"

        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers)
            elif method == "POST":
                response = requests.post(url, data=body, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, params=params, headers=headers)
            else:
                logging.error(f"Unsupported HTTP method: {method}")
                return None

            if response.status_code in [200, 201]:
                return response.json()
            else:
                logging.error(f"API request failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logging.error(f"Error making request to MEXC: {e}")
            return None

    def connect(self) -> bool:
        """Connect to MEXC API"""
        try:
            # Test connection by getting server time
            path = "/api/v3/time"
            response = self._make_request("GET", path)

            if response and 'serverTime' in response:
                self.connected = True
                logging.info("Connected to MEXC")
                return True
            else:
                logging.error(f"Failed to connect to MEXC: {response}")
                return False
        except Exception as e:
            logging.error(f"Error connecting to MEXC: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from MEXC"""
        self.connected = False
        logging.info("Disconnected from MEXC")
        return True

    def get_balance(self, asset: str = None) -> Optional[Balance]:
        """Get account balance"""
        if not self.connected:
            logging.error("Not connected to MEXC")
            return None

        path = "/api/v3/account"
        response = self._make_request("GET", path)

        if response:
            balances = response.get('balances', [])

            if asset:
                for balance in balances:
                    if balance.get('asset') == asset.upper():
                        return Balance(
                            asset=balance.get('asset'),
                            total=float(balance.get('free', 0)) + float(balance.get('locked', 0)),
                            available=float(balance.get('free', 0)),
                            reserved=float(balance.get('locked', 0)),
                            timestamp=datetime.now()
                        )
            else:
                # Return first balance if no asset specified
                if balances:
                    balance = balances[0]
                    return Balance(
                        asset=balance.get('asset'),
                        total=float(balance.get('free', 0)) + float(balance.get('locked', 0)),
                        available=float(balance.get('free', 0)),
                        reserved=float(balance.get('locked', 0)),
                        timestamp=datetime.now()
                    )
        return None

    def get_all_balances(self) -> List[Balance]:
        """Get all account balances"""
        if not self.connected:
            logging.error("Not connected to MEXC")
            return []

        path = "/api/v3/account"
        response = self._make_request("GET", path)

        balances = []
        if response:
            account_balances = response.get('balances', [])

            for balance_info in account_balances:
                balance = Balance(
                    asset=balance_info.get('asset'),
                    total=float(balance_info.get('free', 0)) + float(balance_info.get('locked', 0)),
                    available=float(balance_info.get('free', 0)),
                    reserved=float(balance_info.get('locked', 0)),
                    timestamp=datetime.now()
                )
                balances.append(balance)

        return balances

    def place_order(self, order: Order) -> Optional[str]:
        """Place an order and return order ID"""
        if not self.connected:
            logging.error("Not connected to MEXC")
            return None

        path = "/api/v3/order"

        # Convert our order type to MEXC format
        side = "BUY" if order.side == OrderSide.BUY else "SELL"

        params = {
            "symbol": order.symbol.value,
            "side": side,
            "type": order.order_type,
            "quantity": str(order.quantity),
        }

        if order.price:
            params["price"] = str(order.price.amount)

        if order.time_in_force:
            params["timeInForce"] = order.time_in_force

        if order.stop_price:
            params["stopPrice"] = str(order.stop_price.amount)

        # Convert params to query string for POST body
        body = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])

        response = self._make_request("POST", path, body=body)

        if response and 'orderId' in response:
            order_id = response['orderId']
            logging.info(f"Order placed successfully: {order_id}")
            return str(order_id)
        else:
            logging.error(f"Failed to place order: {response}")
            return None

    def get_open_orders(self, symbol: str = None) -> List[Order]:
        """Get open orders"""
        if not self.connected:
            logging.error("Not connected to MEXC")
            return []

        path = "/api/v3/openOrders"
        params = {"symbol": symbol} if symbol else {}

        response = self._make_request("GET", path, params)
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
                    time_in_force=item.get('timeInForce', 'GTC'),
                    client_order_id=item.get('clientOrderId')
                ))

        return orders

    def cancel_order(self, order_id: str, symbol: Symbol = None) -> bool:
        """Cancel an order"""
        if not self.connected or not symbol:
            logging.error("Not connected to MEXC or symbol not provided")
            return False

        path = "/api/v3/order"
        params = {
            "symbol": symbol.value,
            "orderId": order_id
        }

        response = self._make_request("DELETE", path, params)

        if response:
            logging.info(f"Order {order_id} cancelled successfully")
            return True
        else:
            logging.error(f"Failed to cancel order {order_id}: {response}")
            return False

    def get_order_status(self, order_id: str, symbol: Symbol = None) -> Optional[Dict[str, Any]]:
        """Get order status"""
        if not self.connected or not symbol:
            logging.error("Not connected to MEXC or symbol not provided")
            return None

        path = "/api/v3/order"
        params = {
            "symbol": symbol.value,
            "orderId": order_id
        }

        response = self._make_request("GET", path, params)

        if response:
            return {
                'status': response.get('status', 'UNKNOWN'),
                'order': response
            }
        else:
            logging.error(f"Failed to get order status for {order_id}: {response}")
            return None

    def get_positions(self) -> List[Position]:
        """Get all positions"""
        # MEXC spot doesn't have positions, only futures does
        # This is a simplified implementation for spot trading
        logging.warning("MEXC spot trading doesn't have positions. Only futures positions are available.")
        return []

    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get specific position"""
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None

    def get_all_positions(self) -> List[Position]:
        return self.get_positions()
