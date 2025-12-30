from typing import Dict, Optional, List, Union, Any
import hmac
import hashlib
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
from enum import Enum
import json
import traceback

from domain.entities.trading_entities import Order, Fill, Position, Balance, OrderSide, PositionSide
from domain.ports.broker_ports import BrokerPort
from domain.value_objects import Symbol, Money
from infrastructure.data.adapters.rest_client import RestClient
from infrastructure.brokers.symbol_format_helper import SymbolFormatHelper


class BingXBrokerAdapter(BrokerPort):
    def __init__(self, config: Dict):
        self._broker = _BingXBroker(config)
        self.connected = False

    def _format_symbol(self, symbol: Union[Symbol, str]) -> str:
        """Formats the domain symbol to the broker's expected format using the helper."""
        # Handle both string and Symbol object formats
        if isinstance(symbol, str):
            symbol_str = symbol
        else:
            # If it's a Symbol object, get its value
            if hasattr(symbol, 'value'):
                symbol_str = symbol.value
            else:
                # Fallback: convert to string
                symbol_str = str(symbol)

        # Use the symbol format helper to format for BingX
        return SymbolFormatHelper.format_symbol_for_exchange(symbol_str, 'bingx')

    def _parse_symbol(self, symbol_str: str) -> Symbol:
        """Parses the broker's symbol string into a domain Symbol."""
        return Symbol(symbol_str.replace("-", ""))

    def connect(self):
        try:
            if self._broker.get_account_balance():
                self.connected = True
                return True
            return False
        except Exception:
            self.connected = False
            return False

    def disconnect(self):
        self.connected = False

    def place_order(self, order: Order) -> str:
        if not self.connected:
            self.connect()

        # Instead of modifying the order, we'll modify the internal broker to handle symbol formatting
        # For now, let's pass the original order and handle formatting inside the internal broker
        # by monkey-patching the symbol temporarily

        # Store original symbol
        original_symbol = order.symbol

        # Format the symbol for the API call
        formatted_symbol = self._format_symbol(original_symbol)

        # Temporarily modify the order's symbol for the API call
        # We'll create a temporary order with the formatted symbol
        from domain.entities.trading_entities import Order as DomainOrder
        from datetime import datetime

        # Create a temporary order with the formatted symbol but preserve all other attributes
        temp_order = DomainOrder(
            symbol=formatted_symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            strategy_name=getattr(order, 'strategy_name', 'unknown'),
            timestamp=getattr(order, 'timestamp', datetime.now()),
            position_side=getattr(order, 'position_side', 'BOTH'),
            stop_price=getattr(order, 'stop_price', None),
            time_in_force=getattr(order, 'time_in_force', 'GTC'),
            client_order_id=getattr(order, 'client_order_id', None),
            parent_signal=getattr(order, 'parent_signal', None),
            risk_adjusted_quantity=getattr(order, 'risk_adjusted_quantity', None)
        )

        result = self._broker.execute_order(temp_order)
        if result['success']:
            return result['order_id']
        else:
            raise Exception(f"Failed to place order: {result['error']}")

    def cancel_order(self, order_id: str, symbol: Symbol) -> bool:
        if not self.connected:
            self.connect()
        return self._broker.cancel_order(order_id, self._format_symbol(symbol))

    def get_order_status(self, order_id: str, symbol: Symbol) -> str:
        if not self.connected:
            self.connect()
        return self._broker.get_order_status(order_id, self._format_symbol(symbol))

    def get_balance(self, asset: str = None) -> List[Balance]:
        if not self.connected:
            self.connect()

        balances_data = self._broker.get_account_balance()
        balances = []
        for b in balances_data:
            if asset is None or b.get('asset') == asset:
                total = float(b.get('balance', 0))
                available = float(b.get('availableMargin', 0))
                balances.append(
                    Balance(
                        asset=b.get('asset'),
                        total=Money(amount=total, currency=b.get('asset')),
                        available=Money(amount=available, currency=b.get('asset')),
                        reserved=Money(amount=total - available, currency=b.get('asset')),
                        timestamp=datetime.now()
                    )
                )
        return balances

    def get_position(self, symbol: Symbol) -> Optional[Position]:
        if not self.connected:
            self.connect()

        positions = self.get_all_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None

    def get_all_positions(self) -> List[Position]:
        if not self.connected:
            self.connect()

        positions_data = self._broker.get_open_positions()
        positions = []
        for p in positions_data:
            quantity = float(p['positionAmt'])
            # Handle both possible field names for unrealized PnL
            pnl_value = float(p.get('unrealisedPnl', p.get('unrealizedPnl', 0)))
            positions.append(
                Position(
                    symbol=self._parse_symbol(p['symbol']),
                    side=PositionSide.LONG if quantity > 0 else PositionSide.SHORT,
                    quantity=abs(quantity),
                    entry_price=Money(amount=float(p['avgPrice']), currency='USDT'),
                    unrealized_pnl=Money(amount=pnl_value, currency='USDT'),
                    timestamp=datetime.fromtimestamp(int(p.get('time', time.time()*1000)) / 1000)
                )
            )
        return positions

    def get_available_symbols(self) -> set:
        """Get set of available symbols on this broker."""
        if not self.connected:
            self.connect()
        return self._broker.get_available_symbols()


class _BingXBroker:
    """BingX broker implementation with full API coverage."""

    def __init__(self, config: Dict):
        self.name = config.get('name', 'bingx')
        self.api_key = config['api_key']
        self.secret_key = config['secret_key']
        self.passphrase = config.get('passphrase', '')
        self.testnet = config.get('testnet', True)

        # Base URLs
        if self.testnet:
            self.base_url = "https://open-api-vst.bingx.com"  # Testnet (simulation)
        else:
            self.base_url = "https://open-api.bingx.com"  # Live trading

        self.logger = logging.getLogger(__name__)

        # Rate limiting settings
        self.requests_per_minute = 1200
        self.min_request_interval = 0.05  # 50ms between requests
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'X-BX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        })

        # Set default timeout for all requests
        self.default_timeout = 10  # 10 seconds

    def _generate_signature(self, params_str: str) -> str:
        """Generate signature for BingX API authentication."""
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            params_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _rate_limit(self) -> None:
        """Implement rate limiting for API requests."""
        current_time = time.time()

        # Reset counter if window has passed
        if current_time - self.request_window_start >= 60:
            self.request_count = 0
            self.request_window_start = current_time

        # Check if we've hit the rate limit
        if self.request_count >= self.requests_per_minute:
            sleep_time = 60 - (current_time - self.request_window_start)
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.request_count = 0
            self.request_window_start = time.time()

        # Ensure minimum interval between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)

        self.last_request_time = time.time()
        self.request_count += 1

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None,
                      signed: bool = False) -> Dict:
        """Make authenticated request to BingX API."""
        try:
            self._rate_limit()
            url = f"{self.base_url}{endpoint}"
            headers = {
                'X-BX-APIKEY': self.api_key
            }

            if signed:
                all_params = {}
                if params:
                    all_params.update(params)
                if data:
                    all_params.update(data)

                all_params['timestamp'] = str(int(time.time() * 1000))

                param_strings = []
                for key in sorted(all_params.keys()):
                    param_strings.append(f"{key}={all_params[key]}")

                query_string = '&'.join(param_strings)

                signature = hmac.new(
                    self.secret_key.encode('utf-8'),
                    query_string.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()

                query_string_with_signature = query_string + f"&signature={signature}"

                if method.upper() == 'POST':
                    headers['Content-Type'] = 'application/x-www-form-urlencoded'

                full_url = f"{url}?{query_string_with_signature}"
                timeout = getattr(self, 'default_timeout', 10)
                if method.upper() == 'DELETE':
                    response = self.session.delete(full_url, headers=headers, timeout=timeout)
                elif method.upper() == 'GET':
                    response = self.session.get(full_url, headers=headers, timeout=timeout)
                elif method.upper() == 'POST':
                    response = self.session.post(full_url, headers=headers, timeout=timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method for signed request: {method}")
            else:
                is_klines_request = '/quote/klines' in endpoint

                timeout = getattr(self, 'default_timeout', 10)
                if method.upper() == 'GET':
                    if is_klines_request:
                        klines_headers = {}
                        response = self.session.get(url, headers=klines_headers, params=params, timeout=timeout)
                    else:
                        response = self.session.get(url, headers=headers, params=params, timeout=timeout)
                elif method.upper() == 'POST':
                    response = self.session.post(url, headers=headers, json=data or params, timeout=timeout)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, headers=headers, params=params, timeout=timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}\n{traceback.format_exc()}")
            raise
        except Exception as e:
            self.logger.error(f"Error in _make_request: {str(e)}\nFull traceback:\n{traceback.format_exc()}")
            raise ValueError(f"Request preparation failed: {str(e)}") from e

    def execute_order(self, order: Order) -> Dict[str, Any]:
        """Execute order on BingX."""
        try:
            # Handle the symbol formatting here
            # If symbol is a string, use it directly; if it's a Symbol object, get its value
            if isinstance(order.symbol, str):
                symbol_formatted = order.symbol
            else:
                # If it's a Symbol object, get its string representation
                if hasattr(order.symbol, 'value'):
                    symbol_formatted = order.symbol.value
                else:
                    symbol_formatted = str(order.symbol)

            # Ensure side is handled properly
            if hasattr(order.side, 'value'):
                side_value = order.side.value
            else:
                side_value = str(order.side)

            # Ensure order_type is handled properly
            if hasattr(order.order_type, 'value'):
                order_type_value = order.order_type.value
            else:
                order_type_value = str(order.order_type)

            # Handle position_side similarly
            if hasattr(order, 'position_side') and order.position_side:
                if hasattr(order.position_side, 'value'):
                    position_side_value = order.position_side.value
                else:
                    position_side_value = str(order.position_side)
            else:
                # For BingX, if position_side is not specified, determine it based on order side
                # For LONG positions with BUY orders or SHORT positions with SELL orders
                if order.side == OrderSide.BUY:
                    position_side_value = 'LONG'
                elif order.side == OrderSide.SELL:
                    position_side_value = 'SHORT'
                else:
                    position_side_value = 'BOTH'

            order_data = {
                'symbol': symbol_formatted,
                'side': side_value.upper(),
                'type': order_type_value.upper(),
                'quantity': str(round(float(order.quantity), 6))
            }

            order_data['positionSide'] = position_side_value

            if order.price:
                # Handle both Money object and float/numeric values
                if hasattr(order.price, 'amount'):
                    # If it's a Money object, use the amount attribute
                    price_value = order.price.amount
                else:
                    # If it's already a numeric value, use it directly
                    price_value = order.price
                order_data['price'] = str(price_value)

            # Add Stop Loss and Take Profit parameters if they exist in the order
            # According to the BingX API, these should be separate parameters in the same request
            if hasattr(order, 'stop_loss_price') and order.stop_loss_price:
                # For stop loss, BingX expects stopLossPrice parameter
                # Handle both Money object and float/numeric values
                if hasattr(order.stop_loss_price, 'amount'):
                    sl_price_value = order.stop_loss_price.amount
                else:
                    sl_price_value = order.stop_loss_price
                order_data['stopLossPrice'] = str(sl_price_value)

            if hasattr(order, 'take_profit_price') and order.take_profit_price:
                # For take profit, BingX expects takeProfitPrice parameter
                # Handle both Money object and float/numeric values
                if hasattr(order.take_profit_price, 'amount'):
                    tp_price_value = order.take_profit_price.amount
                else:
                    tp_price_value = order.take_profit_price
                order_data['takeProfitPrice'] = str(tp_price_value)

            endpoint = "/openApi/swap/v2/trade/order"
            response = self._make_request('POST', endpoint, data=order_data, signed=True)

            if response.get('code') == 0:
                order_info = response.get('data', {}).get('order', {})
                return {
                    'success': True,
                    'order_id': order_info.get('orderId'),
                    'response': response['data']
                }
            else:
                return {
                    'success': False,
                    'error': response.get('msg', 'Unknown error')
                }
        except Exception as e:
            self.logger.error(f"Failed to execute order: {e}")
            return {'success': False, 'error': str(e)}

    def get_account_balance(self) -> List[Dict[str, Any]]:
        """Get account balance information."""
        try:
            response = self._make_request('GET', '/openApi/swap/v2/user/balance', signed=True)

            if response.get('code') != 0:
                raise ValueError(f"API error: {response.get('msg', 'Unknown error')}")

            balance_data = response.get('data', {})
            # The actual response is {'code': 0, 'msg': '', 'data': {'balance': {..}}}
            if 'balance' in balance_data:
                return [balance_data['balance']]
            return []
        except Exception as e:
            self.logger.error(f"Failed to get balance: {str(e)}")
            return []

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        try:
            params = {
                'symbol': symbol,
                'orderId': order_id
            }

            response = self._make_request('DELETE', '/openApi/swap/v2/trade/order', params=params, signed=True)
            return response.get('code') == 0

        except Exception as e:
            self.logger.error(f"Failed to cancel order: {str(e)}")
            return False

    def get_order_status(self, order_id: str, symbol: str) -> str:
        pending_orders = self.get_pending_orders(symbol)
        for order in pending_orders:
            if order.get('orderId') == order_id:
                return order.get('status')

        history = self.get_order_history(symbol, limit=100)
        for order in history:
            if order.get('orderId') == order_id:
                return order.get('status')

        return "UNKNOWN"

    def get_pending_orders(self, symbol: str = None) -> List[Dict]:
        """Get all pending orders."""
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol

            response = self._make_request('GET', '/openApi/swap/v2/trade/openOrders', params=params, signed=True)

            if response.get('code') == 0:
                data = response.get('data', {})
                if isinstance(data, dict) and 'orders' in data:
                    return data['orders']
                elif isinstance(data, list):
                    return data
                else:
                    return []
            else:
                return []
        except Exception as e:
            return []

    def get_order_history(
            self,
            symbol: str = None,
            start_time: Optional[datetime] = None,
            end_time: Optional[datetime] = None,
            limit: int = 500
    ) -> List[Dict]:
        """Get order history."""
        try:
            params = {'limit': limit}
            if symbol:
                params['symbol'] = symbol
            if start_time:
                params['startTime'] = int(start_time.timestamp() * 1000)
            if end_time:
                params['endTime'] = int(end_time.timestamp() * 1000)

            response = self._make_request('GET', '/openApi/swap/v2/trade/allOrders', params=params, signed=True)

            if response.get('code') == 0:
                data = response.get('data', {})
                if isinstance(data, dict) and 'orders' in data:
                    return data['orders']
                elif isinstance(data, list):
                    return data
                else:
                    return []
            else:
                return []
        except Exception as e:
            return []

    def get_available_symbols(self) -> set:
        """Get set of available symbols on BingX."""
        try:
            # Get exchange info from BingX API
            response = self._make_request('GET', '/openApi/quote/v1/ticker/24hr', signed=False)

            if response.get('code') == 0:
                symbols = set()
                data = response.get('data', [])
                if isinstance(data, list):
                    for item in data:
                        if 'symbol' in item:
                            # Convert from BingX format (e.g., BTC-USDT) to our format (BTCUSDT)
                            symbol = item['symbol'].replace('-', '')
                            symbols.add(symbol)
                return symbols
            else:
                # Fallback: try another endpoint
                response2 = self._make_request('GET', '/openApi/quote/v1/ticker/price', signed=False)
                if response2.get('code') == 0:
                    symbols = set()
                    data = response2.get('data', [])
                    if isinstance(data, list):
                        for item in data:
                            if 'symbol' in item:
                                symbol = item['symbol'].replace('-', '')
                                symbols.add(symbol)
                    return symbols
        except Exception as e:
            # If API call fails, return empty set
            pass

        # Return empty set if all attempts fail
        return set()

    def get_open_positions(self, symbol: str=None) -> List[Dict]:
        """Get all open positions."""
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol
            response = self._make_request('GET', '/openApi/swap/v2/user/positions', signed=True, params=params)

            if response.get('code') == 0:
                return response.get('data', [])
            else:
                return []

        except Exception as e:
            return []