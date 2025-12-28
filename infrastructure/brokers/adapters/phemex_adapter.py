from typing import Dict, Optional, List, Any
import hmac
import hashlib
import time
import requests
import json
from datetime import datetime
import logging

from domain.entities.trading_entities import Order, Position, Balance, OrderSide
from domain.ports.broker_ports import BrokerPort
from domain.value_objects import Symbol, Money


class PhemexBrokerAdapter(BrokerPort):
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://api.phemex.com"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'x-phemex-access-token': api_key,
            'Content-Type': 'application/json'
        })
        self.connected = False

    def _sign_request(self, method: str, path: str, params: str = "", query_string: str = "") -> str:
        """Sign request for Phemex API"""
        timestamp = str(int(time.time() * 1000))

        # Prepare the signature string
        if method == "GET":
            if query_string:
                signature_string = f"{path}?{query_string}{timestamp}"
            else:
                signature_string = f"{path}{timestamp}"
        else:  # POST, PUT, DELETE
            signature_string = f"{path}{params}{timestamp}"

        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature, timestamp

    def _make_request(self, method: str, path: str, params: Optional[Dict] = None, query_params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request to Phemex"""
        if not self.connected:
            logging.error("Not connected to Phemex")
            return None

        # Prepare query string if needed
        query_string = ""
        if query_params:
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(query_params.items())])

        # Prepare body string if needed
        body_string = ""
        if params:
            body_string = json.dumps(params, separators=(',', ':'))

        signature, timestamp = self._sign_request(method, path, body_string, query_string)

        # Prepare URL with query parameters
        url = f"{self.base_url}{path}"
        if query_string:
            url += f"?{query_string}"

        # Update headers with signature and timestamp
        headers = {
            'x-phemex-access-token': self.api_key,
            'x-phemex-request-expiry': str(timestamp),
            'x-phemex-request-signature': signature,
            'Content-Type': 'application/json'
        }

        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, data=body_string, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                logging.error(f"Unsupported HTTP method: {method}")
                return None

            if response.status_code in [200, 201]:
                return response.json()
            else:
                logging.error(f"API request failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logging.error(f"Error making request to Phemex: {e}")
            return None

    def connect(self) -> bool:
        """Connect to Phemex API"""
        try:
            # Test connection by getting account positions
            path = "/accounts/accountPositions"
            query_params = {"currency": "USD"}

            response = self._make_request("GET", path, query_params=query_params)

            if response and response.get('code') == 0:
                self.connected = True
                logging.info("Connected to Phemex")
                return True
            else:
                logging.error(f"Failed to connect to Phemex: {response}")
                return False
        except Exception as e:
            logging.error(f"Error connecting to Phemex: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from Phemex"""
        self.connected = False
        logging.info("Disconnected from Phemex")
        return True

    def get_balance(self, asset: str = None) -> Optional[Balance]:
        """Get account balance"""
        if not self.connected:
            logging.error("Not connected to Phemex")
            return None

        path = "/accounts/accountPositions"
        query_params = {"currency": asset.upper() if asset else "USD"}

        response = self._make_request("GET", path, query_params=query_params)

        if response and response.get('code') == 0:
            data = response.get('data', {})
            accounts = data.get('accounts', [])

            for account in accounts:
                currency = account.get('currency')
                if not asset or currency == asset.upper():
                    return Balance(
                        asset=currency,
                        total=float(account.get('balanceEv', 0)) / 100000000.0,  # Phemex uses 8 decimal places internally
                        available=float(account.get('availableBalanceEv', 0)) / 100000000.0,
                        reserved=(float(account.get('balanceEv', 0)) - float(account.get('availableBalanceEv', 0))) / 100000000.0,
                        timestamp=datetime.now()
                    )
        return None

    def get_all_balances(self) -> List[Balance]:
        """Get all account balances"""
        if not self.connected:
            logging.error("Not connected to Phemex")
            return []

        path = "/accounts/accountPositions"
        query_params = {"currency": "USD"}  # Using USD as base currency to get all balances

        response = self._make_request("GET", path, query_params=query_params)
        balances = []

        if response and response.get('code') == 0:
            data = response.get('data', {})
            accounts = data.get('accounts', [])

            for account in accounts:
                balance = Balance(
                    asset=account.get('currency'),
                    total=float(account.get('balanceEv', 0)) / 100000000.0,
                    available=float(account.get('availableBalanceEv', 0)) / 100000000.0,
                    reserved=(float(account.get('balanceEv', 0)) - float(account.get('availableBalanceEv', 0))) / 100000000.0,
                    timestamp=datetime.now()
                )
                balances.append(balance)

        return balances

    def place_order(self, order: Order) -> Optional[str]:
        """Place an order and return order ID"""
        if not self.connected:
            logging.error("Not connected to Phemex")
            return None

        path = "/orders"

        # Convert our order type to Phemex format
        side = "Buy" if order.side == OrderSide.BUY else "Sell"

        # Prepare order parameters
        params = {
            "symbol": order.symbol.value,
            "side": side,
            "ordType": order.order_type,
            "orderQty": int(order.quantity * 100000000) if order.quantity else 0,  # Convert to Phemex format
        }

        if order.price:
            params["price"] = int(order.price.amount * 100000000)  # Convert to Phemex format

        if order.stop_price:
            params["stopPxEp"] = int(order.stop_price.amount * 100000000)  # Convert to Phemex format

        if order.time_in_force:
            params["timeInForce"] = order.time_in_force

        response = self._make_request("POST", path, params=params)

        if response and response.get('code') == 0:
            data = response.get('data', {})
            order_id = data.get('orderID', '')
            logging.info(f"Order placed successfully: {order_id}")
            return str(order_id)
        else:
            logging.error(f"Failed to place order: {response}")
            return None

    def get_open_orders(self, symbol: str = None) -> List[Order]:
        """Get open orders"""
        if not self.connected:
            logging.error("Not connected to Phemex")
            return []

        path = "/orders/activeList"
        query_params = {"symbol": symbol} if symbol else {}

        response = self._make_request("GET", path, query_params=query_params)
        orders = []

        if response and response.get('code') == 0:
            data = response.get('data', {})
            open_orders = data.get('rows', [])

            for item in open_orders:
                side = OrderSide.BUY if item.get('side') == 'Buy' else OrderSide.SELL

                orders.append(Order(
                    symbol=Symbol(item.get('symbol')),
                    side=side,
                    quantity=float(item.get('orderQty', 0)) / 100000000.0 if item.get('orderQty') else 0,  # Convert from Phemex format
                    order_type=item.get('ordType', 'MARKET'),
                    price=float(item.get('price', 0)) / 100000000.0 if item.get('price') else None,  # Convert from Phemex format
                    time_in_force=item.get('timeInForce', 'GTC'),
                    client_order_id=item.get('clOrdID')
                ))

        return orders

    def cancel_order(self, order_id: str, symbol: Symbol = None) -> bool:
        """Cancel an order"""
        if not self.connected or not symbol:
            logging.error("Not connected to Phemex or symbol not provided")
            return False

        path = "/orders/cancel"
        params = {
            "symbol": symbol.value,
            "orderID": order_id
        }

        response = self._make_request("DELETE", path, params=params)

        if response and response.get('code') == 0:
            logging.info(f"Order {order_id} cancelled successfully")
            return True
        else:
            logging.error(f"Failed to cancel order {order_id}: {response}")
            return False

    def get_order_status(self, order_id: str, symbol: Symbol = None) -> Optional[Dict[str, Any]]:
        """Get order status"""
        if not self.connected or not symbol:
            logging.error("Not connected to Phemex or symbol not provided")
            return None

        path = "/orders"
        query_params = {
            "symbol": symbol.value,
            "orderID": order_id
        }

        response = self._make_request("GET", path, query_params=query_params)

        if response and response.get('code') == 0:
            data = response.get('data', {})
            return {
                'status': data.get('ordStatus', 'UNKNOWN'),
                'order': data
            }
        else:
            logging.error(f"Failed to get order status for {order_id}: {response}")
            return None

    def get_positions(self) -> List[Position]:
        """Get all positions"""
        if not self.connected:
            logging.error("Not connected to Phemex")
            return []

        path = "/positions/summary"
        query_params = {}

        response = self._make_request("GET", path, query_params=query_params)
        positions = []

        if response and response.get('code') == 0:
            data = response.get('data', {})
            position_list = data.get('position', [])

            for pos in position_list:
                side = 'LONG' if float(pos.get('posQty', 0)) > 0 else 'SHORT'
                positions.append(Position(
                    symbol=Symbol(pos.get('symbol')),
                    side=side,
                    quantity=abs(float(pos.get('posQty', 0))),
                    entry_price=float(pos.get('avgEntryPriceEp', 0)) / 100000000.0 if pos.get('avgEntryPriceEp') else 0,  # Convert from Phemex format
                    unrealized_pnl=float(pos.get('unrealisedPnlEv', 0)) / 100000000.0 if pos.get('unrealisedPnlEv') else 0,  # Convert from Phemex format
                    timestamp=datetime.now()
                ))

        return positions

    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get specific position"""
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None

    def get_available_symbols(self) -> set:
        """Get set of available symbols on Phemex."""
        try:
            # Get exchange info from Phemex API
            path = "/cfg/v2/products"
            response = self._make_request("GET", path)

            if response and response.get('code') == 0:
                symbols = set()
                data = response.get('data', {}).get('products', [])

                for product in data:
                    if product.get('status') == 'Listed':  # Only include listed trading pairs
                        # Ensure symbol is in the correct format (e.g., BTCUSDT)
                        symbol = product['symbol']
                        symbols.add(symbol.upper())  # Normalize to uppercase
                return symbols
        except Exception as e:
            # If API call fails, return empty set
            pass

        # Return empty set if all attempts fail
        return set()

    def get_all_positions(self) -> List[Position]:
        return self.get_positions()
