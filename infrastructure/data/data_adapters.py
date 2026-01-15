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
            "XRPUSDT": 0.55,
            "ADAUSDT": 0.42,
            "DOGEUSDT": 0.08,
            "AVAXUSDT": 32.45,
            "MATICUSDT": 0.68,
            "DOTUSDT": 5.89,
            "LTCUSDT": 72.34,
            "LINKUSDT": 14.56,
            "XLMUSDT": 0.15,
            "TRXUSDT": 0.11,
            "UNIUSDT": 6.78,
            "ATOMUSDT": 7.89,
            "ETCUSDT": 23.45,
            "BCHUSDT": 512.34,
            "NEOUSDT": 12.34,
            "XTZUSDT": 0.89,
            "EOSUSDT": 0.67,
            "XMRUSDT": 156.78,
            "ZECUSDT": 31.23,
            "DASHUSDT": 45.67,
            "ZILUSDT": 0.02,
            "VETUSDT": 0.005,
            "ONTUSDT": 0.23,
            "QTUMUSDT": 2.34,
            "IOTAUSDT": 0.18,
            "THETAUSDT": 1.45,
            "ALGOUSDT": 0.12,
            "ZRXUSDT": 0.34,
            "MKRUSDT": 1234.56,
            "COMPUSDT": 189.78,
            "BATUSDT": 0.23,
            "XEMUSDT": 0.05,
            "OMGUSDT": 1.67,
            "WAVESUSDT": 2.34,
            "ICXUSDT": 0.23,
            "STEEMUSDT": 0.98,
            "STORJUSDT": 0.67,
            "BTGUSDT": 23.45,
            "ADAUSDT": 0.42,
            "NEOUSDT": 12.34,
            "XLMUSDT": 0.15,
            "TRXUSDT": 0.11,
            "ETCUSDT": 23.45,
            "ZECUSDT": 31.23,
            "DASHUSDT": 45.67,
            "XRPUSDT": 0.55,
            "DOGEUSDT": 0.08,
            "AVAXUSDT": 32.45,
            "MATICUSDT": 0.68,
            "DOTUSDT": 5.89,
            "LINKUSDT": 14.56,
            "BCHUSDT": 512.34,
            "ZILUSDT": 0.02,
            "VETUSDT": 0.005,
            "QTUMUSDT": 2.34,
            "IOTAUSDT": 0.18,
            "HBARUSDT": 0.05,
            "SUIUSDT": 2.34,
            "TAOUSDT": 1.23,
            "GIGGLEUSDT": 0.01,
            "BIFIUSDT": 1234.56,
            "PAXGUSDT": 1890.12,
            "WBTCUSDT": 45000.78,
            "YFIUSDT": 15432.98,
            "DCRUSDT": 23.45,
            "HOTUSDT": 0.001,
            "ZILUSDT": 0.02,
            "ETCUSDT": 23.45,
            "DOGEUSDT": 0.08,
            "AVAXUSDT": 32.45,
            "MATICUSDT": 0.68,
            "DOTUSDT": 5.89,
            "LINKUSDT": 14.56,
            "BCHUSDT": 512.34,
            "XLMUSDT": 0.15,
            "TRXUSDT": 0.11,
            "XMRUSDT": 156.78,
            "HBARUSDT": 0.05,
            "SUIUSDT": 2.34,
            "TAOUSDT": 1.23,
            "GIGGLEUSDT": 0.01,
            "BIFIUSDT": 1234.56,
            "PAXGUSDT": 1890.12,
            "WBTCUSDT": 45000.78,
            "YFIUSDT": 15432.98,
            "DCRUSDT": 23.45,
            "HOTUSDT": 0.001,
            "NEOUSDT": 12.34,
            "LTCUSDT": 72.34,
            "BNBUSDT": 312.56,
            "SOLUSDT": 98.76
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
            ],
            "SOLUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 98 + i * 0.1,
                 "high": 98.5 + i * 0.1, "low": 97.5 + i * 0.1, "close": 98.2 + i * 0.1, "volume": 1000 + i * 10}
                for i in range(100)
            ],
            "XRPUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.5 + i * 0.001,
                 "high": 0.505 + i * 0.001, "low": 0.495 + i * 0.001, "close": 0.502 + i * 0.001, "volume": 2000 + i * 20}
                for i in range(100)
            ],
            "ADAUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.4 + i * 0.0005,
                 "high": 0.405 + i * 0.0005, "low": 0.395 + i * 0.0005, "close": 0.402 + i * 0.0005, "volume": 1500 + i * 15}
                for i in range(100)
            ],
            "DOGEUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.08 + i * 0.0001,
                 "high": 0.081 + i * 0.0001, "low": 0.079 + i * 0.0001, "close": 0.0805 + i * 0.0001, "volume": 5000 + i * 50}
                for i in range(100)
            ],
            "AVAXUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 32 + i * 0.05,
                 "high": 32.5 + i * 0.05, "low": 31.5 + i * 0.05, "close": 32.2 + i * 0.05, "volume": 800 + i * 8}
                for i in range(100)
            ],
            "MATICUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.65 + i * 0.001,
                 "high": 0.66 + i * 0.001, "low": 0.64 + i * 0.001, "close": 0.655 + i * 0.001, "volume": 1200 + i * 12}
                for i in range(100)
            ],
            "DOTUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 5.8 + i * 0.01,
                 "high": 5.9 + i * 0.01, "low": 5.7 + i * 0.01, "close": 5.85 + i * 0.01, "volume": 600 + i * 6}
                for i in range(100)
            ],
            "LTCUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 70 + i * 0.1,
                 "high": 71 + i * 0.1, "low": 69 + i * 0.1, "close": 70.5 + i * 0.1, "volume": 300 + i * 3}
                for i in range(100)
            ],
            "LINKUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 14 + i * 0.02,
                 "high": 14.5 + i * 0.02, "low": 13.5 + i * 0.02, "close": 14.2 + i * 0.02, "volume": 700 + i * 7}
                for i in range(100)
            ],
            "XLMUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.14 + i * 0.0002,
                 "high": 0.15 + i * 0.0002, "low": 0.13 + i * 0.0002, "close": 0.145 + i * 0.0002, "volume": 3000 + i * 30}
                for i in range(100)
            ],
            "TRXUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.10 + i * 0.0001,
                 "high": 0.11 + i * 0.0001, "low": 0.09 + i * 0.0001, "close": 0.105 + i * 0.0001, "volume": 4000 + i * 40}
                for i in range(100)
            ],
            "ETCUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 23 + i * 0.05,
                 "high": 24 + i * 0.05, "low": 22 + i * 0.05, "close": 23.5 + i * 0.05, "volume": 400 + i * 4}
                for i in range(100)
            ],
            "BNBUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 310 + i * 0.1,
                 "high": 315 + i * 0.1, "low": 305 + i * 0.1, "close": 312 + i * 0.1, "volume": 200 + i * 2}
                for i in range(100)
            ],
            "NEOUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 12 + i * 0.02,
                 "high": 12.5 + i * 0.02, "low": 11.5 + i * 0.02, "close": 12.2 + i * 0.02, "volume": 500 + i * 5}
                for i in range(100)
            ],
            "XMRUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 155 + i * 0.2,
                 "high": 160 + i * 0.2, "low": 150 + i * 0.2, "close": 156 + i * 0.2, "volume": 150 + i * 1}
                for i in range(100)
            ],
            "HBARUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.05 + i * 0.0001,
                 "high": 0.06 + i * 0.0001, "low": 0.04 + i * 0.0001, "close": 0.055 + i * 0.0001, "volume": 2500 + i * 25}
                for i in range(100)
            ],
            "SUIUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 2.3 + i * 0.005,
                 "high": 2.4 + i * 0.005, "low": 2.2 + i * 0.005, "close": 2.35 + i * 0.005, "volume": 900 + i * 9}
                for i in range(100)
            ],
            "TAOUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 1.2 + i * 0.002,
                 "high": 1.3 + i * 0.002, "low": 1.1 + i * 0.002, "close": 1.25 + i * 0.002, "volume": 100 + i * 1}
                for i in range(100)
            ],
            "GIGGLEUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.01 + i * 0.00005,
                 "high": 0.02 + i * 0.00005, "low": 0.005 + i * 0.00005, "close": 0.012 + i * 0.00005, "volume": 10000 + i * 100}
                for i in range(100)
            ],
            "BIFIUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 1200 + i * 2,
                 "high": 1300 + i * 2, "low": 1100 + i * 2, "close": 1250 + i * 2, "volume": 50 + i * 0.5}
                for i in range(100)
            ],
            "PAXGUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 1800 + i * 5,
                 "high": 1900 + i * 5, "low": 1700 + i * 5, "close": 1850 + i * 5, "volume": 20 + i * 0.2}
                for i in range(100)
            ],
            "WBTCUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 44000 + i * 50,
                 "high": 46000 + i * 50, "low": 42000 + i * 50, "close": 45000 + i * 50, "volume": 10 + i * 0.1}
                for i in range(100)
            ],
            "YFIUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 15000 + i * 20,
                 "high": 16000 + i * 20, "low": 14000 + i * 20, "close": 15500 + i * 20, "volume": 5 + i * 0.05}
                for i in range(100)
            ],
            "DCRUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 23 + i * 0.05,
                 "high": 25 + i * 0.05, "low": 21 + i * 0.05, "close": 24 + i * 0.05, "volume": 100 + i * 1}
                for i in range(100)
            ],
            "HOTUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.001 + i * 0.00001,
                 "high": 0.002 + i * 0.00001, "low": 0.0005 + i * 0.00001, "close": 0.0012 + i * 0.00001, "volume": 50000 + i * 500}
                for i in range(100)
            ],
            "ZECUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 30 + i * 0.05,
                 "high": 32 + i * 0.05, "low": 28 + i * 0.05, "close": 31 + i * 0.05, "volume": 200 + i * 2}
                for i in range(100)
            ],
            "DASHUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 45 + i * 0.08,
                 "high": 47 + i * 0.08, "low": 43 + i * 0.08, "close": 46 + i * 0.08, "volume": 150 + i * 1.5}
                for i in range(100)
            ],
            "ZILUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.02 + i * 0.0001,
                 "high": 0.03 + i * 0.0001, "low": 0.01 + i * 0.0001, "close": 0.022 + i * 0.0001, "volume": 8000 + i * 80}
                for i in range(100)
            ],
            "VETUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.005 + i * 0.00002,
                 "high": 0.006 + i * 0.00002, "low": 0.004 + i * 0.00002, "close": 0.0052 + i * 0.00002, "volume": 15000 + i * 150}
                for i in range(100)
            ],
            "QTUMUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 2.3 + i * 0.005,
                 "high": 2.5 + i * 0.005, "low": 2.1 + i * 0.005, "close": 2.4 + i * 0.005, "volume": 300 + i * 3}
                for i in range(100)
            ],
            "IOTAUSDT": [
                {"timestamp": (datetime.now().timestamp() - i * 60), "open": 0.18 + i * 0.0003,
                 "high": 0.20 + i * 0.0003, "low": 0.16 + i * 0.0003, "close": 0.19 + i * 0.0003, "volume": 2000 + i * 20}
                for i in range(100)
            ]
        }

    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for a symbol"""
        symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
        price = self.mock_prices.get(symbol_str)

        # If symbol not found in mock prices, generate a reasonable default price
        # based on the symbol name to avoid the $50000.00 default issue
        if price is None:
            # Generate a reasonable price based on common cryptocurrency price ranges
            # Use the base currency to determine typical price range
            base_currency = symbol_str.replace('USDT', '').replace('USDC', '').replace('BUSD', '')

            # Common cryptocurrencies and their typical price ranges
            if base_currency in ['BTC', 'WBTC']:
                price = 45000.0 + random.uniform(-1000, 1000)  # Bitcoin range
            elif base_currency in ['ETH', 'WETH']:
                price = 2500.0 + random.uniform(-100, 100)    # Ethereum range
            elif base_currency in ['SOL', 'AVAX', 'FTM', 'APT', 'AR']:
                price = 90.0 + random.uniform(-10, 10)        # Mid-range altcoins
            elif base_currency in ['BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC', 'LINK', 'UNI', 'LTC', 'BCH']:
                price = 10.0 + random.uniform(-5, 5)          # Lower range altcoins
            elif base_currency in ['XLM', 'TRX', 'ATOM', 'NEAR', 'FIL', 'ETC', 'VET', 'XTZ', 'ICX', 'HBAR', 'SUI', 'APT']:
                price = 0.5 + random.uniform(-0.2, 0.2)       # Penny stocks/crypto range
            elif base_currency in ['SHIB', 'PEPE', 'DOGE', 'FLOKI', 'SAFEMOON']:
                price = 0.00001 + random.uniform(-0.000005, 0.000005)  # Meme coin range
            elif base_currency in ['XMR', 'ZEC', 'DASH', 'DCR']:
                price = 30.0 + random.uniform(-10, 10)        # Privacy coins range
            else:
                # For any other symbol, use a reasonable default based on common patterns
                # Use a random price between $0.01 and $500 to cover most crypto ranges
                price = random.uniform(0.01, 500.0)

        logger.info(f"Mock data provider: Current price for {symbol_str}: {price}")
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
