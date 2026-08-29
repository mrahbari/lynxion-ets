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
import uuid
import threading

from domain.entities import Order, Fill, Position, Balance, OrderSide, PositionSide
from domain.ports.broker_ports import BrokerPort
from domain.value_objects import Symbol, Money
from infrastructure.data.adapters.rest_client import RestClient
from infrastructure.brokers.symbol_format_helper import SymbolFormatHelper
from shared.rate_limiter import global_rate_limiter
from shared.utils import format_price_for_api


_BINGX_ENTRY_ADMISSION_LOCK = threading.RLock()


def ensure_client_order_id(order) -> str:
    """B2: return the order's client_order_id, generating + assigning one once if absent.

    Assigning back to the order means a retry of the SAME order object reuses the id, so
    the exchange can deduplicate (idempotency). BingX clientOrderID: alphanumeric, <=40 chars.
    """
    coid = getattr(order, "client_order_id", None)
    if not coid:
        coid = "x" + uuid.uuid4().hex[:30]
        try:
            order.client_order_id = coid
        except Exception:
            pass
    return coid


class BingXBrokerAdapter(BrokerPort):
    def __init__(self, config: Dict):
        self._broker = _BingXBroker(config)
        self.connected = False
        # Initialize logger for the adapter
        import logging
        self.logger = logging.getLogger(__name__)

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

        # Universal fail-closed check for SymbolCooldownGate
        try:
            from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
            allowed, reason = symbol_cooldown_gate.is_symbol_allowed(order.symbol)
            if not allowed:
                self.logger.warning(f"🛑 [BINGX GATE] Order REJECTED for {order.symbol}: {reason}")
                raise ValueError(f"Symbol {order.symbol} blocked by Risk Health Gate: {reason}")
        except ValueError:
            raise
        except Exception as gate_err:
            self.logger.error(f"SymbolCooldownGate unavailable in place_order; rejecting order: {gate_err}")
            raise RuntimeError(f"Risk Health Gate unavailable; order rejected: {gate_err}") from gate_err

        # Store original symbol
        original_symbol = order.symbol

        # Format the symbol for the API call
        formatted_symbol = self._format_symbol(original_symbol)

        # Temporarily modify the order's symbol for the API call
        # We'll create a temporary order with the formatted symbol
        from domain.entities import Order as DomainOrder
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
            risk_adjusted_quantity=getattr(order, 'risk_adjusted_quantity', None),
            stop_loss_price=getattr(order, 'stop_loss_price', None),  # Add stop loss price
            take_profit_price=getattr(order, 'take_profit_price', None)  # Add take profit price
        )

        result = self._broker.execute_order(temp_order)
        if result.get('success') and not result.get('protection_failed') and not result.get('conditional_orders_errors'):
            return result['order_id']
        else:
            error_msg = result.get('error') or f"protective orders failed: {result.get('conditional_orders_errors')}"
            # Make error messages more readable
            if 'error code:109400' in error_msg or 'Rate Limit' in error_msg or 'rate limit' in error_msg:
                readable_error = "API Rate Limit Exceeded: Too many requests to BingX API. Please reduce request frequency."
            elif 'over 20' in error_msg and 'requests within' in error_msg:
                readable_error = "Rate Limit Exceeded: Exceeded BingX API request limits. Consider implementing request throttling."
            elif 'TriggerClose' in error_msg or 'stop loss' in error_msg.lower() or 'take profit' in error_msg.lower() or 'stopLoss' in error_msg or 'takeProfit' in error_msg or 'stopLossPrice' in error_msg or 'takeProfitPrice' in error_msg:
                readable_error = "API Parameter Error: Invalid parameter format for stop loss/take profit. Check parameter formatting. Ensure SL/TP prices are properly formatted as strings with appropriate decimal precision."
            else:
                readable_error = f"Order placement failed: {error_msg}"

            raise Exception(f"Failed to place order: {readable_error}")

    def cancel_order(self, order_id: str, symbol: Symbol) -> bool:
        if not self.connected:
            self.connect()
        return self._broker.cancel_order(order_id, self._format_symbol(symbol))

    def get_order_status(self, order_id: str, symbol: Symbol) -> str:
        if not self.connected:
            self.connect()
        return self._broker.get_order_status(order_id, self._format_symbol(symbol))

    def get_order_fill(self, order_id: str, symbol: Symbol) -> Dict[str, Any]:
        """B7: return {status, executed_qty, avg_price} for partial-fill tracking."""
        if not self.connected:
            self.connect()
        return self._broker.get_order_fill(order_id, self._format_symbol(symbol))

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

    def _place_conditional_order(self, symbol: str, side: str, quantity: str, stop_price: str,
                                order_type: str, position_side: str) -> Dict[str, Any]:
        """Place a conditional order via internal broker."""
        if not self.connected:
            self.connect()
        return self._broker._place_conditional_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            order_type=order_type,
            position_side=position_side
        )

    def get_position(self, symbol) -> Optional[Position]:
        from domain.value_objects import Symbol as DomainSymbol
        symbol_obj = symbol if hasattr(symbol, 'value') else DomainSymbol(str(symbol))
        if not self.connected:
            self.connect()

        positions = self.get_all_positions()
        for pos in positions:
            if pos.symbol == symbol_obj:
                return pos
        return None

    def get_all_positions(self) -> List[Position]:
        if not self.connected:
            self.connect()

        positions_data = self._broker.get_open_positions()
        positions = []
        for p in positions_data:
            # B4 resilience: one malformed/exotic exchange symbol must never break position
            # reconciliation for the whole account — skip it (logged) and keep the rest.
            try:
                quantity = float(p['positionAmt'])
                if quantity == 0:
                    continue  # not an open position
                pnl_value = float(p.get('unrealisedPnl', p.get('unrealizedPnl', 0)))
                mark_p = float(p.get('markPrice', 0) or p.get('mark_price', 0) or 0)
                pos_side_raw = str(p.get('positionSide', '')).upper()
                is_short_side = pos_side_raw == 'SHORT' or float(p['positionAmt']) < 0
                positions.append(
                    Position(
                        symbol=self._parse_symbol(p['symbol']),
                        side=PositionSide.SHORT if is_short_side else PositionSide.LONG,
                        quantity=abs(quantity),
                        entry_price=Money(amount=float(p['avgPrice']), currency='USDT'),
                        unrealized_pnl=Money(amount=pnl_value, currency='USDT'),
                        timestamp=datetime.fromtimestamp(int(p.get('time', time.time() * 1000)) / 1000),
                        mark_price=mark_p
                    )
                )
            except Exception as e:
                self.logger.warning(f"Skipping unparseable position {p.get('symbol')!r}: {e}")
                continue
        return positions

    def get_available_symbols(self) -> set:
        """Get set of available symbols on this broker."""
        if not self.connected:
            self.connect()
        return self._broker.get_available_symbols()

    def get_pending_orders(self, symbol: Any = None) -> List[Dict]:
        """Get pending orders for a symbol or all symbols."""
        if not self.connected:
            self.connect()
        sym_str = self._format_symbol(symbol) if symbol else None
        return self._broker.get_pending_orders(sym_str)

    def _place_conditional_order(self, symbol: Any, side: str, quantity: str, stop_price: str,
                                order_type: str, position_side: str) -> Dict[str, Any]:
        """Place a conditional stop order directly on the exchange."""
        if not self.connected:
            self.connect()
        sym_str = self._format_symbol(symbol)
        return self._broker._place_conditional_order(
            symbol=sym_str,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            order_type=order_type,
            position_side=position_side
        )

    def _unwind_position(self, symbol: Any, original_side: str, quantity: str, position_side: str) -> Dict[str, Any]:
        """Execute market unwind for position close."""
        if not self.connected:
            self.connect()
        sym_str = self._format_symbol(symbol)
        return self._broker._unwind_position(
            symbol=sym_str,
            original_side=original_side,
            quantity=quantity,
            position_side=position_side
        )


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

        # Rate limiting settings - responsive and safe
        self.requests_per_minute = 300
        self.min_request_interval = 0.2  # 200ms between requests for fast trailing SL sync
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'X-BX-APIKEY': self.api_key
        })

        # Set default timeout for all requests
        self.default_timeout = 10  # 10 seconds
        self._contract_precisions = {}

    def _generate_signature(self, params_str: str) -> str:
        """Generate signature for BingX API authentication."""
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            params_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _rate_limit(self) -> None:
        """Implement rate limiting for API requests using global rate limiter."""
        # Wait for a token from the global rate limiter for BingX
        global_rate_limiter.wait_for_tokens('bingx', 1)

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None,
                      signed: bool = False) -> Dict:
        """Make authenticated request to BingX API with transient fault retries."""
        try:
            self._rate_limit()  # Apply rate limiting before making the request
            url = f"{self.base_url}{endpoint}"
            headers = {
                'X-BX-APIKEY': self.api_key
            }

            def send_api_call():
                if signed:
                    all_params = {}
                    if params:
                        all_params.update(params)
                    if data:
                        all_params.update(data)

                    # Update timestamp on each attempt to prevent signature expiry/skew
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

            def should_retry_request(exc: BaseException) -> bool:
                if isinstance(exc, requests.exceptions.HTTPError):
                    if exc.response is not None:
                        # Retry on 429 Rate Limit or 5xx Server errors
                        return exc.response.status_code == 429 or exc.response.status_code >= 500
                elif isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                    return True
                return False

            from shared.retry import retry_with_backoff
            return retry_with_backoff(
                send_api_call,
                max_attempts=3,
                base_delay=0.5,
                retry_on=(requests.exceptions.RequestException,),
                should_retry=should_retry_request,
                on_retry=lambda attempt, exc, delay: self.logger.warning(
                    f"⚠️ BingX API {method} {endpoint} failed (attempt {attempt}): {exc}; retrying in {delay:.2f}s..."
                )
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}\n{traceback.format_exc()}")
            raise
        except Exception as e:
            self.logger.error(f"Error in _make_request: {str(e)}\nFull traceback:\n{traceback.format_exc()}")
            raise ValueError(f"Request preparation failed: {str(e)}") from e

    def _fetch_all_contracts(self) -> None:
        """Fetch all swap contracts and cache their precisions."""
        try:
            # signed=False because contracts endpoint is public
            response = self._make_request('GET', '/openApi/swap/v2/quote/contracts', signed=False)
            if response.get('code') == 0:
                data = response.get('data', [])
                for contract_info in data:
                    symbol = contract_info.get('symbol')
                    if symbol:
                        self._contract_precisions[symbol] = {
                            'pricePrecision': int(contract_info.get('pricePrecision', 4)),
                            'quantityPrecision': int(contract_info.get('quantityPrecision', 4))
                        }
                self.logger.info(f"Successfully cached precision info for {len(self._contract_precisions)} BingX contracts.")
        except Exception as e:
            self.logger.error(f"Failed to fetch and cache contract precisions: {e}")

    def _get_contract_precision(self, symbol: str) -> Dict[str, int]:
        """Get the cached precision info for the symbol, fetching it if not present."""
        if not hasattr(self, '_contract_precisions'):
            self._contract_precisions = {}
        api_symbol = symbol
        if '-' not in symbol:
            if symbol.endswith('USDT'):
                api_symbol = symbol[:-4] + '-' + symbol[-4:]
            elif symbol.endswith('USDC'):
                api_symbol = symbol[:-4] + '-' + symbol[-4:]
                
        if not self._contract_precisions:
            if hasattr(self, 'api_key') and hasattr(self, 'base_url') and self.api_key:
                self._fetch_all_contracts()
            
        if api_symbol in self._contract_precisions:
            return self._contract_precisions[api_symbol]
            
        if hasattr(self, 'api_key') and hasattr(self, 'base_url') and self.api_key:
            try:
                response = self._make_request('GET', '/openApi/swap/v2/quote/contracts', params={'symbol': api_symbol}, signed=False)
                if response.get('code') == 0:
                    data = response.get('data', [])
                    if data and isinstance(data, list):
                        contract_info = data[0]
                        precision_info = {
                            'pricePrecision': int(contract_info.get('pricePrecision', 4)),
                            'quantityPrecision': int(contract_info.get('quantityPrecision', 4))
                        }
                        self._contract_precisions[api_symbol] = precision_info
                        return precision_info
            except Exception as e:
                self.logger.warning(f"Failed to fetch contract precision for {api_symbol}: {e}")
            
        return {'pricePrecision': 4, 'quantityPrecision': 4}

    def _format_price(self, symbol: str, price: float) -> str:
        """Format price according to the symbol's actual pricePrecision on the exchange."""
        precision_info = self._get_contract_precision(symbol)
        precision = precision_info.get('pricePrecision', 4)
        return f"{price:.{precision}f}"

    def _format_quantity(self, symbol: str, quantity: float) -> str:
        """Format quantity according to the symbol's actual quantityPrecision on the exchange."""
        precision_info = self._get_contract_precision(symbol)
        precision = precision_info.get('quantityPrecision', 4)
        return f"{quantity:.{precision}f}"

    def _assert_entry_admission(self, order: Order) -> tuple[bool, str]:
        """Fail-closed final risk check against the authoritative broker snapshot."""
        try:
            from infrastructure.risk.risk_enforcement import build_vst_risk_enforcement

            allowed, reason = build_vst_risk_enforcement().enforce(order)
            if not allowed:
                return False, reason

            response = self._make_request(
                'GET', '/openApi/swap/v2/user/positions', signed=True, params={}
            )
            if response.get('code') != 0 or not isinstance(response.get('data'), list):
                return False, "broker position snapshot unavailable or malformed"

            open_positions = []
            for position in response['data']:
                quantity = abs(float(position.get('positionAmt', 0) or 0))
                if quantity > 0:
                    open_positions.append(position)

            from bootstrap.settings.loaders import load_settings
            settings = load_settings()
            max_open_positions = int(getattr(settings.safety, 'max_open_positions', 5))
            if len(open_positions) >= max_open_positions:
                return False, (
                    f"portfolio capacity reached: {len(open_positions)} open positions "
                    f">= configured maximum {max_open_positions}"
                )

            from infrastructure.services.symbol_validator import symbol_validator
            requested_symbol = symbol_validator.normalize_symbol(order.symbol)
            for position in open_positions:
                if symbol_validator.normalize_symbol(position.get('symbol')) == requested_symbol:
                    return False, f"duplicate position blocked: {requested_symbol} is already open"

            current_exposure = sum(
                abs(float(position.get('positionAmt', 0) or 0))
                * float(position.get('markPrice', 0) or position.get('avgPrice', 0) or 0)
                for position in open_positions
            )
            order_price = float(getattr(getattr(order, 'price', None), 'amount', 0) or 0)
            order_notional = abs(float(getattr(order, 'quantity', 0) or 0)) * order_price
            max_portfolio_exposure = 1_000.0
            if current_exposure + order_notional > max_portfolio_exposure:
                return False, (
                    f"portfolio exposure limit exceeded: ${current_exposure + order_notional:.2f} "
                    f"> ${max_portfolio_exposure:.2f}"
                )
            return True, "broker-backed risk admission approved"
        except Exception as admission_error:
            return False, f"broker-backed risk admission error: {admission_error}"

    def execute_order(self, order: Order) -> Dict[str, Any]:
        """Execute only after an atomic, broker-backed, fail-closed risk admission."""
        with _BINGX_ENTRY_ADMISSION_LOCK:
            allowed, reason = self._assert_entry_admission(order)
            if not allowed:
                self.logger.error(f"🛑 [BINGX RISK ADMISSION] Order REJECTED: {reason}")
                return {"success": False, "order_id": None, "error": reason}
            return self._execute_order_after_admission(order)

    def _execute_order_after_admission(self, order: Order) -> Dict[str, Any]:
        """Perform the exchange request after final admission has succeeded."""
        try:
            # Final exchange-boundary admission check.  Some recovery/service paths
            # call this low-level method directly instead of adapter.place_order().
            try:
                from infrastructure.services.symbol_validator import symbol_validator
                clean_symbol = symbol_validator.normalize_symbol(order.symbol)
                blacklisted = symbol_validator.get_blacklisted_symbols()
                if clean_symbol in blacklisted:
                    reason = f"PERMANENT_BLACKLIST: {clean_symbol} is blacklisted from trading in configuration"
                    self.logger.warning(f"🛑 [BINGX FINAL GATE] Order REJECTED for {order.symbol}: {reason}")
                    return {"success": False, "order_id": None, "error": reason}
            except Exception as gate_err:
                self.logger.error(f"BingX final risk gate unavailable; rejecting order: {gate_err}")
                return {
                    "success": False,
                    "order_id": None,
                    "error": f"Risk Health Gate unavailable: {gate_err}",
                }

            # Handle the symbol formatting here
            # Ensure symbol is properly formatted for BingX REST API (must include hyphen, e.g. XMR-USDT)
            if isinstance(order.symbol, str):
                raw_sym = order.symbol
            elif hasattr(order.symbol, 'value'):
                raw_sym = str(order.symbol.value)
            else:
                raw_sym = str(order.symbol)

            if '-' not in raw_sym:
                if raw_sym.endswith('USDT') or raw_sym.endswith('USDC'):
                    symbol_formatted = raw_sym[:-4] + '-' + raw_sym[-4:]
                else:
                    symbol_formatted = raw_sym
            else:
                symbol_formatted = raw_sym

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
                side_upper = side_value.upper()
                if side_upper == 'BUY':
                    position_side_value = 'LONG'
                elif side_upper == 'SELL':
                    position_side_value = 'SHORT'
                else:
                    position_side_value = 'BOTH'

            # B2 idempotency: ensure a client order id is sent so the exchange can dedupe.
            client_order_id = ensure_client_order_id(order)

            order_data = {
                'symbol': symbol_formatted,
                'side': side_value.upper(),
                'type': order_type_value.upper(),
                'quantity': self._format_quantity(symbol_formatted, float(order.quantity)),
                'positionSide': position_side_value,
                'clientOrderID': client_order_id,
            }

            if order.price:
                # Handle both Money object and float/numeric values
                if hasattr(order.price, 'amount'):
                    # If it's a Money object, use the amount attribute
                    price_value = order.price.amount
                else:
                    # If it's already a numeric value, use it directly
                    price_value = order.price
                # Format price using exchange-specific precision
                formatted_price = self._format_price(symbol_formatted, float(price_value))
                order_data['price'] = formatted_price

            # Add Stop Loss and Take Profit parameters if they exist in the order
            # According to the BingX API documentation, these should be separate parameters in the same request
            # For setting SL/TP with market orders, use stopLossPrice and takeProfitPrice (not stopLoss/takeProfit)
            # The error suggests that the API expects different parameter names or format
            has_stop_loss = hasattr(order, 'stop_loss_price') and order.stop_loss_price is not None
            has_take_profit = hasattr(order, 'take_profit_price') and order.take_profit_price is not None

            if has_stop_loss:
                # For stop loss, use stopLossPrice parameter (according to API docs)
                # Handle both Money object and float/numeric values
                if hasattr(order.stop_loss_price, 'amount'):
                    sl_price_value = order.stop_loss_price.amount
                else:
                    sl_price_value = order.stop_loss_price
                # Format as string with appropriate precision to avoid type issues
                # Ensure the value is properly formatted as a string to avoid type mismatch
                if sl_price_value is not None:
                    # Format as string to ensure proper type handling by the API
                    # Use the new API-compliant formatting function to avoid precision issues
                    # Convert to float first to handle Decimal objects properly
                    sl_float = float(sl_price_value)
                    # Validate that the stop loss price is a valid positive number
                    if sl_float <= 0:
                        self.logger.warning(f"Invalid stop loss price: {sl_float}, skipping...")
                    else:
                        formatted_sl_price = self._format_price(symbol_formatted, sl_float)
                        order_data['stopLossPrice'] = formatted_sl_price  # Changed from 'stopLoss' to 'stopLossPrice'
                        self.logger.debug(f"Added stop loss price: {formatted_sl_price}")

            if has_take_profit:
                # For take profit, use takeProfitPrice parameter (according to API docs)
                # Handle both Money object and float/numeric values
                if hasattr(order.take_profit_price, 'amount'):
                    tp_price_value = order.take_profit_price.amount
                else:
                    tp_price_value = order.take_profit_price
                # Format as string with appropriate precision to avoid type issues
                # Ensure the value is properly formatted as a string to avoid type mismatch
                if tp_price_value is not None:
                    # Format as string to ensure proper type handling by the API
                    # Use the new API-compliant formatting function to avoid precision issues
                    # Convert to float first to handle Decimal objects properly
                    tp_float = float(tp_price_value)
                    # Validate that the take profit price is a valid positive number
                    if tp_float <= 0:
                        self.logger.warning(f"Invalid take profit price: {tp_float}, skipping...")
                    else:
                        formatted_tp_price = self._format_price(symbol_formatted, tp_float)
                        order_data['takeProfitPrice'] = formatted_tp_price  # Changed from 'takeProfit' to 'takeProfitPrice'
                        self.logger.debug(f"Added take profit price: {formatted_tp_price}")

            # When stop loss or take profit is specified, we may need to set additional parameters
            # depending on the order type and API requirements
            # For market orders with SL/TP, we might need to place them as separate conditional orders
            # This is a common pattern in many exchanges
            if has_stop_loss or has_take_profit:
                # Check if this is a market order with SL/TP attached
                if order_type_value.upper() == 'MARKET':
                    # For market orders with SL/TP, we might need to place the main order first,
                    # then place separate conditional orders for SL/TP
                    # This is often the correct approach for many exchanges
                    self.logger.debug(f"Processing market order with SL/TP - attempting to place main order with attached SL/TP: SL={has_stop_loss}, TP={has_take_profit}")

                    # For now, let's continue with the current approach but add better error handling
                    # If the single order approach fails, we'll need to implement the separate order approach
                else:
                    # For LIMIT orders with SL/TP, the attachment should work directly
                    self.logger.debug(f"Processing limit order with SL/TP attached: SL={has_stop_loss}, TP={has_take_profit}")

            # Check if we have SL/TP and it's a market order - we might need to handle this differently
            if (has_stop_loss or has_take_profit) and order_type_value.upper() == 'MARKET':
                # For market orders with SL/TP, we may need to place the main order first,
                # then place separate conditional orders for SL/TP
                # This is a common pattern in many exchanges
                self.logger.info(f"Placing market order with separate SL/TP handling for {symbol_formatted}")

                # First, create the main market order without SL/TP
                main_order_data = {
                    'symbol': symbol_formatted,
                    'side': side_value.upper(),
                    'type': order_type_value.upper(),
                    'quantity': self._format_quantity(symbol_formatted, float(order.quantity)),
                    'positionSide': position_side_value,
                    'clientOrderID': client_order_id,
                }

                if order.price:
                    if hasattr(order.price, 'amount'):
                        price_value = order.price.amount
                    else:
                        price_value = order.price
                    formatted_price = self._format_price(symbol_formatted, float(price_value))
                    main_order_data['price'] = formatted_price

                # Place the main market order
                endpoint = "/openApi/swap/v2/trade/order"
                response = self._make_request('POST', endpoint, data=main_order_data, signed=True)

                if response.get('code') == 0:
                    order_info = response.get('data', {}).get('order', {})
                    main_order_id = order_info.get('orderId')

                    # If main order was successful, now place separate conditional orders for SL/TP
                    conditional_errors = []

                    # Place stop loss order if needed
                    # For stop loss: if we're long (BUY), we want to SELL to close when price goes down
                    # For stop loss: if we're short (SELL), we want to BUY to close when price goes up
                    sl_side = 'SELL' if side_value.upper() == 'BUY' else 'BUY'
                    if side_value.upper() == 'BUY':
                        # For long positions, stop loss triggers when price goes BELOW the stop price
                        # So for a BUY order, we place a STOP_MARKET order to SELL when price drops
                        sl_order_type = 'STOP_MARKET'
                    else:
                        # For short positions, stop loss triggers when price goes ABOVE the stop price
                        # So for a SELL order, we place a STOP_MARKET order to BUY when price rises
                        sl_order_type = 'STOP_MARKET'

                    if has_stop_loss:
                        sl_response = self._place_conditional_order(
                            symbol=symbol_formatted,
                            side=sl_side,
                            quantity=self._format_quantity(symbol_formatted, float(order.quantity)),
                            stop_price=order_data.get('stopLossPrice'),
                            order_type=sl_order_type,
                            position_side=position_side_value
                        )

                        if not sl_response['success']:
                            conditional_errors.append(f"SL order failed: {sl_response['error']}")

                    # Place take profit order if needed
                    # For take profit: if we're long (BUY), we want to SELL to close when price goes up
                    # For take profit: if we're short (SELL), we want to BUY to close when price goes down
                    tp_side = 'SELL' if side_value.upper() == 'BUY' else 'BUY'
                    if side_value.upper() == 'BUY':
                        # For long positions, take profit triggers when price goes ABOVE the take profit price
                        # So for a BUY order, we place a TAKE_PROFIT_MARKET order to SELL when price rises
                        tp_order_type = 'TAKE_PROFIT_MARKET'
                    else:
                        # For short positions, take profit triggers when price goes BELOW the take profit price
                        # So for a SELL order, we place a TAKE_PROFIT_MARKET order to BUY when price drops
                        tp_order_type = 'TAKE_PROFIT_MARKET'

                    if has_take_profit:
                        tp_response = self._place_conditional_order(
                            symbol=symbol_formatted,
                            side=tp_side,
                            quantity=self._format_quantity(symbol_formatted, float(order.quantity)),
                            stop_price=order_data.get('takeProfitPrice'),
                            order_type=tp_order_type,
                            position_side=position_side_value
                        )

                        if not tp_response['success']:
                            conditional_errors.append(f"TP order failed: {tp_response['error']}")

                    # B1 GUARANTEED PROTECTION: a position must never remain open without its
                    # SL/TP. If any protective order failed, unwind the just-opened position;
                    # if the unwind also fails, halt all trading (kill switch) and flag the orphan.
                    if conditional_errors:
                        self.logger.error(
                            f"🛑 PROTECTION FAILED for {main_order_id} on {symbol_formatted}: "
                            f"{conditional_errors} — unwinding position (B1)")
                        unwound = self._unwind_position(
                            symbol_formatted, side_value.upper(),
                            self._format_quantity(symbol_formatted, float(order.quantity)), position_side_value)
                        if unwound:
                            try:
                                from infrastructure.strategies.strategy_manager import strategy_manager
                                strategy_manager.record_trade_result(symbol_formatted, is_profitable=False, position_closed=True, is_execution_unwind=True)
                                from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
                                symbol_cooldown_gate.record_stop_loss_exit(symbol_formatted)
                                self.logger.warning(f"🛑 Activated 60m Cooldown for {symbol_formatted} following protective unwind.")
                            except Exception as sm_err:
                                self.logger.warning(f"Could not forward B1 unwind to strategy_manager: {sm_err}")
                        else:
                            try:
                                from shared.live_execution_guard import live_execution_guard
                                live_execution_guard.engage_kill_switch(
                                    f"UNPROTECTED naked position {main_order_id} on "
                                    f"{symbol_formatted}: protective orders AND unwind both failed")
                            except Exception:
                                pass
                            self.logger.critical(
                                f"❌ NAKED POSITION {main_order_id} on {symbol_formatted}: unwind FAILED "
                                f"— trading HALTED, manual intervention required")
                        return {
                            'success': False,
                            'order_id': None,
                            'error': f'protective orders failed ({conditional_errors}); unwound={unwound}',
                            'protection_failed': True,
                            'unwound': unwound,
                            'orphaned_main_order_id': None if unwound else main_order_id,
                        }

                    # Both main order and protective orders succeeded.
                    print(f"\n🟢 [ORDER EXECUTED] Main order & SL/TP placed successfully: OrderID={main_order_id} Symbol={symbol_formatted} Side={side_value.upper()} Qty={order.quantity}", flush=True)
                    self.logger.warning(f"🟢 [ORDER EXECUTED] Main order & SL/TP placed successfully: OrderID={main_order_id} Symbol={symbol_formatted}")
                    return {
                        'success': True,
                        'order_id': main_order_id,
                        'response': response['data'],
                        'conditional_orders_errors': None,
                    }
                else:
                    return {
                        'success': False,
                        'error': response.get('msg', 'Unknown error from main order')
                    }
            else:
                # For orders without SL/TP or non-market orders with SL/TP, use the original approach
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

    def _format_symbol_str(self, symbol: str) -> str:
        """Ensure standard BingX perpetual contract symbol format with hyphen (e.g. BTC-USDT)."""
        s = str(symbol or "").upper().replace("/", "").replace("_", "").strip()
        if "-" in s:
            return s
        if s.endswith("USDT") and len(s) > 4:
            return f"{s[:-4]}-USDT"
        elif s.endswith("USDC") and len(s) > 4:
            return f"{s[:-4]}-USDC"
        return s

    def _unwind_position(self, symbol: str, original_side: str, quantity: str,
                         position_side: str) -> bool:
        """B1: flatten a just-opened position when its protective SL/TP could not be attached.

        Places a MARKET order in the opposite direction. Returns True if the
        exchange accepted the close. This is a protective unwind of an already-authorized
        entry, so it bypasses the guard (it only ever reduces risk).
        """
        try:
            formatted_sym = self._format_symbol_str(symbol)
            close_side = 'SELL' if original_side.upper() == 'BUY' else 'BUY'
            unwind_data = {
                'symbol': formatted_sym,
                'side': close_side,
                'type': 'MARKET',
                'quantity': quantity,
                'positionSide': position_side,
            }
            if position_side.upper() not in ('LONG', 'SHORT'):
                unwind_data['reduceOnly'] = 'true'
            resp = self._make_request('POST', '/openApi/swap/v2/trade/order',
                                      data=unwind_data, signed=True)
            if resp.get('code') == 0:
                self.logger.warning(
                    f"✅ UNWOUND unprotected position on {formatted_sym} ({close_side} {quantity})")
                return True
            self.logger.error(f"❌ UNWIND FAILED on {formatted_sym}: {resp.get('msg', resp)}")
            return False
        except Exception as e:
            self.logger.error(f"❌ UNWIND EXCEPTION on {symbol}: {e}")
            return False

    def _place_conditional_order(self, symbol: str, side: str, quantity: str, stop_price: str,
                               order_type: str, position_side: str) -> Dict[str, Any]:
        """Place a standard position-level conditional order (stop loss or take profit) using Swap V2 endpoint with closePosition=true."""
        try:
            formatted_sym = self._format_symbol_str(symbol)
            formatted_stop_price = self._format_price(formatted_sym, float(stop_price)) if stop_price is not None else stop_price
            formatted_qty = self._format_quantity(formatted_sym, float(quantity)) if quantity is not None else quantity
            conditional_order_data = {
                'symbol': formatted_sym,
                'side': side,
                'type': order_type,
                'quantity': formatted_qty,
                'stopPrice': formatted_stop_price,
                'positionSide': position_side,
                'closePosition': 'true',
                'workingType': 'MARK_PRICE'
            }

            endpoint = "/openApi/swap/v2/trade/order"
            response = self._make_request('POST', endpoint, params=conditional_order_data, signed=True)

            resp_code = response.get('code')
            resp_msg = str(response.get('msg', '')).lower()
            is_conflict = (
                resp_code in (110406, 110407, 110411, 100404, 100405, 80016)
                or any(phrase in resp_msg for phrase in ('already exists', 'conflict', 'position sl', 'position tp'))
            )

            if response.get('code') == 0:
                order_info = response.get('data', {}).get('order', {})
                return {
                    'success': True,
                    'order_id': order_info.get('orderId'),
                    'response': response['data']
                }
            elif is_conflict:
                # Position SL/TP conflict: cancel existing conditional order on this symbol and retry
                self.logger.warning(f"Position order conflict on {formatted_sym} ({response.get('msg')}), cancelling stale conditional orders and retrying...")
                open_orders = self.get_pending_orders(formatted_sym) or []
                prefix = "STOP" if "STOP" in order_type.upper() else "TAKE_PROFIT"
                for o in open_orders:
                    if prefix in str(o.get("type", "")).upper():
                        oid = str(o.get("orderId"))
                        if oid:
                            self.cancel_order(oid, formatted_sym)
                time.sleep(0.25)
                retry_resp = self._make_request('POST', endpoint, params=conditional_order_data, signed=True)
                if retry_resp.get('code') == 0:
                    order_info = retry_resp.get('data', {}).get('order', {})
                    return {
                        'success': True,
                        'order_id': order_info.get('orderId'),
                        'response': retry_resp['data']
                    }
                elif retry_resp.get('code') in (110406, 110407, 110411, 100404, 100405, 80016) or 'already exists' in str(retry_resp.get('msg', '')).lower():
                    # Second retry with longer propagation cushion
                    time.sleep(0.40)
                    retry2_resp = self._make_request('POST', endpoint, params=conditional_order_data, signed=True)
                    if retry2_resp.get('code') == 0:
                        order_info = retry2_resp.get('data', {}).get('order', {})
                        return {
                            'success': True,
                            'order_id': order_info.get('orderId'),
                            'response': retry2_resp['data']
                        }
                    else:
                        return {'success': False, 'error': retry2_resp.get('msg', str(retry2_resp))}
                else:
                    return {'success': False, 'error': retry_resp.get('msg', str(retry_resp))}
            else:
                error_msg = response.get('msg', str(response))
                self.logger.error(f"BingX Swap V2 conditional order failed on {formatted_sym}: {error_msg}")
                return {'success': False, 'error': error_msg}
        except Exception as e:
            self.logger.error(f"Failed to place conditional order on BingX Swap V2 for {symbol}: {e}")
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
            formatted_sym = self._format_symbol_str(symbol)
            params = {
                'symbol': formatted_sym,
                'orderId': order_id
            }

            response = self._make_request('DELETE', '/openApi/swap/v2/trade/order', params=params, signed=True)
            return response.get('code') == 0

        except Exception as e:
            self.logger.error(f"Failed to cancel order: {str(e)}")
            return False

    def get_order_status(self, order_id: str, symbol: str) -> str:
        formatted_sym = self._format_symbol_str(symbol)
        pending_orders = self.get_pending_orders(formatted_sym)
        for order in pending_orders:
            if str(order.get('orderId')) == str(order_id):
                return order.get('status')

        history = self.get_order_history(formatted_sym, limit=100)
        for order in history:
            if str(order.get('orderId')) == str(order_id):
                return order.get('status')

        return "UNKNOWN"

    def get_order_fill(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """B7: return the order's {status, executed_qty, avg_price} from open orders + history."""
        formatted_sym = self._format_symbol_str(symbol)
        for order in list(self.get_pending_orders(formatted_sym)) + list(self.get_order_history(formatted_sym, limit=100)):
            if str(order.get('orderId')) == str(order_id):
                return {
                    "status": order.get('status', 'UNKNOWN'),
                    "executed_qty": order.get('executedQty', order.get('cumQty', 0)) or 0,
                    "avg_price": order.get('avgPrice', order.get('avgFillPrice')),
                }
        return {"status": "UNKNOWN", "executed_qty": 0, "avg_price": None}

    def get_pending_orders(self, symbol: str = None) -> List[Dict]:
        """Get all pending orders."""
        try:
            params = {}
            if symbol:
                params['symbol'] = self._format_symbol_str(symbol)

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
                params['symbol'] = self._format_symbol_str(symbol)
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
            # Try the correct BingX API endpoint for getting all trading pairs
            # According to BingX API documentation, the exchangeInfo endpoint is the most reliable
            response = self._make_request('GET', '/openApi/spot/v1/public/exchangeInfo', signed=False)

            if response.get('code') == 0:
                symbols = set()
                data = response.get('data', {})

                # Check if the response has a 'symbols' field (common format for exchange info)
                if 'symbols' in data:
                    for symbol_info in data['symbols']:
                        if isinstance(symbol_info, dict):
                            # Check if the symbol is currently trading
                            status = symbol_info.get('status', '').upper()
                            if status in ['TRADING', 'ENABLED', 'ACTIVE']:
                                symbol = symbol_info.get('symbol', '')
                                if symbol:
                                    # Convert from BingX format (e.g., BTC-USDT) to our format (BTCUSDT)
                                    formatted_symbol = symbol.replace('-', '')
                                    symbols.add(formatted_symbol)

                # If we found symbols using exchangeInfo, return them
                if symbols:
                    self.logger.debug(f"Retrieved {len(symbols)} symbols from exchangeInfo endpoint")
                    return symbols

            # If the exchangeInfo endpoint didn't work, try the ticker/24hr endpoint for all symbols
            try:
                ticker_response = self._make_request('GET', '/openApi/spot/v1/market/ticker/24hr', signed=False)

                if ticker_response.get('code') == 0:
                    symbols = set()
                    data = ticker_response.get('data', [])

                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'symbol' in item:
                                symbol = item['symbol']
                                # Convert from BingX format (e.g., BTC-USDT) to our format (BTCUSDT)
                                formatted_symbol = symbol.replace('-', '')
                                symbols.add(formatted_symbol)

                    if symbols:
                        self.logger.debug(f"Retrieved {len(symbols)} symbols from ticker/24hr endpoint")
                        return symbols
            except Exception as ticker_error:
                self.logger.debug(f"Ticker endpoint failed: {ticker_error}")

            # If that doesn't work, try the ticker/price endpoint for all symbols
            try:
                price_response = self._make_request('GET', '/openApi/spot/v1/market/ticker/price', signed=False)

                if price_response.get('code') == 0:
                    symbols = set()
                    data = price_response.get('data', [])

                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'symbol' in item:
                                symbol = item['symbol']
                                # Convert from BingX format (e.g., BTC-USDT) to our format (BTCUSDT)
                                formatted_symbol = symbol.replace('-', '')
                                symbols.add(formatted_symbol)

                    if symbols:
                        self.logger.debug(f"Retrieved {len(symbols)} symbols from ticker/price endpoint")
                        return symbols
            except Exception as price_error:
                self.logger.debug(f"Price ticker endpoint failed: {price_error}")

        except Exception as e:
            self.logger.error(f"Error getting available symbols from BingX: {e}")
            # If API call fails, return empty set but log the error
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return set()

        # If all API methods fail, return the approved symbols as a fallback
        # since we know these should be available on BingX
        try:
            from infrastructure.services.symbol_validator import symbol_validator
            if hasattr(symbol_validator, 'get_approved_symbols'):
                approved_symbols = symbol_validator.get_approved_symbols()
                self.logger.debug(f"Using {len(approved_symbols)} approved symbols as fallback")
                return approved_symbols
        except ImportError:
            # If we can't import the symbol validator, return empty set
            self.logger.warning("Could not import symbol validator, using empty set as fallback")
            pass
        except Exception as e:
            self.logger.warning(f"Could not get approved symbols from validator: {e}")

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

    def get_positions(self, symbol: str=None) -> List[Dict]:
        """Alias for get_open_positions."""
        return self.get_open_positions(symbol)

    def get_all_positions(self) -> List[Dict]:
        """Alias for get_open_positions."""
        return self.get_open_positions()
