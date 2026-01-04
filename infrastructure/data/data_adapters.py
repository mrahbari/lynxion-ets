"""
Infrastructure implementations of data services.
"""
from typing import List, Optional, Dict, Any
from domain.entities.trading_entities import MarketData
from domain.value_objects import Symbol
from domain.ports.data_ports import DataProviderPort, DataCachePort, DataAggregatorPort
from shared.logger import logger
from datetime import datetime, timedelta
import random
import threading
import time


class BaseDataProviderAdapter(DataProviderPort):
    """Base class for data provider adapters"""

    def __init__(self, name: str):
        self.name = name
        self.subscriptions = {}

    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for a symbol"""
        raise NotImplementedError

    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical data for a symbol"""
        raise NotImplementedError

    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """Subscribe to real-time market data for a symbol"""
        raise NotImplementedError

    def unsubscribe_from_market_data(self, subscription_id: str):
        """Unsubscribe from real-time market data"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]


class MockDataProviderAdapter(BaseDataProviderAdapter):
    """Infrastructure implementation of mock data provider for testing"""

    def __init__(self):
        super().__init__("MockDataProvider")
        self.mock_prices = {
            "BTCUSDT": 45123.45,
            "ETHUSDT": 2567.89,
            "BNBUSDT": 312.56,
            "SOLUSDT": 98.76,
        }
        self.mock_historical = {
            "BTCUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 45000 + i * 10,
                 "high": 45010 + i * 10, "low": 44990 + i * 10, "close": 45005 + i * 10, "volume": 100 + i}
                for i in range(100)
            ],
            "ETHUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 2500 + i * 5,
                 "high": 2505 + i * 5, "low": 2495 + i * 5, "close": 2502 + i * 5, "volume": 500 + i * 2}
                for i in range(100)
            ]
        }

    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for a symbol"""
        price = self.mock_prices.get(symbol.value)
        logger.info(f"Mock data provider: Current price for {symbol.value}: {price}")
        return price

    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical data for a symbol"""
        data = self.mock_historical.get(symbol.value, [])
        logger.info(f"Mock data provider: Retrieved {len(data)} historical data points for {symbol.value}")
        return data

    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """Subscribe to real-time market data for a symbol"""
        import uuid
        subscription_id = str(uuid.uuid4())

        def mock_data_feed():
            while subscription_id in self.subscriptions:
                price = self.get_current_price(symbol)
                if price:
                    market_data = {
                        'symbol': symbol.value,
                        'price': price,
                        'timestamp': datetime.now().timestamp(),
                        'bid': price * 0.999,
                        'ask': price * 1.001
                    }
                    try:
                        callback(market_data)
                    except Exception as e:
                        logger.error(f"Error in market data callback: {e}")
                        break
                time.sleep(1)  # Update every second

        self.subscriptions[subscription_id] = {
            'symbol': symbol,
            'callback': callback,
            'thread': threading.Thread(target=mock_data_feed, daemon=True)
        }

        self.subscriptions[subscription_id]['thread'].start()
        logger.info(f"Mock data provider: Subscribed to {symbol.value}, subscription ID: {subscription_id}")
        return subscription_id


class RedisDataCacheAdapter(DataCachePort):
    """Infrastructure implementation of Redis-based data cache"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client  # In a real implementation, this would be an actual Redis client
        if self.redis_client is None:
            # For demonstration, we'll use a simple dict as a mock cache
            self._cache = {}
        self.name = "RedisDataCache"

    def store_data(self, key: str, data: Any, ttl: int = 3600):
        """Store data in cache with TTL"""
        if self.redis_client:
            # In real implementation: self.redis_client.setex(key, ttl, data)
            pass
        else:
            # Mock implementation
            self._cache[key] = {
                'data': data,
                'ttl': ttl,
                'timestamp': time.time()
            }
        logger.info(f"Stored data in cache with key: {key}")

    def retrieve_data(self, key: str) -> Optional[Any]:
        """Retrieve data from cache"""
        if self.redis_client:
            # In real implementation: return self.redis_client.get(key)
            return None
        else:
            # Mock implementation
            if key in self._cache:
                cached = self._cache[key]
                # Check if expired
                if time.time() - cached['timestamp'] < cached['ttl']:
                    logger.info(f"Retrieved data from cache with key: {key}")
                    return cached['data']
                else:
                    # Remove expired data
                    del self._cache[key]
                    logger.info(f"Cache entry expired and removed: {key}")
        logger.info(f"Data not found in cache with key: {key}")
        return None


class DataAggregatorAdapter(DataAggregatorPort):
    """Infrastructure implementation of data aggregator"""

    def __init__(self, data_providers: List[DataProviderPort]):
        self.data_providers = data_providers
        self.name = "DataAggregator"

    def aggregate_data(self, sources: List[str], symbols: List[Symbol]) -> Dict[Symbol, Any]:
        """Aggregate data from multiple sources"""
        aggregated_data = {}

        for symbol in symbols:
            symbol_data = {}

            for provider in self.data_providers:
                try:
                    price = provider.get_current_price(symbol)
                    symbol_data[provider.name] = price
                except Exception as e:
                    logger.error(f"Error getting data from {provider.name}: {e}")

            # Calculate aggregate metrics
            available_prices = [price for price in symbol_data.values() if price is not None]
            if available_prices:
                symbol_data['average_price'] = sum(available_prices) / len(available_prices)
                symbol_data['best_price'] = min(available_prices) if available_prices else None
                symbol_data['worst_price'] = max(available_prices) if available_prices else None

            aggregated_data[symbol] = symbol_data

        logger.info(f"Aggregated data for {len(symbols)} symbols from {len(self.data_providers)} sources")
        return aggregated_data


class WebsocketDataProviderAdapter(BaseDataProviderAdapter):
    """Infrastructure implementation of WebSocket data provider"""

    def __init__(self, base_url: str):
        super().__init__("WebSocketDataProvider")
        self.base_url = base_url
        self.websocket_connections = {}
        self._running = False

    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price from cached WebSocket data"""
        # In a real implementation, this would retrieve from WebSocket cache
        # For mock, return None to indicate this needs live data
        return None

    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical data - in WebSocket context, this might use REST API"""
        # For WebSocket provider, historical data might come from a different source
        # Using mock data for demonstration
        mock_data = MockDataProviderAdapter().get_historical_data(symbol, period, timeframe)
        return mock_data

    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """Subscribe to WebSocket market data"""
        # In a real implementation, this would establish a WebSocket connection
        import uuid
        subscription_id = f"WS_{str(uuid.uuid4())}"

        def websocket_feed():
            # Simulate WebSocket feed with mock data
            mock_provider = MockDataProviderAdapter()
            while self._running and subscription_id in self.websocket_connections:
                price = mock_provider.get_current_price(symbol)
                if price:
                    market_data = {
                        'symbol': symbol.value,
                        'price': price,
                        'timestamp': datetime.now().timestamp(),
                        'type': 'websocket'
                    }
                    try:
                        callback(market_data)
                    except Exception as e:
                        logger.error(f"Error in WebSocket callback: {e}")
                        break
                time.sleep(0.5)  # Simulate real-time updates

        self.websocket_connections[subscription_id] = {
            'symbol': symbol,
            'callback': callback,
            'thread': threading.Thread(target=websocket_feed, daemon=True)
        }

        self.websocket_connections[subscription_id]['thread'].start()
        logger.info(f"WebSocket data provider: Subscribed to {symbol.value}")
        return subscription_id

    def start(self):
        """Start the WebSocket service"""
        self._running = True

    def stop(self):
        """Stop the WebSocket service"""
        self._running = False
        for conn in self.websocket_connections.values():
            if conn['thread'].is_alive():
                conn['thread'].join(timeout=1)  # Real Data Provider Implementation


class HistoricalDataProviderAdapter:
    """Real historical data provider implementation"""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache

    def get_historical_data(self,
                            symbol: Symbol,
                            start_date: str,
                            end_date: str,
                            timeframe: str = '1d') -> List[Dict[str, Any]]:
        """Get historical market data for backtesting"""
        # Create a cache key
        cache_key = f"{symbol.value}_{start_date}_{end_date}_{timeframe}"

        # Check if data is in cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now().timestamp() - timestamp) < self.cache_ttl:
                logger.info(f"Retrieved historical data for {symbol.value} from cache")
                return cached_data

        # In a real implementation, this would fetch from an API
        # For demonstration, generate mock historical data
        logger.info(f"Generating mock historical data for {symbol.value}")

        # Parse dates (simplified for demo)
        import dateutil.parser
        try:
            start_dt = dateutil.parser.parse(start_date) if start_date else datetime.now() - timedelta(days=30)
            end_dt = dateutil.parser.parse(end_date) if end_date else datetime.now()
        except:
            # If parsing fails, use default dates
            start_dt = datetime.now() - timedelta(days=30)
            end_dt = datetime.now()

        # Calculate number of data points based on timeframe
        if timeframe == '1m':
            interval = timedelta(minutes=1)
        elif timeframe == '5m':
            interval = timedelta(minutes=5)
        elif timeframe == '1h':
            interval = timedelta(hours=1)
        else:  # Default to daily
            interval = timedelta(days=1)

        # Generate mock price data
        current_time = start_dt
        mock_data = []

        # Start with a base price
        current_price = 40000.0 + (hash(symbol.value) % 10000)  # Different starting prices for different symbols
        while current_time <= end_dt:
            # Generate OHLCV data with some randomness
            open_price = current_price
            daily_change = (random.random() - 0.5) * 0.05  # Up to ±2.5% daily change
            high_mult = 1 + random.random() * 0.02  # Up to 2% above open
            low_mult = 1 - random.random() * 0.02  # Up to 2% below open
            close_mult = 1 + (random.random() - 0.5) * 0.04  # Close can be anywhere in range

            high_price = open_price * high_mult
            low_price = open_price * low_mult
            close_price = max(low_price, min(high_price, open_price * (1 + daily_change)))

            volume = 1000 + random.random() * 9000  # Random volume between 1k-10k

            mock_data.append({
                'timestamp': current_time.isoformat(),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })

            # Update for next iteration
            current_price = close_price
            current_time += interval

        # Cache the data
        self.cache[cache_key] = (mock_data, datetime.now().timestamp())

        logger.info(f"Generated {len(mock_data)} historical data points for {symbol.value}")
        return mock_data
