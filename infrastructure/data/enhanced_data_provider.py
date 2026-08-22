"""
Enhanced Data Provider that can handle new symbols by downloading data when needed.
This version uses a more practical approach for the existing architecture.
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
from infrastructure.data._edp_pricing import _EdpPricingMixin
from infrastructure.data._edp_availability import _EdpAvailabilityMixin


def _convert_period_to_ms(period: str) -> int:
    """Convert period string to milliseconds timestamp."""
    from datetime import datetime, timedelta

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


class EnhancedDataProviderAdapter(DataProviderPort, _EdpPricingMixin, _EdpAvailabilityMixin):
    """
    Enhanced data provider that can automatically download historical data
    for new symbols that are not found in the local data directory.
    """

    def __init__(self, settings, csv_base_path: str = None, download_enabled: bool = True, broker_service=None,
                 historical_data_source: str = None, fallback_sources: list = None):
        """
        Initialize the enhanced data provider.

        Args:
            settings: Injected settings object (E1.T4 — supplied by the composition root;
                this adapter no longer imports bootstrap.settings.loaders).
            csv_base_path: Path to CSV historical data files
            download_enabled: Whether to enable automatic downloading of missing data
            broker_service: Broker service to use for symbol availability checks
            historical_data_source: Preferred data source for historical data ('bingx', 'binance', 'mexc', 'phemex', 'multi')
            fallback_sources: List of fallback data sources in order of preference
        """
        # Settings injected by the composition root (E1.T4); same values as before,
        # without importing bootstrap.settings.loaders here.
        self._settings = settings
        _settings = settings
        # Use environment variable or default for base path
        if csv_base_path is None:
            csv_base_path = _settings.data.csv_data_path if _settings.data and hasattr(_settings.data, 'csv_data_path') else './data/history/raw/1m'
        # Default broker resolved once and reused by the broker-selection paths.
        self._default_broker = _settings.broker.default_broker.lower() if _settings.broker and hasattr(_settings.broker, 'default_broker') else 'bingx'.lower()

        self.csv_base_path = csv_base_path
        self.download_enabled = download_enabled
        self.broker_service = broker_service
        self.logger = EnhancedLogger("EnhancedDataProvider")

        # Initialize configurable historical data provider for fetching data from multiple sources
        self.historical_data_provider = ConfigurableHistoricalDataProvider(
            settings=_settings,
            preferred_data_source=historical_data_source,
            fallback_sources=fallback_sources
        )

        # Initialize the base CSV provider
        self.csv_provider = CSVHistoryLoaderAdapter(base_path=csv_base_path)

        # Initialize download components if enabled

        # Add caching and synchronization for symbol availability checks
        self._symbol_availability_cache = {}
        self._cache_lock = threading.Lock()
        self._cache_timeout = timedelta(minutes=2)  # Cache timeout of 2 minutes for symbol availability
        if self.download_enabled:
            self.file_repo = FileRepositoryAdapter(raw_retention_days=self._settings.data.raw_retention_days)
            self.data_downloader = DataDownloaderAdapter()
            self.sync_manager = SyncManager(self.file_repo, self.data_downloader)
            self.download_lock = threading.Lock()
        else:
            self.file_repo = None
            self.data_downloader = None
            self.sync_manager = None
            self.download_lock = None

        # Initialize symbol availability cache
        self._available_symbols_cache = set()
        self._cache_timestamp = None
        self._cache_duration = 3600  # Cache duration in seconds (1 hour)
    
    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for a symbol."""
        try:
            # Try to get from local data first
            price = self.csv_provider.get_current_price(symbol)
            if price is not None and price != 0:
                return price

            # If not available locally, try to get real price from exchange
            real_price = self._get_real_price_from_exchange(symbol.value)
            if real_price is not None and real_price > 0:
                return real_price

            # If no real data available and download is enabled, try to download historical data
            # which might help in getting more recent price information
            if self.download_enabled:
                # Attempt to download recent data to get current price
                with self.download_lock:
                    success = self._download_symbol_data_sync(symbol.value, '1m', '1d')
                    if success:
                        # Try again to get the price after download
                        updated_price = self.csv_provider.get_current_price(symbol)
                        if updated_price is not None and updated_price != 0:
                            return updated_price

            # If all else fails, return the price from CSV if available, otherwise None
            return price
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol.value}: {e}")
            return None
    
    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical data for a symbol, prioritizing real exchange data."""
        try:
            # First, try to get real historical data from external source
            # This should be the primary source for available symbols
            real_historical = self._get_real_historical_from_external_source(symbol.value, period, timeframe)
            if real_historical and len(real_historical) > 0:
                self.logger.info(f"Successfully fetched {len(real_historical)} real historical data points for {symbol.value} from external source")
                return real_historical

            # If real data is not available, try to get from local data
            try:
                historical_data = self.csv_provider.get_historical_data(symbol, period, timeframe)

                # If we have data, return it
                if historical_data and len(historical_data) > 0:
                    self.logger.info(f"Using {len(historical_data)} historical data points from local storage for {symbol.value}")
                    return historical_data
            except FileNotFoundError:
                # Symbol data doesn't exist locally, we'll try to download
                pass

            # If no data found locally and download is enabled, try to download
            if self.download_enabled:
                self.logger.info(f"No historical data found for {symbol.value}, attempting to download...")

                with self.download_lock:
                    # Attempt to download the missing data
                    success = self._download_symbol_data_sync(symbol.value, timeframe, period)

                    if success:
                        # Try again to get the data after download
                        try:
                            downloaded_data = self.csv_provider.get_historical_data(symbol, period, timeframe)
                            if downloaded_data and len(downloaded_data) > 0:
                                self.logger.info(f"Successfully downloaded {len(downloaded_data)} data points for {symbol.value}")
                                return downloaded_data
                        except FileNotFoundError:
                            pass  # Data still not available after download attempt

            # If all else fails, try to get real data one more time before falling back to minimal data
            # This is important to avoid using mock data which doesn't generate real signals
            real_historical = self._get_real_historical_from_external_source(symbol.value, period, timeframe)
            if real_historical and len(real_historical) > 0:
                self.logger.info(f"Using {len(real_historical)} real historical data points as final fallback for {symbol.value}")
                return real_historical

            # In production, never trade on synthetic minimal data if real data is missing/corrupted
            self.logger.warning(f"No valid historical data available for {symbol.value}; returning empty data to prevent corrupted signals.")
            return []

        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol.value}: {e}")
            # Try to get real historical data as fallback before failing
            real_historical = self._get_real_historical_from_external_source(symbol.value, period, timeframe)
            if real_historical and len(real_historical) > 0:
                self.logger.info(f"Using {len(real_historical)} real historical data points as fallback for {symbol.value}")
                return real_historical
            self.logger.warning(f"Data quality or provider failure for {symbol.value}: {e}. Aborting data fetch.")
            return []

    def _get_real_historical_from_external_source(self, symbol: str, period: str, timeframe: str) -> List[Dict[str, Any]]:
        """Fetch real historical data from external sources like exchanges with caching."""
        # Try to get data from cache first
        broker_name = self._get_broker_name()
        cached_data = data_cache.get(broker_name, symbol, timeframe)
        if cached_data:
            self.logger.debug(f"Using cached data for {symbol} {timeframe} from {broker_name}")
            return cached_data

        # Use the configurable historical data provider to fetch data from multiple sources
        try:
            # Convert Symbol if needed
            from domain.value_objects import Symbol as DomainSymbol
            if not isinstance(symbol, DomainSymbol):
                symbol_obj = DomainSymbol(symbol)
            else:
                symbol_obj = symbol

            # Fetch historical data using the configurable provider
            historical_data = self.historical_data_provider.get_historical_data(
                symbol=symbol_obj,
                period=period,
                timeframe=timeframe
            )

            if historical_data and len(historical_data) > 0:
                self.logger.info(f"Fetched {len(historical_data)} historical data points from configurable source for {symbol}")

                # Cache the data to prevent duplicate requests
                data_cache.set(broker_name, symbol, timeframe, historical_data, ttl=60)  # Cache for 60 seconds
                return historical_data
        except Exception as e:
            self.logger.debug(f"Could not fetch real historical data for {symbol} from configurable source: {e}")
            # Fallback to the original method if configurable provider fails
            try:
                from .binance_client import BinanceClient
                client = BinanceClient()

                # Convert period to milliseconds for Binance API
                start_time_ms = _convert_period_to_ms(period)
                end_time_ms = int(datetime.now().timestamp() * 1000)

                # Convert timeframe to Binance format (1m, 5m, 1h, etc.)
                binance_timeframe = self._convert_timeframe_to_binance(timeframe)

                # Fetch klines from Binance
                klines = client.get_klines(symbol, binance_timeframe, start_time_ms, end_time_ms)

                if klines:
                    # Convert Binance kline format to our expected format
                    converted_data = []
                    for kline in klines:
                        # Binance kline format: [open_time, open, high, low, close, volume, ...]
                        converted_data.append({
                            'timestamp': kline[0] // 1000,  # Convert ms to seconds
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5])
                        })
                    self.logger.info(f"Fetched {len(converted_data)} historical data points from external source for {symbol}")

                    # Cache the data to prevent duplicate requests
                    data_cache.set(broker_name, symbol, timeframe, converted_data, ttl=60)  # Cache for 60 seconds
                    return converted_data
            except Exception as fallback_e:
                self.logger.debug(f"Fallback method also failed for {symbol}: {fallback_e}")
                pass

        return []

    def _get_broker_name(self) -> str:
        """Get the name of the broker being used."""
        if self.broker_service:
            if hasattr(self.broker_service, 'get_broker_name'):
                return self.broker_service.get_broker_name()
            elif hasattr(self.broker_service, 'broker'):
                if hasattr(self.broker_service.broker, 'get_broker_name'):
                    return self.broker_service.broker.get_broker_name()
        return "unknown"

    def _convert_timeframe_to_binance(self, timeframe: str) -> str:
        """Convert internal timeframe to Binance format."""
        # Our internal format is already compatible with Binance format
        # 1m, 5m, 1h, 1d, etc. are the same in both systems
        return timeframe

    def _get_minimal_data_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Generate minimal mock data for a symbol when no real data is available."""
        import time
        from datetime import datetime, timedelta

        # Create minimal historical data to allow watchers to continue functioning
        # This is better than returning empty data which would break analysis
        now = datetime.now()
        data = []

        # Generate a few data points to give the watchers something to work with
        # Use an intelligent approach to estimate a reasonable price
        base_price = self._estimate_base_price_intelligently(symbol)

        for i in range(10):  # Generate 10 data points for basic analysis
            timestamp = int((now - timedelta(minutes=i)).timestamp())
            # Use smaller variations to avoid negative prices
            price_offset = (i % 3) * 0.01  # Very small variations like 0.00, 0.01, 0.02
            price = base_price + price_offset

            # Ensure high >= open/close and low <= open/close
            high = price + 0.001
            low = max(0.0001, price - 0.001)  # Ensure low is never negative
            open_price = price - 0.0005
            close_price = price + 0.0005

            data.append({
                'timestamp': timestamp,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': 100.0  # Default volume
            })

        return data

    def is_symbol_available(self, symbol: str) -> bool:
        """Check if a symbol is available on the exchange with exchange switching capability."""

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available
        from infrastructure.services.symbol_validator import symbol_validator
        from domain.value_objects import Symbol as DomainSymbol

        # Create a domain symbol object for validation
        domain_symbol = DomainSymbol(symbol)
        if not symbol_validator.is_symbol_approved(domain_symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol} is not in approved symbols list. Not available for trading.")
            return False

        # If symbol is approved, then check if it's available on the exchange
        # First, try to use the MultiBrokerExecutionService if available
        if self.broker_service:
            # Check if this is a MultiBrokerExecutionService that supports exchange switching
            if hasattr(self.broker_service, 'is_symbol_available'):
                try:
                    return self.broker_service.is_symbol_available(symbol)
                except Exception as e:
                    self.logger.debug(f"MultiBroker service failed for symbol {symbol}, falling back: {e}")

        # Check if cache is still valid
        current_time = time.time()
        cache_valid = (self._cache_timestamp is not None and
                      (current_time - self._cache_timestamp) < self._cache_duration)

        cache_size = len(self._available_symbols_cache) if self._available_symbols_cache else 0
        self.logger.debug(f"Checking symbol availability for {symbol}, cache valid: {cache_valid}, cache size: {cache_size}")

        # If cache is valid, check if symbol is in the cached set
        if cache_valid and symbol in self._available_symbols_cache:
            self.logger.debug(f"Symbol {symbol} found in valid cache")
            return True
        elif cache_valid and symbol not in self._available_symbols_cache:
            # If cache is valid but symbol is not in it, it's not available
            self.logger.debug(f"Symbol {symbol} not found in valid cache (cache size: {len(self._available_symbols_cache) if self._available_symbols_cache else 0})")
            # Still try the single symbol check as a fallback to avoid false negatives
            return self._check_single_symbol(symbol)

        # If cache is not valid, refresh it
        if not cache_valid:
            self.logger.debug(f"Cache not valid, refreshing for symbol {symbol}")
            self._refresh_available_symbols_cache()

        # Check again after refresh
        if self._available_symbols_cache:
            is_available = symbol in self._available_symbols_cache
            self.logger.debug(f"Symbol {symbol} availability after refresh: {is_available}, cache size: {len(self._available_symbols_cache)}")
            if is_available:
                return True
            else:
                # Even if not in cache, try single symbol check as fallback
                return self._check_single_symbol(symbol)
        else:
            self.logger.debug(f"Cache is empty after refresh, falling back to single symbol check for {symbol}")
            return self._check_single_symbol(symbol)

    def _download_symbol_data_sync(self, symbol: str, timeframe: str = '1m', period: str = '30d') -> bool:
        """Download historical data for a symbol using a thread-safe async approach."""
        import asyncio
        import concurrent.futures
        import threading

        # Use a thread pool to run the async operation safely
        def run_download():
            try:
                # Parse the period to determine start and end dates
                from datetime import datetime, timedelta
                if period.endswith('d'):
                    days = int(period[:-1])
                    end_time = int(datetime.now().timestamp())
                    start_time = int((datetime.now() - timedelta(days=days)).timestamp())
                elif period.endswith('h'):
                    hours = int(period[:-1])
                    end_time = int(datetime.now().timestamp())
                    start_time = int((datetime.now() - timedelta(hours=hours)).timestamp())
                elif period.endswith('m'):
                    minutes = int(period[:-1])
                    end_time = int(datetime.now().timestamp())
                    start_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp())
                else:
                    # Default to 30 days if format is unknown
                    end_time = int(datetime.now().timestamp())
                    start_time = int((datetime.now() - timedelta(days=30)).timestamp())

                # Create a new event loop for this thread and run the async operation
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Run the async operation within the new loop
                    result = loop.run_until_complete(
                        self.sync_manager.sync_symbol_data(
                            symbol=symbol,
                            timeframes=[timeframe],
                            start_time=start_time,
                            end_time=end_time
                        )
                    )
                    return result
                finally:
                    # Properly close the loop
                    if not loop.is_closed():
                        loop.close()
            except Exception as e:
                self.logger.error(f"Error in download thread for {symbol}: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return None

        # Run the async download in a separate thread
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_download)
                result = future.result(timeout=120)  # Increase timeout to 120 seconds

                if result and result.get('rows_written', 0) > 0:
                    self.logger.info(f"Successfully downloaded {result['rows_written']} data points for {symbol}")
                    return True
                elif result and result.get('success', False):
                    self.logger.info(f"Successfully downloaded data for {symbol} (success flag)")
                    return True
                else:
                    self.logger.warning(f"Download returned no data for {symbol}: {result}")
                    return False
        except concurrent.futures.TimeoutError:
            self.logger.error(f"Download timeout for {symbol}")
            return False
        except Exception as e:
            self.logger.error(f"Error downloading data for {symbol}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """Subscribe to real-time market data for a symbol."""
        # For now, use the CSV provider's method (which returns unsupported)
        return self.csv_provider.subscribe_to_market_data(symbol, callback)

    def unsubscribe_from_market_data(self, subscription_id: str):
        """Unsubscribe from real-time market data."""
        # For now, use the CSV provider's method
        return self.csv_provider.unsubscribe_from_market_data(subscription_id)


def create_enhanced_data_provider(settings, csv_base_path: str = None, download_enabled: bool = True, broker_service=None,
                                 historical_data_source: str = None, fallback_sources: list = None) -> DataProviderPort:
    """
    Factory function to create the enhanced data provider.

    Args:
        csv_base_path: Path to CSV historical data files
        download_enabled: Whether to enable automatic downloading of missing data
        broker_service: Broker service to use for symbol availability checks
        historical_data_source: Preferred data source for historical data ('bingx', 'binance', 'mexc', 'phemex', 'multi')
        fallback_sources: List of fallback data sources in order of preference

    Returns:
        Configured enhanced data provider instance
    """
    return EnhancedDataProviderAdapter(
        settings=settings,
        csv_base_path=csv_base_path,
        download_enabled=download_enabled,
        broker_service=broker_service,
        historical_data_source=historical_data_source,
        fallback_sources=fallback_sources
    )