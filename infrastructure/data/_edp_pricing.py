"""E5.T5 (infra-only mechanical split): price-estimation/fetch helpers extracted from
``EnhancedDataProviderAdapter``.

Behavior-preserving mixin — _estimate_base_price_intelligently,
_calculate_price_by_market_category, _get_real_price_from_exchange moved verbatim
(signatures, ``self`` semantics, returned prices UNCHANGED) and composed via inheritance.
Imports are the module's original top-level block (conservative; some unused here) to
guarantee name resolution. No layer move, no Money/Symbol-semantics change, no logic change.
"""
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from domain.ports.data_ports import DataProviderPort
from domain.entities import MarketData
from domain.value_objects import Symbol
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
from infrastructure.data_sync.data_downloader_adapter import DataDownloaderAdapter
from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
from application.data_sync.sync_manager import SyncManager
from shared.logger import EnhancedLogger
from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService
from infrastructure.data.improved_data_cache import improved_data_cache as data_cache
from infrastructure.data.configurable_historical_data_provider import ConfigurableHistoricalDataProvider


class _EdpPricingMixin:
    """Price estimation + exchange price fetch helpers."""

    def _estimate_base_price_intelligently(self, symbol: str) -> float:
        """
        Estimate a reasonable base price by fetching real market data from exchange.
        This method connects to a real exchange API to get current prices instead of using hardcoded values.
        """
        # Try to get real price from exchange first
        real_price = self._get_real_price_from_exchange(symbol)
        if real_price is not None and real_price > 0:
            return real_price

        # If real data is not available, fall back to a more intelligent approach
        # that doesn't use hardcoded ranges
        return self._calculate_price_by_market_category(symbol)

    def _calculate_price_by_market_category(self, symbol: str) -> float:
        """Calculate price based on market category by fetching from exchange or using intelligent estimation."""
        # Try to get real price from exchange first
        real_price = self._get_real_price_from_exchange(symbol)
        if real_price is not None and real_price > 0:
            return real_price

        # If exchange data is not available, use a more intelligent approach
        # that doesn't rely on hardcoded coin lists
        base_currency = symbol
        if 'USDT' in symbol or 'BUSD' in symbol or 'USDC' in symbol:
            # Standard format like BTCUSDT, ETHUSDT, etc.
            quote_part = 'USDT' if 'USDT' in symbol else 'BUSD' if 'BUSD' in symbol else 'USDC'
            base_currency = symbol.replace(quote_part, '')

        # Use market cap ranking estimation instead of hardcoded lists
        # This is a more scalable approach that doesn't require maintaining coin lists
        base_hash = abs(hash(base_currency.upper())) % 100000
        # Use the hash to create a reasonable price range based on market patterns
        # rather than hardcoded coin categories
        if len(base_currency) <= 3:
            # Likely major coin - higher price range
            return max(0.01, (base_hash % 50000) / 1000.0)  # $0.01 to $50
        else:
            # Likely smaller coin - lower price range
            return max(0.0001, (base_hash % 10000) / 10000.0)  # $0.0001 to $1

    def _get_real_price_from_exchange(self, symbol: str) -> Optional[float]:
        """Fetch real price from exchange API with caching."""
        # Try to get price from cache first (use a short TTL for prices)
        broker_name = self._get_broker_name()
        cache_key = f"{broker_name}_price_{symbol}"
        cached_price = data_cache.get(broker_name, f"price_{symbol}", "tick")  # Use "tick" as timeframe for prices
        if cached_price and len(cached_price) > 0:
            price = cached_price[0].get('price')
            self.logger.debug(f"Using cached price {price} for {symbol} from {broker_name}")
            return price

        # Try to get price via broker service if available
        if self.broker_service:
            broker = None  # Initialize broker variable to avoid UnboundLocalError
            try:
                broker_service_type = self._get_broker_type(self.broker_service)
                self.logger.debug(f"Fetching price for {symbol} using broker service: {broker_service_type}")

                # Check if the broker service itself has get_available_symbols method (like BrokerExecutionService)
                if hasattr(self.broker_service, 'get_available_symbols'):
                    self.logger.debug(f"Checking symbol {symbol} availability via broker service {broker_service_type}")
                    available_symbols = self.broker_service.get_available_symbols()
                    if symbol not in available_symbols:
                        self.logger.debug(f"Symbol {symbol} not available on broker service")
                        return None
                    else:
                        self.logger.debug(f"Symbol {symbol} found in broker service available symbols")
                    broker = self.broker_service  # Set broker for later use
                # Check if it's a BrokerExecutionService and try to access its internal broker
                elif hasattr(self.broker_service, 'broker'):
                    # Access the internal broker directly
                    broker = self.broker_service.broker
                    broker_type = self._get_broker_type(broker)
                    self.logger.debug(f"Accessing internal broker {broker_type} for symbol {symbol}")
                elif hasattr(self.broker_service, 'get_broker_by_name'):
                    default_broker = self._default_broker
                    broker = self.broker_service.get_broker_by_name(default_broker)
                    broker_type = self._get_broker_type(broker)
                    self.logger.debug(f"Got broker {broker_type} by name '{default_broker}' for symbol {symbol}")
                elif hasattr(self.broker_service, 'get_broker'):
                    broker = self.broker_service.get_broker('spot')
                    broker_type = self._get_broker_type(broker)
                    self.logger.debug(f"Got broker {broker_type} by instrument type 'spot' for symbol {symbol}")
                else:
                    broker = self.broker_service
                    broker_type = self._get_broker_type(broker)
                    self.logger.debug(f"Using broker service {broker_type} as broker instance for symbol {symbol}")

                if broker:
                    # Try to get ticker data directly from broker
                    # This assumes the broker has a method to get ticker data
                    # For now, we'll try to use the broker's available symbols to verify the symbol exists
                    if hasattr(broker, 'get_available_symbols'):
                        broker_type = self._get_broker_type(broker)
                        self.logger.debug(f"Checking symbol {symbol} availability via broker {broker_type}")
                        available_symbols = broker.get_available_symbols()
                        if symbol not in available_symbols:
                            self.logger.debug(f"Symbol {symbol} not available on broker")
                            return None
                        else:
                            self.logger.debug(f"Symbol {symbol} found in broker available symbols")
                    # If symbol is available, we could potentially get price data from broker
                    # For now, we'll continue with the direct API approach for price fetching
            except Exception as e:
                self.logger.error(f"Could not fetch price via broker service: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")

        # Try alternative method using requests with exponential backoff
        try:
            import requests
            import time
            import random

            # Use a generic approach - try Binance API as fallback with exponential backoff
            api_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"

            # Exponential backoff parameters
            max_retries = 3
            base_delay = 1  # Start with 1 second

            for attempt in range(max_retries):
                try:
                    self.logger.debug(f"Attempt {attempt + 1}/{max_retries} - Using fallback API call for price of {symbol}: {api_url}")
                    # Use session with proper connection management
                    with requests.Session() as session:
                        response = session.get(api_url, timeout=10)  # Increased timeout

                    if response.status_code == 200:
                        data = response.json()
                        if 'price' in data:
                            price = float(data['price'])
                            self.logger.debug(f"Successfully fetched price {price} for {symbol} from direct API")

                            # Cache the price with a short TTL (30 seconds for price data)
                            data_cache.set(broker_name, f"price_{symbol}", "tick", [{'price': price}], ttl=30)
                            return price
                    elif response.status_code == 400:
                        # Symbol not found on exchange - don't retry
                        self.logger.debug(f"Symbol {symbol} not found on exchange: {response.text}")
                        return None
                    elif response.status_code in [429, 502, 503, 504]:  # Rate limiting or server errors
                        if attempt < max_retries - 1:  # Don't sleep on the last attempt
                            # Calculate delay with exponential backoff and jitter
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            self.logger.warning(f"API call failed with status {response.status_code}, retrying in {delay:.2f}s (attempt {attempt + 1})")
                            time.sleep(delay)
                        else:
                            self.logger.warning(f"API call failed after {max_retries} attempts with status {response.status_code}")
                    else:
                        # Other HTTP errors - don't retry
                        self.logger.debug(f"API call failed with status {response.status_code}: {response.text}")
                        return None

                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        self.logger.warning(f"API call timed out, retrying in {delay:.2f}s (attempt {attempt + 1})")
                        time.sleep(delay)
                    else:
                        self.logger.warning(f"API call timed out after {max_retries} attempts")
                except requests.exceptions.ConnectionError:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        self.logger.warning(f"Connection error, retrying in {delay:.2f}s (attempt {attempt + 1})")
                        time.sleep(delay)
                    else:
                        self.logger.warning(f"Connection error after {max_retries} attempts")
                except Exception as api_error:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        self.logger.warning(f"API error: {api_error}, retrying in {delay:.2f}s (attempt {attempt + 1})")
                        time.sleep(delay)
                    else:
                        self.logger.warning(f"API error after {max_retries} attempts: {api_error}")
                        break

        except Exception as e:
            self.logger.debug(f"Could not fetch real price for {symbol} from direct API: {e}")
            pass

        return None
