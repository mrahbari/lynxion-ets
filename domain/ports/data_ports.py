from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities.trading_entities import MarketData
from domain.value_objects import Symbol


class DataProviderPort(Protocol):
    """Port for data provider operations"""
    
    @abstractmethod
    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for a symbol"""
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical data for a symbol"""
        pass
    
    @abstractmethod
    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """Subscribe to real-time market data for a symbol"""
        pass
    
    @abstractmethod
    def unsubscribe_from_market_data(self, subscription_id: str):
        """Unsubscribe from real-time market data"""
        pass


class DataCachePort(Protocol):
    """Port for data caching operations"""
    
    @abstractmethod
    def store_data(self, key: str, data: Any, ttl: int = 3600):
        """Store data in cache with TTL"""
        pass
    
    @abstractmethod
    def retrieve_data(self, key: str) -> Optional[Any]:
        """Retrieve data from cache"""
        pass


class DataAggregatorPort(Protocol):
    """Port for data aggregation operations"""
    
    @abstractmethod
    def aggregate_data(self, sources: List[str], symbols: List[Symbol]) -> Dict[Symbol, Any]:
        """Aggregate data from multiple sources"""
        pass