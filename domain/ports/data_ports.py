from abc import abstractmethod
from datetime import datetime
from typing import Protocol, List, Optional, Dict, Any
from domain.entities import MarketData, TradeTick, OrderBookSnapshot, ReplayEvent, ReplayCheckpoint
from domain.value_objects import Symbol, ExchangeVenue


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


class MarketDataCollectorPort(Protocol):
    """Port for collecting real-time market data from external streams."""

    @abstractmethod
    def start_collecting(self, symbols: List[Symbol], callbacks: Dict[str, Any]) -> None:
        """Start real-time collection for specified symbols and register event callbacks."""
        pass

    @abstractmethod
    def stop_collecting(self) -> None:
        """Stop all active real-time data streams and disconnect connections."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if collector has active stream connections, False otherwise."""
        pass


from domain.entities.market_data import TradeTick, OrderBookSnapshot, MarketState


class MarketDataStoragePort(Protocol):
    """Port for time-series persistence of market data."""

    @abstractmethod
    def store_trade_tick(self, tick: TradeTick) -> None:
        """Persist a single trade tick to storage."""
        pass

    @abstractmethod
    def store_order_book_snapshot(self, snapshot: OrderBookSnapshot) -> None:
        """Persist an L2 order book snapshot to storage."""
        pass

    @abstractmethod
    def store_market_state(self, state: MarketState) -> None:
        """Persist a composite market state to storage."""
        pass

    @abstractmethod
    def retrieve_trade_ticks(self, symbol: Symbol, start: datetime, end: datetime) -> List[TradeTick]:
        """Retrieve historical trade ticks for a given symbol and time range."""
        pass

    @abstractmethod
    def retrieve_order_book_snapshots(self, symbol: Symbol, start: datetime, end: datetime) -> List[OrderBookSnapshot]:
        """Retrieve historical L2 order book snapshots for a given symbol and time range."""
        pass


class FeatureGeneratorPort(Protocol):
    """Port for computing quantitative features from raw market data streams."""

    @abstractmethod
    def generate_features(self, symbol: Symbol, start: datetime, end: datetime) -> Dict[str, Any]:
        """Generate derived features over a historical window."""
        pass

    @abstractmethod
    def update_feature_online(self, symbol: Symbol, new_data: Any) -> Dict[str, Any]:
        """Update feature metrics incrementally in real-time as new ticks or order book levels arrive."""
        pass


class ReplayEnginePort(Protocol):
    """Port for running deterministic historical data replay in backtests."""

    @abstractmethod
    def load_replay_data(self, symbols: List[Symbol], start: datetime, end: datetime) -> None:
        """Pre-load or configure historical datasets to replay."""
        pass

    @abstractmethod
    def next_tick(self) -> Optional[Any]:
        """Fetch the next chronological market event for playback."""
        pass

    @abstractmethod
    def set_replay_speed(self, speed_factor: float) -> None:
        """Adjust playback execution speed factor (for visualization or load testing)."""
        pass

    @abstractmethod
    def load_events(self, events: List[ReplayEvent]) -> None:
        """Load a sequence of ReplayEvents into the playback engine."""
        pass

    @abstractmethod
    def process_next_event(self) -> Optional[ReplayEvent]:
        """Process the next sequential ReplayEvent and advance the pointer."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """Pause playback execution."""
        pass

    @abstractmethod
    def resume(self) -> None:
        """Resume playback execution."""
        pass

    @abstractmethod
    def create_checkpoint(self) -> ReplayCheckpoint:
        """Capture the current builder order book states and stream position."""
        pass

    @abstractmethod
    def restore_checkpoint(self, checkpoint: ReplayCheckpoint) -> None:
        """Restore all order books and stream position back to a checkpoint."""
        pass

    @abstractmethod
    def is_paused(self) -> bool:
        """Return True if the engine execution is currently paused."""
        pass


class DataValidationPort(Protocol):
    """Port for validating data schema, range constraints, and structural integrity."""

    @abstractmethod
    def validate_tick(self, tick: Dict[str, Any]) -> bool:
        """Validate raw incoming trade tick dictionary against schema and logic rules."""
        pass

    @abstractmethod
    def validate_order_book(self, ob: Dict[str, Any]) -> bool:
        """Validate raw order book data dictionary against schema and consistency rules."""
        pass


class MarketDataNormalizerPort(Protocol):
    """Port for normalizing raw venue messages into canonical domain events or entities."""

    @abstractmethod
    def normalize_trade(self, raw_message: Dict[str, Any], venue: ExchangeVenue) -> TradeTick:
        """Normalize exchange-specific trade message into a canonical TradeTick."""
        pass

    @abstractmethod
    def normalize_order_book(self, raw_message: Dict[str, Any], venue: ExchangeVenue) -> OrderBookSnapshot:
        """Normalize exchange-specific order book snapshot/update into a canonical OrderBookSnapshot."""
        pass

    @abstractmethod
    def normalize_symbol(self, raw_symbol: str, venue: ExchangeVenue) -> Symbol:
        """Translate exchange-specific symbol into a canonical Symbol."""
        pass


from domain.entities.market_data import FundingRate, OpenInterest


class DerivativesDataDownloaderPort(Protocol):
    """Port for downloading historical derivatives data (Funding Rates and Open Interest)."""

    @abstractmethod
    async def fetch_funding_rates(
        self,
        symbol: Symbol,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[FundingRate]:
        """Fetch historical funding rates from exchange REST API."""
        pass

    @abstractmethod
    async def fetch_open_interest_history(
        self,
        symbol: Symbol,
        period: str = "1h",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OpenInterest]:
        """Fetch historical Open Interest series from exchange REST API."""
        pass