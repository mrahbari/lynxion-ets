"""
Configurable Historical Data Provider that can use different brokers to avoid rate limits.
This provider allows selecting different data sources for historical data requests.
"""
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import requests
import pandas as pd

from domain.ports.data_ports import DataProviderPort
from domain.entities import MarketData
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from infrastructure.brokers.broker_adapters import (
    BingXBrokerAdapter, BinanceBrokerAdapter, MEXCBrokerAdapter, PhemexBrokerAdapter
)
from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService


class ConfigurableHistoricalDataProvider(DataProviderPort):
    """
    A configurable historical data provider that can use different brokers to fetch historical data.
    This helps avoid rate limits by distributing requests across multiple data sources.
    """
    
    def __init__(self, settings, preferred_data_source: str = None, fallback_sources: List[str] = None):
        """
        Initialize the configurable historical data provider.

        Args:
            settings: Injected settings object (E1.T4 — supplied by the composition root;
                this adapter no longer imports bootstrap.settings.loaders).
            preferred_data_source: Primary data source ('bingx', 'binance', 'mexc', 'phemex', 'multi')
            fallback_sources: List of fallback data sources in order of preference
        """
        self._settings = settings
        self.logger = EnhancedLogger("ConfigurableHistoricalDataProvider")

        # Determine preferred data source
        if preferred_data_source is None:
            # Default to binance for historical data to avoid BingX rate limits
            preferred_data_source = self._settings.data.preferred_historical_data_source if self._settings.data and hasattr(self._settings.data, 'preferred_historical_data_source') else 'binance'

        # Set default fallbacks if not provided
        if fallback_sources is None:
            fallback_sources = (self._settings.data.historical_data_fallback_sources if self._settings.data and self._settings.data.historical_data_fallback_sources else 'binance,mexc,phemex').split(',')

        self.preferred_data_source = preferred_data_source.lower()
        self.fallback_sources = [source.strip().lower() for source in fallback_sources]

        # Initialize broker adapters
        self.brokers = {}
        self._initialize_brokers()

        # Track usage statistics to help with load balancing
        self.usage_stats = {source: {'requests': 0, 'errors': 0} for source in ['bingx', 'binance', 'mexc', 'phemex']}

        # Cache of (source, symbol) -> timestamp for invalid/unsupported symbols per exchange (24-hour TTL)
        self.unsupported_exchange_symbols = {}  # (source, symbol) -> float timestamp
        self.unsupported_exchange_ttl = 86400  # 24 hours in seconds

        self.logger.info(f"Configurable Historical Data Provider initialized with preferred source: {self.preferred_data_source}")
        self.logger.info(f"Fallback sources: {self.fallback_sources}")

    def _initialize_brokers(self):
        """Initialize broker adapters for historical data retrieval."""
        # Initialize Binance (usually has good historical data availability)
        # NOTE: For historical data fetching, we can use public endpoints without API keys
        try:
            # Check if API keys are provided, but still initialize the adapter as it can use public endpoints
            api_key = self._settings.broker.binance_api_key if self._settings.broker and hasattr(self._settings.broker, 'binance_api_key') else None
            secret_key = self._settings.broker.binance_secret_key if self._settings.broker and hasattr(self._settings.broker, 'binance_secret_key') else None

            # Initialize Binance adapter even without API keys for public endpoint access
            self.brokers['binance'] = BinanceBrokerAdapter(
                api_key=api_key or '',  # Pass empty string if no key
                secret_key=secret_key or ''  # Pass empty string if no key
            )
            self.logger.info("✅ Binance broker initialized for historical data (public endpoints available)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize Binance broker for historical data: {e}")

        # Initialize BingX
        # NOTE: For historical data fetching, we can use public endpoints without API keys
        try:
            # Initialize BingX adapter even without API keys for public endpoint access
            bingx_config = {
                'api_key': self._settings.broker.bingx_api_key if self._settings.broker and hasattr(self._settings.broker, 'bingx_api_key') else '',
                'secret_key': self._settings.broker.bingx_secret_key if self._settings.broker and hasattr(self._settings.broker, 'bingx_secret_key') else '',
                'passphrase': self._settings.broker.bingx_passphrase if self._settings.broker and hasattr(self._settings.broker, 'bingx_passphrase') else '',
                'testnet': self._settings.broker.bingx_testnet if self._settings.broker and hasattr(self._settings.broker, 'bingx_testnet') else True
            }

            self.brokers['bingx'] = BingXBrokerAdapter(bingx_config)
            self.logger.info("✅ BingX broker initialized for historical data (public endpoints available)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize BingX broker for historical data: {e}")

        # Initialize MEXC
        # NOTE: For historical data fetching, we can use public endpoints without API keys
        try:
            # Initialize MEXC adapter even without API keys for public endpoint access
            api_key = self._settings.broker.mexc_api_key if self._settings.broker and hasattr(self._settings.broker, 'mexc_api_key') else None
            secret_key = self._settings.broker.mexc_secret_key if self._settings.broker and hasattr(self._settings.broker, 'mexc_secret_key') else None
            testnet = self._settings.broker.mexc_testnet if self._settings.broker and hasattr(self._settings.broker, 'mexc_testnet') else True

            base_url = "https://api-testnet.mexc.com" if testnet else "https://api.mexc.com"
            self.brokers['mexc'] = MEXCBrokerAdapter(
                api_key=api_key or '',  # Pass empty string if no key
                secret_key=secret_key or '',  # Pass empty string if no key
                base_url=base_url
            )
            self.logger.info("✅ MEXC broker initialized for historical data (public endpoints available)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize MEXC broker for historical data: {e}")

        # Initialize Phemex
        # NOTE: For historical data fetching, we can use public endpoints without API keys
        try:
            # Initialize Phemex adapter even without API keys for public endpoint access
            api_key = self._settings.broker.phemex_api_key if self._settings.broker and hasattr(self._settings.broker, 'phemex_api_key') else None
            secret_key = self._settings.broker.phemex_secret_key if self._settings.broker and hasattr(self._settings.broker, 'phemex_secret_key') else None
            testnet = self._settings.broker.phemex_testnet if self._settings.broker and hasattr(self._settings.broker, 'phemex_testnet') else True

            base_url = "https://testnet-api.phemex.com" if testnet else "https://api.phemex.com"
            self.brokers['phemex'] = PhemexBrokerAdapter(
                api_key=api_key or '',  # Pass empty string if no key
                secret_key=secret_key or '',  # Pass empty string if no key
                base_url=base_url
            )
            self.logger.info("✅ Phemex broker initialized for historical data (public endpoints available)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize Phemex broker for historical data: {e}")

        # Initialize MultiBrokerExecutionService as an option
        try:
            self.brokers['multi'] = MultiBrokerExecutionService(settings=self._settings)
            self.logger.info("✅ MultiBroker service initialized for historical data")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize MultiBroker service for historical data: {e}")

    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """
        Get historical data using the preferred data source with fallback options.

        Args:
            symbol: Trading symbol
            period: Historical period (e.g., '7d', '30d', '1h')
            timeframe: Candlestick timeframe (e.g., '1m', '5m', '1h')

        Returns:
            List of historical data points
        """
        symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available
        from application.symbol_management.centralized_symbol_manager import is_symbol_approved
        if not is_symbol_approved(symbol_str):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Not available for trading.")
            return []  # Return empty list to indicate no data available

        # Check if this symbol has recently failed to fetch data
        import time
        current_time = time.time()
        if symbol_str in self.failed_symbols_cache:
            last_failure = self.failed_symbols_cache[symbol_str]
            if current_time - last_failure < self.failed_symbols_cache_duration:
                self.logger.debug(f"Skipping data fetch for {symbol_str} - recently failed (less than {self.failed_symbols_cache_duration}s ago)")

                # Try to get data from local CSV cache as a fallback
                cached_data = self._get_cached_data_fallback(symbol_str, period, timeframe)
                if cached_data:
                    self.logger.info(f"✅ Retrieved cached data for {symbol_str} from local storage")
                    return cached_data

                return []  # Return empty list to avoid repeated attempts

        # Create ordered list of data sources to try
        data_sources = [self.preferred_data_source] + [source for source in self.fallback_sources
                                                       if source != self.preferred_data_source]

        self.logger.info(f"Fetching historical data for {symbol_str} from sources: {data_sources}")

        current_time_sec = time.time()
        for source in data_sources:
            key = (source.lower(), symbol_str)
            if key in self.unsupported_exchange_symbols:
                last_failed_ts = self.unsupported_exchange_symbols[key]
                if current_time_sec - last_failed_ts < self.unsupported_exchange_ttl:
                    self.logger.debug(f"Skipping {source} for {symbol_str} - known unsupported symbol on {source}")
                    continue
                else:
                    # TTL expired (24 hours passed), remove so we can re-check exchange availability
                    del self.unsupported_exchange_symbols[key]

            try:
                self.logger.debug(f"Attempting to fetch historical data for {symbol_str} from {source}")

                # Increment request counter
                if source in self.usage_stats:
                    self.usage_stats[source]['requests'] += 1

                # Try to get historical data from the current source
                data = self._fetch_from_source(source, symbol_str, period, timeframe)

                if data and len(data) > 0:
                    self.logger.info(f"✅ Successfully fetched {len(data)} historical data points for {symbol_str} from {source}")

                    # Cache the data locally for future use
                    self._cache_data_locally(symbol_str, data)

                    return data
                else:
                    self.logger.debug(f"No data returned from {source} for {symbol_str}, trying next fallback source...")

            except Exception as e:
                error_str = str(e).lower()
                if 'invalid symbol' in error_str or '-1121' in error_str or 'invalid_symbol' in error_str:
                    self.unsupported_exchange_symbols[key] = time.time()
                    self.logger.debug(f"Cached {symbol_str} as unsupported on {source} (24-hour TTL)")
                elif any(network_error in error_str for network_error in ['resolve', 'nodename', 'servname', 'connection', 'timeout', 'network', 'ssl']):
                    self.logger.debug(f"Network issue fetching data from {source} for {symbol_str}: {e}")
                else:
                    self.logger.debug(f"Failed to fetch historical data for {symbol_str} from {source}: {e}")
                    if source in self.usage_stats:
                        self.usage_stats[source]['errors'] += 1
                continue

        # If all sources failed, try to get data from local CSV cache as a fallback
        cached_data = self._get_cached_data_fallback(symbol_str, period, timeframe)
        if cached_data:
            self.logger.info(f"✅ Retrieved cached data for {symbol_str} from local storage as fallback")
            return cached_data

        # If all sources and fallback failed, add to failed symbols cache and return empty list
        # This allows the system to continue operating even if historical data is unavailable
        error_msg = f"Failed to fetch historical data for {symbol_str} from any data source. Tried: {data_sources}"
        self.logger.error(error_msg)
        self.logger.warning(f"Returning empty data list for {symbol_str} - system will continue with limited functionality")

        # Add to failed symbols cache to prevent repeated attempts
        self.failed_symbols_cache[symbol_str] = current_time
        return []  # Return empty list instead of raising exception

    def _get_cached_data_fallback(self, symbol: str, period: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Get cached data from local storage as a fallback when online sources fail.
        """
        try:
            # Try to load from CSV cache if available
            from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
            # Use the same base path as configured in the environment variable
            csv_data_path = self._settings.data.csv_data_path if self._settings.data and hasattr(self._settings.data, 'csv_data_path') else './data/history/raw/1m'
            # Extract the base path correctly (ensure we keep the relative path structure)
            # If path starts with ./ then keep it relative, otherwise handle absolute paths
            if csv_data_path.startswith('./'):
                # For relative paths like ./data/history/raw/1m, extract base as ./data
                path_parts = csv_data_path.split('/')
                if len(path_parts) >= 4 and 'data' in path_parts:
                    # Find the index of 'data' and keep the relative structure
                    data_idx = path_parts.index('data')
                    base_path = '/'.join(path_parts[:data_idx+1])  # e.g., ./data
                else:
                    base_path = './data'
            elif csv_data_path.startswith('/'):
                # For absolute paths, extract properly
                path_parts = csv_data_path.lstrip("/").split('/')
                if 'data' in path_parts:
                    data_idx = path_parts.index('data')
                    base_path = '/' + '/'.join(path_parts[:data_idx+1])  # e.g., /data
                else:
                    base_path = './data'
            else:
                # For other formats, default to relative path
                base_path = './data'

            csv_loader = CSVHistoryLoaderAdapter(base_path=base_path)

            # Try loading directly using the load method which returns Unix timestamps
            df = csv_loader.load(symbol, timeframe)
            if not df.empty and 'timestamp' in df.columns:
                # Convert DataFrame to the expected format with Unix timestamps
                result = []
                for _, row in df.iterrows():
                    result.append({
                        'timestamp': int(row['timestamp']) if pd.notna(row['timestamp']) else 0,
                        'open': float(row['open']) if 'open' in row and pd.notna(row['open']) else 0.0,
                        'high': float(row['high']) if 'high' in row and pd.notna(row['high']) else 0.0,
                        'low': float(row['low']) if 'low' in row and pd.notna(row['low']) else 0.0,
                        'close': float(row['close']) if 'close' in row and pd.notna(row['close']) else 0.0,
                        'volume': float(row['volume']) if 'volume' in row and pd.notna(row['volume']) else 0.0
                    })
                self.logger.info(f"Loaded {len(result)} data points from CSV cache for {symbol}")
                return result
            else:
                self.logger.debug(f"No cached data found in CSV for {symbol}")

        except Exception as e:
            self.logger.warning(f"Could not load cached data for {symbol}: {e}")

        # If no real data is available, return empty list instead of synthetic data
        # This ensures the system only operates with real data
        self.logger.warning(f"No real historical data available for {symbol}, returning empty list")
        return []

    def _cache_data_locally(self, symbol: str, data: List[Dict[str, Any]]):
        """
        Cache data locally for future use when online sources are unavailable.
        """
        try:
            # Save to CSV cache for future use
            from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
            # Use the same base path as configured in the environment variable
            csv_data_path = self._settings.data.csv_data_path if self._settings.data and hasattr(self._settings.data, 'csv_data_path') else './data/history/raw/1m'
            # Extract the base path correctly (ensure we keep the relative path structure)
            # If path starts with ./ then keep it relative, otherwise handle absolute paths
            if csv_data_path.startswith('./'):
                # For relative paths like ./data/history/raw/1m, extract base as ./data
                path_parts = csv_data_path.split('/')
                if len(path_parts) >= 4 and 'data' in path_parts:
                    # Find the index of 'data' and keep the relative structure
                    data_idx = path_parts.index('data')
                    base_path = '/'.join(path_parts[:data_idx+1])  # e.g., ./data
                else:
                    base_path = './data'
            elif csv_data_path.startswith('/'):
                # For absolute paths, extract properly
                path_parts = csv_data_path.lstrip("/").split('/')
                if 'data' in path_parts:
                    data_idx = path_parts.index('data')
                    base_path = '/' + '/'.join(path_parts[:data_idx+1])  # e.g., /data
                else:
                    base_path = './data'
            else:
                # For other formats, default to relative path
                base_path = './data'

            csv_loader = CSVHistoryLoaderAdapter(base_path=base_path)

            # Ensure data has Unix timestamps before saving
            processed_data = []
            for item in data:
                processed_item = item.copy()
                # Ensure timestamp is Unix timestamp integer
                if isinstance(processed_item['timestamp'], (pd.Timestamp, datetime)):
                    processed_item['timestamp'] = int(processed_item['timestamp'].timestamp())
                elif isinstance(processed_item['timestamp'], str):
                    # If it's a datetime string, convert to Unix timestamp
                    dt = pd.to_datetime(processed_item['timestamp'], utc=True)
                    processed_item['timestamp'] = int(dt.timestamp())
                processed_data.append(processed_item)

            # Save the data to CSV
            csv_loader.save_historical_data(symbol, processed_data)
            self.logger.debug(f"Cached {len(data)} data points for {symbol} in local storage")

        except Exception as e:
            self.logger.warning(f"Could not cache data for {symbol}: {e}")

    def _fetch_from_source(self, source: str, symbol: str, period: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Fetch historical data from a specific source.
        
        Args:
            source: Data source ('bingx', 'binance', 'mexc', 'phemex', 'multi')
            symbol: Trading symbol
            period: Historical period
            timeframe: Candlestick timeframe
            
        Returns:
            List of historical data points
        """
        if source not in self.brokers:
            self.logger.warning(f"Data source {source} not available")
            return []  # Return empty list instead of raising an exception to allow fallback

        broker = self.brokers[source]

        # Different brokers may have different methods for fetching historical data
        # For now, we'll use direct API calls for most reliable historical data
        if source == 'binance':
            return self._fetch_binance_historical(symbol, period, timeframe)
        elif source == 'bingx':
            return self._fetch_bingx_historical(symbol, period, timeframe)
        elif source == 'mexc':
            return self._fetch_mexc_historical(symbol, period, timeframe)
        elif source == 'phemex':
            return self._fetch_phemex_historical(symbol, period, timeframe)
        elif source == 'multi':
            # Use the multi broker service's method if available
            if hasattr(broker, 'get_historical_data'):
                return broker.get_historical_data(Symbol(symbol), period, timeframe)
            else:
                # Fall back to direct API calls
                return self._fetch_binance_historical(symbol, period, timeframe)
        else:
            # Default to direct API call
            return self._fetch_binance_historical(symbol, period, timeframe)

    def _handle_http_error(self, e: Exception, symbol: str, source: str) -> Exception:
        """Helper to decode requests HTTPError and return a detailed, user-friendly exception."""
        import requests
        if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
            try:
                err_json = e.response.json()
                if isinstance(err_json, dict):
                    msg = err_json.get('msg') or err_json.get('message') or ''
                    code = err_json.get('code')
                    
                    # Custom mapping for known code errors (e.g. Binance -1121)
                    if code == -1121 or 'invalid symbol' in msg.lower() or 'invalid_symbol' in msg.lower():
                        if hasattr(self, 'unsupported_exchange_symbols'):
                            self.unsupported_exchange_symbols[(source.lower(), symbol)] = time.time()
                        detailed_msg = f"Invalid symbol '{symbol}' on {source} (code {code}: {msg})"
                    else:
                        detailed_msg = f"{source} API error (code {code}: {msg})"
                    return Exception(detailed_msg)
            except Exception:
                pass
        return e

    def _fetch_binance_historical(self, symbol: str, period: str, timeframe: str) -> List[Dict[str, Any]]:
        """Fetch historical data from Binance API directly."""
        try:
            # Convert period to milliseconds
            start_time = self._convert_period_to_ms(period)
            end_time = int(datetime.now().timestamp() * 1000)

            # Binance API endpoint for klines
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': timeframe,
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000  # Max limit for Binance
            }

            # Use session with proper connection management
            with requests.Session() as session:
                response = session.get(url, params=params, timeout=10)
                response.raise_for_status()

            klines = response.json()

            # Convert Binance kline format to our expected format
            converted_data = []
            for kline in klines:
                # Binance kline format: [open_time, open, high, low, close, volume, ...]
                # The open_time is in milliseconds (e.g., 1703123456000)
                timestamp_ms = kline[0]
                # Convert to seconds (divide by 1000) but ensure it's a proper Unix timestamp
                # Use integer division to avoid floating point issues
                timestamp_s = int(timestamp_ms) // 1000 if isinstance(timestamp_ms, (int, float)) else timestamp_ms
                converted_data.append({
                    'timestamp': int(timestamp_s),  # Store as Unix timestamp integer
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })

            return converted_data

        except Exception as e:
            detailed_e = self._handle_http_error(e, symbol, "Binance")
            self.logger.debug(f"Source Binance failed for {symbol}: {detailed_e}")
            raise detailed_e

    def _fetch_bingx_historical(self, symbol: str, period: str, timeframe: str) -> List[Dict[str, Any]]:
        """Fetch historical data from BingX API directly."""
        try:
            # Convert period to milliseconds
            start_time = self._convert_period_to_ms(period)
            end_time = int(datetime.now().timestamp() * 1000)

            # BingX API endpoint for klines
            url = f"https://open-api.bingx.com/openApi/quote/v1/klines"
            params = {
                'symbol': symbol,
                'interval': timeframe,
                'startTime': start_time,
                'endTime': end_time,
                'limit': 500  # BingX max limit
            }

            # Add API key to headers
            headers = {
                'X-BX-APIKEY': self._settings.broker.bingx_api_key if self._settings.broker and hasattr(self._settings.broker, 'bingx_api_key') else ''
            }

            # Use session with proper connection management
            with requests.Session() as session:
                response = session.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()

            data = response.json()

            if data.get('code') != 0:
                raise Exception(f"BingX API error: {data.get('msg', 'Unknown error')}")

            klines = data.get('data', [])

            # Convert BingX kline format to our expected format
            converted_data = []
            for kline in klines:
                timestamp_ms = kline[0]
                # Convert to seconds (divide by 1000) but ensure it's a proper Unix timestamp
                # Use integer division to avoid floating point issues
                timestamp_s = int(timestamp_ms) // 1000 if isinstance(timestamp_ms, (int, float)) else timestamp_ms
                converted_data.append({
                    'timestamp': int(timestamp_s),  # Store as Unix timestamp integer
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })

            return converted_data

        except Exception as e:
            detailed_e = self._handle_http_error(e, symbol, "BingX")
            self.logger.debug(f"Source BingX failed for {symbol}: {detailed_e}")
            raise detailed_e

    def _fetch_mexc_historical(self, symbol: str, period: str, timeframe: str) -> List[Dict[str, Any]]:
        """Fetch historical data from MEXC API directly."""
        try:
            # Convert period to milliseconds
            start_time = self._convert_period_to_ms(period)
            end_time = int(datetime.now().timestamp() * 1000)

            # MEXC API endpoint for klines
            url = f"https://api.mexc.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': timeframe,
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000  # Max limit for MEXC
            }

            # Use session with proper connection management
            with requests.Session() as session:
                response = session.get(url, params=params, timeout=10)
                response.raise_for_status()

            klines = response.json()

            # Convert MEXC kline format to our expected format
            converted_data = []
            for kline in klines:
                # MEXC kline format: [open_time, open, high, low, close, volume, ...]
                timestamp_ms = kline[0]
                # Convert to seconds (divide by 1000) but ensure it's a proper Unix timestamp
                # Use integer division to avoid floating point issues
                timestamp_s = int(timestamp_ms) // 1000 if isinstance(timestamp_ms, (int, float)) else timestamp_ms
                converted_data.append({
                    'timestamp': int(timestamp_s),  # Store as Unix timestamp integer
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })

            return converted_data

        except Exception as e:
            detailed_e = self._handle_http_error(e, symbol, "MEXC")
            self.logger.debug(f"Source MEXC failed for {symbol}: {detailed_e}")
            raise detailed_e

    def _fetch_phemex_historical(self, symbol: str, period: str, timeframe: str) -> List[Dict[str, Any]]:
        """Fetch historical data from Phemex API directly."""
        try:
            # Convert period to milliseconds
            start_time = self._convert_period_to_ms(period)
            end_time = int(datetime.now().timestamp() * 1000)

            # Phemex API endpoint for klines
            # Note: Phemex has different endpoint format
            url = f"https://api.phemex.com/md/kline"
            params = {
                'symbol': symbol,
                'resolution': self._convert_timeframe_to_phemex(timeframe),
                'from': start_time // 1000,  # Phemex expects seconds
                'to': end_time // 1000,      # Phemex expects seconds
            }

            # Use session with proper connection management
            with requests.Session() as session:
                response = session.get(url, params=params, timeout=10)
                response.raise_for_status()

            data = response.json()

            if data.get('code') != 0:
                raise Exception(f"Phemex API error: {data.get('msg', 'Unknown error')}")

            klines = data.get('result', {}).get('data', [])

            # Convert Phemex kline format to our expected format
            converted_data = []
            for kline in klines:
                timestamp_ms = kline[0]
                # Convert to seconds (divide by 1000) but ensure it's a proper Unix timestamp
                # Use integer division to avoid floating point issues
                timestamp_s = int(timestamp_ms) // 1000 if isinstance(timestamp_ms, (int, float)) else timestamp_ms
                converted_data.append({
                    'timestamp': int(timestamp_s),  # Store as Unix timestamp integer
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })

            return converted_data

        except Exception as e:
            detailed_e = self._handle_http_error(e, symbol, "Phemex")
            self.logger.debug(f"Source Phemex failed for {symbol}: {detailed_e}")
            raise detailed_e

    def _convert_timeframe_to_phemex(self, timeframe: str) -> str:
        """Convert our timeframe format to Phemex format."""
        mapping = {
            '1m': '1',
            '5m': '5',
            '15m': '15',
            '30m': '30',
            '1h': '60',
            '2h': '120',
            '4h': '240',
            '6h': '360',
            '12h': '720',
            '1d': 'D',
            '1w': 'W',
            '1M': 'M'
        }
        return mapping.get(timeframe, '1m')  # Default to 1m if not found

    def _convert_period_to_ms(self, period: str) -> int:
        """Convert period string to milliseconds timestamp."""
        if period.endswith('d'):
            days = int(period[:-1])
            start_time = datetime.now() - timedelta(days=days)
        elif period.endswith('h'):
            hours = int(period[:-1])
            start_time = datetime.now() - timedelta(hours=hours)
        elif period.endswith('m'):
            minutes = int(period[:-1])
            start_time = datetime.now() - timedelta(minutes=minutes)
        else:
            # Default to 30 days if format is unknown
            start_time = datetime.now() - timedelta(days=30)

        return int(start_time.timestamp() * 1000)  # Convert to milliseconds

    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price using the preferred data source."""
        symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)

        # Try to get price from the preferred source first
        try:
            # Use direct API call to avoid rate limits on BingX
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_str}"
            with requests.Session() as session:
                response = session.get(url, timeout=5)
                response.raise_for_status()

            data = response.json()
            return float(data['price'])
        except Exception as e:
            self.logger.warning(f"Failed to get current price for {symbol_str} from Binance: {e}")
            # Fallback to other sources if needed
            try:
                url = f"https://open-api.bingx.com/openApi/quote/v1/ticker/price?symbol={symbol_str}"
                headers = {'X-BX-APIKEY': self._settings.broker.bingx_api_key if self._settings.broker and hasattr(self._settings.broker, 'bingx_api_key') else ''}
                with requests.Session() as session:
                    response = session.get(url, headers=headers, timeout=5)
                    response.raise_for_status()

                data = response.json()
                if 'data' in data and 'price' in data['data']:
                    return float(data['data']['price'])
            except Exception as e2:
                self.logger.warning(f"Failed to get current price for {symbol_str} from BingX: {e2}")

        return None

    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """Subscribe to real-time market data."""
        # For historical data provider, this is not typically implemented
        # Return a placeholder ID
        return f"historical_sub_{symbol.value if hasattr(symbol, 'value') else str(symbol)}"

    def unsubscribe_from_market_data(self, subscription_id: str):
        """Unsubscribe from real-time market data."""
        # For historical data provider, this is not typically implemented
        pass

    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """Get usage statistics for each data source."""
        return self.usage_stats


def create_configurable_historical_data_provider(
    settings,
    preferred_data_source: str = None,
    fallback_sources: List[str] = None
) -> DataProviderPort:
    """
    Factory function to create a configurable historical data provider.
    
    Args:
        preferred_data_source: Primary data source ('bingx', 'binance', 'mexc', 'phemex', 'multi')
        fallback_sources: List of fallback data sources in order of preference
        
    Returns:
        Configured historical data provider instance
    """
    return ConfigurableHistoricalDataProvider(
        settings=settings,
        preferred_data_source=preferred_data_source,
        fallback_sources=fallback_sources
    )