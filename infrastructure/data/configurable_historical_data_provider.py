"""
Configurable Historical Data Provider that can use different brokers to avoid rate limits.
This provider allows selecting different data sources for historical data requests.
"""
import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import requests
import pandas as pd

from domain.ports.data_ports import DataProviderPort
from domain.entities.trading_entities import MarketData
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
    
    def __init__(self, preferred_data_source: str = None, fallback_sources: List[str] = None):
        """
        Initialize the configurable historical data provider.
        
        Args:
            preferred_data_source: Primary data source ('bingx', 'binance', 'mexc', 'phemex', 'multi')
            fallback_sources: List of fallback data sources in order of preference
        """
        self.logger = EnhancedLogger("ConfigurableHistoricalDataProvider")
        
        # Determine preferred data source
        if preferred_data_source is None:
            # Default to binance for historical data to avoid BingX rate limits
            preferred_data_source = os.getenv('PREFERRED_HISTORICAL_DATA_SOURCE', 'binance')
        
        # Set default fallbacks if not provided
        if fallback_sources is None:
            fallback_sources = os.getenv('HISTORICAL_DATA_FALLBACK_SOURCES', 'binance,mexc,phemex').split(',')
        
        self.preferred_data_source = preferred_data_source.lower()
        self.fallback_sources = [source.strip().lower() for source in fallback_sources]
        
        # Initialize broker adapters
        self.brokers = {}
        self._initialize_brokers()
        
        # Track usage statistics to help with load balancing
        self.usage_stats = {source: {'requests': 0, 'errors': 0} for source in ['bingx', 'binance', 'mexc', 'phemex']}
        
        self.logger.info(f"Configurable Historical Data Provider initialized with preferred source: {self.preferred_data_source}")
        self.logger.info(f"Fallback sources: {self.fallback_sources}")

    def _initialize_brokers(self):
        """Initialize broker adapters for historical data retrieval."""
        # Initialize Binance (usually has good historical data availability)
        try:
            binance_config = {
                'api_key': os.getenv('BINANCE_API_KEY'),
                'secret_key': os.getenv('BINANCE_SECRET_KEY'),
                'testnet': os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
            }
            if binance_config['api_key'] and binance_config['secret_key']:
                self.brokers['binance'] = BinanceBrokerAdapter(
                    api_key=binance_config['api_key'],
                    secret_key=binance_config['secret_key']
                )
                self.logger.info("✅ Binance broker initialized for historical data")
            else:
                self.logger.warning("⚠️ Binance broker not configured for historical data (missing API keys)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize Binance broker for historical data: {e}")

        # Initialize BingX
        try:
            bingx_config = {
                'api_key': os.getenv('BINGX_API_KEY'),
                'secret_key': os.getenv('BINGX_SECRET_KEY'),
                'passphrase': os.getenv('BINGX_PASSPHRASE', ''),
                'testnet': os.getenv('BINGX_TESTNET', 'true').lower() == 'true'
            }
            required_keys = ['api_key', 'secret_key']
            if all(bingx_config.get(key) for key in required_keys):
                self.brokers['bingx'] = BingXBrokerAdapter(bingx_config)
                self.logger.info("✅ BingX broker initialized for historical data")
            else:
                self.logger.warning("⚠️ BingX broker not configured for historical data (missing API keys)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize BingX broker for historical data: {e}")

        # Initialize MEXC
        try:
            mexc_api_key = os.getenv('MEXC_API_KEY')
            mexc_secret_key = os.getenv('MEXC_SECRET_KEY')
            mexc_testnet = os.getenv('MEXC_TESTNET', 'true').lower() == 'true'

            if mexc_api_key and mexc_secret_key:
                base_url = "https://api-testnet.mexc.com" if mexc_testnet else "https://api.mexc.com"
                self.brokers['mexc'] = MEXCBrokerAdapter(
                    api_key=mexc_api_key,
                    secret_key=mexc_secret_key,
                    base_url=base_url
                )
                self.logger.info("✅ MEXC broker initialized for historical data")
            else:
                self.logger.warning("⚠️ MEXC broker not configured for historical data (missing API keys)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize MEXC broker for historical data: {e}")

        # Initialize Phemex
        try:
            phemex_api_key = os.getenv('PHEMEX_API_KEY')
            phemex_secret_key = os.getenv('PHEMEX_SECRET_KEY')
            phemex_testnet = os.getenv('PHEMEX_TESTNET', 'true').lower() == 'true'

            if phemex_api_key and phemex_secret_key:
                base_url = "https://testnet-api.phemex.com" if phemex_testnet else "https://api.phemex.com"
                self.brokers['phemex'] = PhemexBrokerAdapter(
                    api_key=phemex_api_key,
                    secret_key=phemex_secret_key,
                    base_url=base_url
                )
                self.logger.info("✅ Phemex broker initialized for historical data")
            else:
                self.logger.warning("⚠️ Phemex broker not configured for historical data (missing API keys)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize Phemex broker for historical data: {e}")

        # Initialize MultiBrokerExecutionService as an option
        try:
            self.brokers['multi'] = MultiBrokerExecutionService()
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
        from utils.symbol_validator import symbol_validator
        if not symbol_validator.is_symbol_approved(symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Not available for trading.")
            return []  # Return empty list to indicate no data available

        # Create ordered list of data sources to try
        data_sources = [self.preferred_data_source] + [source for source in self.fallback_sources
                                                       if source != self.preferred_data_source]

        self.logger.info(f"Fetching historical data for {symbol_str} from sources: {data_sources}")
        
        for source in data_sources:
            try:
                self.logger.debug(f"Attempting to fetch historical data for {symbol_str} from {source}")
                
                # Increment request counter
                self.usage_stats[source]['requests'] += 1
                
                # Try to get historical data from the current source
                data = self._fetch_from_source(source, symbol_str, period, timeframe)
                
                if data and len(data) > 0:
                    self.logger.info(f"✅ Successfully fetched {len(data)} historical data points for {symbol_str} from {source}")
                    return data
                else:
                    self.logger.warning(f"⚠️ No data returned from {source} for {symbol_str}, trying next source...")
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to fetch historical data for {symbol_str} from {source}: {e}")
                self.usage_stats[source]['errors'] += 1
                continue
        
        # If all sources failed, raise an exception
        error_msg = f"Failed to fetch historical data for {symbol_str} from any data source. Tried: {data_sources}"
        self.logger.error(error_msg)
        raise Exception(error_msg)

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
            raise ValueError(f"Data source {source} not available")
        
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
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            klines = response.json()
            
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
            
            return converted_data
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data from Binance for {symbol}: {e}")
            raise

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
                'X-BX-APIKEY': os.getenv('BINGX_API_KEY', '')
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') != 0:
                raise Exception(f"BingX API error: {data.get('msg', 'Unknown error')}")
            
            klines = data.get('data', [])
            
            # Convert BingX kline format to our expected format
            converted_data = []
            for kline in klines:
                converted_data.append({
                    'timestamp': int(kline[0]) // 1000,  # Convert ms to seconds
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            return converted_data
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data from BingX for {symbol}: {e}")
            raise

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
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            klines = response.json()
            
            # Convert MEXC kline format to our expected format
            converted_data = []
            for kline in klines:
                # MEXC kline format: [open_time, open, high, low, close, volume, ...]
                converted_data.append({
                    'timestamp': kline[0] // 1000,  # Convert ms to seconds
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            return converted_data
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data from MEXC for {symbol}: {e}")
            raise

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
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') != 0:
                raise Exception(f"Phemex API error: {data.get('msg', 'Unknown error')}")
            
            klines = data.get('result', {}).get('data', [])
            
            # Convert Phemex kline format to our expected format
            converted_data = []
            for kline in klines:
                converted_data.append({
                    'timestamp': int(kline[0]) // 1000,  # Convert to seconds
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            return converted_data
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data from Phemex for {symbol}: {e}")
            raise

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
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return float(data['price'])
        except Exception as e:
            self.logger.warning(f"Failed to get current price for {symbol_str} from Binance: {e}")
            # Fallback to other sources if needed
            try:
                url = f"https://open-api.bingx.com/openApi/quote/v1/ticker/price?symbol={symbol_str}"
                headers = {'X-BX-APIKEY': os.getenv('BINGX_API_KEY', '')}
                response = requests.get(url, headers=headers, timeout=5)
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
        preferred_data_source=preferred_data_source,
        fallback_sources=fallback_sources
    )