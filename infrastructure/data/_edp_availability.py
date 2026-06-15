"""E5.T5 (infra-only mechanical split): symbol-availability helpers extracted from
``EnhancedDataProviderAdapter``.

Behavior-preserving mixin — _refresh_available_symbols_cache, _get_broker_type,
_check_single_symbol, _check_symbol_via_multiple_exchanges, _format_symbol_for_exchange
moved verbatim (signatures, ``self`` semantics, results UNCHANGED) and composed via
inheritance. Conservative top-level imports. No layer move, no logic change.
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


class _EdpAvailabilityMixin:
    """Symbol-availability + exchange-check helpers."""

    def _refresh_available_symbols_cache(self):
        """Refresh the cache of available symbols."""
        try:
            # Get the broker from the broker service and call its get_available_symbols method
            if self.broker_service:
                # Log the type of broker service for debugging
                broker_service_type = self._get_broker_type(self.broker_service)
                self.logger.debug(f"Refreshing symbol cache - Broker service type: {broker_service_type}")

                # Check if the broker service itself has get_available_symbols method (like BrokerExecutionService)
                if hasattr(self.broker_service, 'get_available_symbols'):
                    self.logger.debug(f"Calling get_available_symbols on broker service {broker_service_type}")
                    available_symbols = self.broker_service.get_available_symbols()
                    self._available_symbols_cache = available_symbols
                    self._cache_timestamp = time.time()

                    self.logger.debug(f"Refreshed symbol availability cache with {len(available_symbols)} symbols from broker service")
                    return
                # Check if it's a BrokerExecutionService and try to access its internal broker
                elif hasattr(self.broker_service, 'broker'):
                    # Access the internal broker directly
                    broker = self.broker_service.broker
                    broker_type = self._get_broker_type(broker)
                    self.logger.debug(f"Accessed internal broker: {broker_type}")
                elif hasattr(self.broker_service, 'get_broker_by_name'):
                    # Get the default broker from environment or use 'bingx' as default
                    default_broker = self._default_broker
                    broker = self.broker_service.get_broker_by_name(default_broker)
                    broker_type = self._get_broker_type(broker)
                    self.logger.debug(f"Got broker by name '{default_broker}': {broker_type}")
                elif hasattr(self.broker_service, 'get_broker'):
                    # If it's a broker manager, get the default broker
                    broker = self.broker_service.get_broker('spot')  # Use 'spot' as default instrument type
                    broker_type = self._get_broker_type(broker)
                    self.logger.debug(f"Got broker by instrument type 'spot': {broker_type}")
                else:
                    # If it's already a broker instance
                    broker = self.broker_service
                    broker_type = self._get_broker_type(broker)
                    self.logger.debug(f"Using broker service as broker instance: {broker_type}")

                if broker and hasattr(broker, 'get_available_symbols'):
                    broker_type = self._get_broker_type(broker)
                    self.logger.debug(f"Calling get_available_symbols on broker {broker_type}")
                    available_symbols = broker.get_available_symbols()
                    self._available_symbols_cache = available_symbols
                    self._cache_timestamp = time.time()

                    self.logger.debug(f"Refreshed symbol availability cache with {len(available_symbols)} symbols from broker")
                    return
                else:
                    broker_type = self._get_broker_type(broker)
                    self.logger.warning(f"Broker does not support get_available_symbols method. Broker type: {broker_type}")
                    # Log what methods the broker actually has
                    if broker:
                        methods = [method for method in dir(broker) if not method.startswith('_')]
                        self.logger.debug(f"Available methods on broker: {methods}")
            else:
                self.logger.warning("No broker service provided for symbol availability check")

        except Exception as e:
            self.logger.error(f"Error refreshing symbol availability cache: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # If we can't refresh the cache, keep the old one or try alternative method
            pass

    def _get_broker_type(self, broker_obj) -> str:
        """Helper method to get broker type name safely."""
        return type(broker_obj).__name__ if broker_obj else "None"

    def _check_single_symbol(self, symbol: str) -> bool:
        """Check a single symbol availability using direct API call with exchange switching."""

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available
        from infrastructure.services.symbol_validator import symbol_validator
        from domain.value_objects import Symbol as DomainSymbol

        # Create a domain symbol object for validation
        domain_symbol = DomainSymbol(symbol)
        if not symbol_validator.is_symbol_approved(domain_symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol} is not in approved symbols list. Not available for trading.")

            # Cache this negative result
            cache_key = f"symbol_check_{symbol}"
            current_time = datetime.now()
            with self._cache_lock:
                self._symbol_availability_cache[cache_key] = (current_time, False)

            return False

        # Check if we have a recent result for this symbol in our cache
        cache_key = f"symbol_check_{symbol}"
        current_time = datetime.now()
        with self._cache_lock:
            if cache_key in self._symbol_availability_cache:
                timestamp, result = self._symbol_availability_cache[cache_key]
                if current_time - timestamp < self._cache_timeout:
                    self.logger.debug(f"Symbol {symbol} availability found in cache: {result}")
                    return result

        # First check if the symbol is in the cached available symbols
        if symbol in self._available_symbols_cache:
            self.logger.debug(f"Symbol {symbol} found in cache")

            # Cache this positive result
            with self._cache_lock:
                self._symbol_availability_cache[cache_key] = (current_time, True)

            return True

        # If not in cache, check if broker service is available to check symbol
        if self.broker_service:
            # Check if this is a MultiBrokerExecutionService that supports exchange switching
            if hasattr(self.broker_service, 'is_symbol_available'):
                try:
                    return self.broker_service.is_symbol_available(symbol)
                except Exception as e:
                    self.logger.debug(f"MultiBroker service failed for symbol {symbol}, falling back: {e}")

            # Log broker service type for debugging
            broker_service_type = self._get_broker_type(self.broker_service)
            self.logger.debug(f"Checking symbol {symbol} using broker service: {broker_service_type}")

            try:
                # Check if the broker service itself has get_available_symbols method (like BrokerExecutionService)
                if hasattr(self.broker_service, 'get_available_symbols'):
                    self.logger.debug(f"Broker service {broker_service_type} has get_available_symbols method")
                    available_symbols = self.broker_service.get_available_symbols()
                    self.logger.debug(f"Got {len(available_symbols)} available symbols from broker service, checking for {symbol}")
                    if symbol in available_symbols:
                        self.logger.debug(f"Symbol {symbol} found in broker service available symbols")
                        return True
                    else:
                        # If symbol not found in broker service, continue to fallback
                        self.logger.debug(f"Symbol {symbol} not found in broker service available symbols")
                else:
                    # If broker service doesn't have the method, try to access internal broker
                    broker = None
                    if hasattr(self.broker_service, 'broker'):
                        # Access the internal broker directly
                        broker = self.broker_service.broker
                        broker_type = self._get_broker_type(broker)
                        self.logger.debug(f"Accessing internal broker: {broker_type}")
                    elif hasattr(self.broker_service, 'get_broker_by_name'):
                        default_broker = self._default_broker
                        broker = self.broker_service.get_broker_by_name(default_broker)
                        broker_type = self._get_broker_type(broker)
                        self.logger.debug(f"Got broker by name '{default_broker}': {broker_type}")
                    elif hasattr(self.broker_service, 'get_broker'):
                        broker = self.broker_service.get_broker('spot')
                        broker_type = self._get_broker_type(broker)
                        self.logger.debug(f"Got broker by instrument type 'spot': {broker_type}")
                    else:
                        broker = self.broker_service
                        broker_type = self._get_broker_type(broker)
                        self.logger.debug(f"Using broker service as broker instance: {broker_type}")

                    if broker and hasattr(broker, 'get_available_symbols'):
                        # Get fresh symbols from broker and check
                        available_symbols = broker.get_available_symbols()
                        broker_type = self._get_broker_type(broker)
                        self.logger.debug(f"Got {len(available_symbols)} available symbols from broker {broker_type}, checking for {symbol}")
                        if symbol in available_symbols:
                            self.logger.debug(f"Symbol {symbol} found in broker available symbols")
                            return True
                    else:
                        # Log which broker type doesn't support the method
                        broker_type = self._get_broker_type(broker)
                        self.logger.warning(f"Broker {broker_type} does not support get_available_symbols method for symbol {symbol}")
            except Exception as e:
                self.logger.error(f"Could not check symbol availability via broker service: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")

        # Fallback to direct API call with exchange switching
        result = self._check_symbol_via_multiple_exchanges(symbol)

        # Cache the result
        current_time = datetime.now()
        with self._cache_lock:
            self._symbol_availability_cache[cache_key] = (current_time, result)

        return result

    def _check_symbol_via_multiple_exchanges(self, symbol: str) -> bool:
        """Check symbol availability across multiple exchanges with fallback."""

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available
        from infrastructure.services.symbol_validator import symbol_validator
        from domain.value_objects import Symbol as DomainSymbol

        # Create a domain symbol object for validation
        domain_symbol = DomainSymbol(symbol)
        if not symbol_validator.is_symbol_approved(domain_symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol} is not in approved symbols list. Not available for trading.")
            return False

        import requests

        # Define exchange order for checking
        exchange_configs = [
            {
                'name': 'binance',
                'url': f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
                'success_check': lambda resp: resp.status_code == 200
            },
            {
                'name': 'bingx',
                'url': f"https://open-api.bingx.com/openApi/quote/v1/ticker/price?symbol={symbol}",
                'success_check': lambda resp: resp.status_code == 200 and 'data' in resp.json()
            },
            {
                'name': 'mexc',
                'url': f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}",
                'success_check': lambda resp: resp.status_code == 200
            },
            {
                'name': 'phemex',
                'url': f"https://api.phemex.com/md/ticker/24hr?symbol={symbol}",
                'success_check': lambda resp: resp.status_code == 200
            }
        ]

        for config in exchange_configs:
            try:
                self.logger.debug(f"Trying {config['name']} API for symbol {symbol}")
                # Use session with proper connection management
                with requests.Session() as session:
                    response = session.get(config['url'], timeout=5)

                if config['success_check'](response):
                    self.logger.debug(f"Symbol {symbol} found on {config['name']}")
                    return True
            except Exception as e:
                self.logger.debug(f"Failed to check {symbol} on {config['name']}: {e}")
                continue

        self.logger.debug(f"Symbol {symbol} not found on any exchange")
        return False

    def _format_symbol_for_exchange(self, symbol: str) -> str:
        """Format symbol for exchange API (e.g., BTCUSDT -> BTC/USDT)."""
        if '/' in symbol:
            return symbol  # Already in correct format
        elif 'USDT' in symbol:
            base = symbol.replace('USDT', '')
            return f"{base}/USDT"
        elif 'BUSD' in symbol:
            base = symbol.replace('BUSD', '')
            return f"{base}/BUSD"
        elif 'USDC' in symbol:
            base = symbol.replace('USDC', '')
            return f"{base}/USDC"
        else:
            # For other quote currencies or unknown format
            # Try to identify common quote currencies
            for quote in ['USD', 'EUR', 'GBP', 'JPY', 'BTC', 'ETH']:
                if symbol.endswith(quote):
                    base = symbol[:-len(quote)]
                    return f"{base}/{quote}"
            # If no known quote currency found, assume it's base/USDT format
            return f"{symbol}/USDT"
