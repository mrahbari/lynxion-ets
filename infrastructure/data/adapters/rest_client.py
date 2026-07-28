import requests
import time
import hashlib
import hmac
from typing import Dict, Any, Optional
from shared.logger import logger
import json


class RestClient:
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://api.binance.com"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': api_key
        })
        
        # Rate limiting
        self.request_times = []
        self.max_requests_per_minute = 1200  # Binance limit
        
    def _rate_limit(self):
        """Implement rate limiting to avoid API limits"""
        now = time.time()
        # Remove requests older than 60 seconds
        self.request_times = [req_time for req_time in self.request_times if now - req_time < 60]
        
        if len(self.request_times) >= self.max_requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                
        self.request_times.append(now)
        
    def _sign_request(self, params: Dict[str, Any]) -> str:
        """Sign request with HMAC"""
        query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
        
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = False) -> Optional[Dict]:
        """Make an API request with transient fault retries"""
        self._rate_limit()
        url = f"{self.base_url}{endpoint}"

        def send_api_call():
            # Update signature/timestamp on each attempt
            local_params = dict(params) if params is not None else {}
            if signed:
                local_params['timestamp'] = int(time.time() * 1000)
                signature = self._sign_request(local_params)
                local_params['signature'] = signature

            if method.upper() == 'GET':
                response = self.session.get(url, params=local_params)
            elif method.upper() == 'POST':
                response = self.session.post(url, params=local_params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=local_params)
            else:
                raise ValueError(f"Unsupported method: {method}")

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

        try:
            from shared.retry import retry_with_backoff
            return retry_with_backoff(
                send_api_call,
                max_attempts=3,
                base_delay=0.5,
                retry_on=(requests.exceptions.RequestException,),
                should_retry=should_retry_request,
                on_retry=lambda attempt, exc, delay: logger.warning(
                    f"⚠️ Binance API {method} {endpoint} failed (attempt {attempt}): {exc}; retrying in {delay:.2f}s..."
                )
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
            
    def get_server_time(self) -> Optional[int]:
        """Get server time"""
        endpoint = "/api/v3/time"
        result = self._make_request('GET', endpoint)
        if result:
            return result.get('serverTime')
        return None
        
    def get_exchange_info(self) -> Optional[Dict]:
        """Get exchange information"""
        endpoint = "/api/v3/exchangeInfo"
        return self._make_request('GET', endpoint)
        
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get specific symbol information"""
        endpoint = "/api/v3/exchangeInfo"
        params = {"symbol": symbol.upper()}
        result = self._make_request('GET', endpoint, params)
        
        if result and 'symbols' in result:
            for sym in result['symbols']:
                if sym['symbol'] == symbol.upper():
                    return sym
        return None
        
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> Optional[list]:
        """Get kline/candlestick data"""
        endpoint = "/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }
        return self._make_request('GET', endpoint, params)
        
    def get_ticker_price(self, symbol: str = None) -> Optional[Dict]:
        """Get current ticker price"""
        endpoint = "/api/v3/ticker/price"
        params = {"symbol": symbol.upper()} if symbol else None
        return self._make_request('GET', endpoint, params)
        
    def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict]:
        """Get order book"""
        endpoint = "/api/v3/depth"
        params = {
            "symbol": symbol.upper(),
            "limit": min(limit, 5000)
        }
        return self._make_request('GET', endpoint, params)
        
    def place_order(
        self, 
        symbol: str, 
        side: str, 
        order_type: str, 
        quantity: float, 
        price: Optional[float] = None,
        time_in_force: str = "GTC",
        stop_price: Optional[float] = None
    ) -> Optional[Dict]:
        """Place an order (requires signed request)"""
        endpoint = "/api/v3/order"
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity
        }
        
        if order_type.upper() in ["LIMIT", "STOP_LOSS_LIMIT", "TAKE_PROFIT_LIMIT"]:
            params["price"] = price
            params["timeInForce"] = time_in_force
            
        if stop_price and order_type.upper() in ["STOP_LOSS", "STOP_LOSS_LIMIT", "TAKE_PROFIT", "TAKE_PROFIT_LIMIT"]:
            params["stopPrice"] = stop_price
            
        return self._make_request('POST', endpoint, params, signed=True)
        
    def get_open_orders(self, symbol: str = None) -> Optional[list]:
        """Get open orders (requires signed request)"""
        endpoint = "/api/v3/openOrders"
        params = {"symbol": symbol.upper()} if symbol else {}
        return self._make_request('GET', endpoint, params, signed=True)
        
    def cancel_order(self, symbol: str, order_id: int) -> Optional[Dict]:
        """Cancel an order (requires signed request)"""
        endpoint = "/api/v3/order"
        params = {
            "symbol": symbol.upper(),
            "orderId": order_id
        }
        return self._make_request('DELETE', endpoint, params, signed=True)
        
    def get_account_info(self) -> Optional[Dict]:
        """Get account information (requires signed request)"""
        endpoint = "/api/v3/account"
        return self._make_request('GET', endpoint, {}, signed=True)
        
    def get_balance(self, asset: str = None) -> Optional[Dict]:
        """Get specific asset balance"""
        account_info = self.get_account_info()
        if not account_info or 'balances' not in account_info:
            return None
            
        balances = {}
        for balance in account_info['balances']:
            balances[balance['asset']] = {
                'free': float(balance['free']),
                'locked': float(balance['locked']),
                'total': float(balance['free']) + float(balance['locked'])
            }
            
        if asset:
            return balances.get(asset.upper())
        return balances