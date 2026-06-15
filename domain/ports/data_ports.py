from abc import abstractmethod
from datetime import datetime
from typing import Protocol, List, Optional, Dict, Any
from domain.entities import MarketData
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


class DataIntegrityPort(Protocol):
    """Port for market-data integrity validation (E3.T10, gap-closure F5).

    Validates data quality (missing-candle ratios) before backtesting and
    produces integrity reports. The canonical adapter lives at
    ``infrastructure/data/integrity/data_integrity_checker.py``; integrity-report
    fields and the pass/fail threshold are preserved exactly. ``df`` / ``data_dict``
    carry tabular market data (typed ``Any`` to keep domain contracts pandas-free).
    """

    @abstractmethod
    def calculate_missing_candle_ratio(self, df: Any, start_time: datetime, end_time: datetime,
                                       timeframe: str = "1d") -> float:
        """Return the ratio (0.0–1.0) of missing candles in ``df``."""
        pass

    @abstractmethod
    def validate_symbol_data(self, df: Any, symbol: str, start_time: datetime, end_time: datetime,
                             timeframe: str = "1d", max_missing_ratio: float = 0.05) -> bool:
        """Return True iff ``symbol`` data meets the missing-ratio threshold."""
        pass

    @abstractmethod
    def validate_multiple_symbols(self, data_dict: Dict[str, Any], symbols: List[str],
                                  start_time: datetime, end_time: datetime, timeframe: str = "1d",
                                  max_missing_ratio: float = 0.05) -> Dict[str, bool]:
        """Validate several symbols; return ``{symbol: passed}``."""
        pass

    @abstractmethod
    def generate_integrity_report(self, data_dict: Dict[str, Any], symbols: List[str],
                                  start_time: datetime, end_time: datetime,
                                  timeframe: str = "1d") -> Dict[str, Any]:
        """Return a comprehensive data-integrity report."""
        pass