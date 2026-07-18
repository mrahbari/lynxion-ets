"""Immutable domain models for Lynxion-ETS Quantitative Market Data Platform."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from domain.value_objects import Symbol, Price, Side, ExchangeTimestamp, Quantity


@dataclass
class MarketData:
    """Legacy domain entity representing basic market data (preserved for backward compatibility)"""
    symbol: Symbol
    price: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None


@dataclass(frozen=True)
class OrderBookLevel:
    """Immutable domain model for a single price level in the order book."""
    price: Price
    quantity: Quantity

    def __post_init__(self):
        if self.price.value < 0:
            raise ValueError(f"Order book level price cannot be negative: {self.price.value}")
        if self.quantity.value < 0:
            raise ValueError(f"Order book level quantity cannot be negative: {self.quantity.value}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "price": str(self.price.value),
            "quantity": str(self.quantity.value)
        }


@dataclass(frozen=True)
class OrderBookSnapshot:
    """Immutable domain model representing a full L2 Order Book snapshot."""
    symbol: Symbol
    timestamp: ExchangeTimestamp
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    sequence_id: int

    def __post_init__(self):
        if self.sequence_id < 0:
            raise ValueError(f"Sequence ID cannot be negative: {self.sequence_id}")
        
        # Verify bids and asks are matching the snapshot symbol
        for level in self.bids + self.asks:
            if level.price.symbol != self.symbol:
                raise ValueError(f"Level symbol mismatch: expected {self.symbol}, got {level.price.symbol}")

        # Invariant checks for bids/asks crossing
        if self.bids and self.asks:
            best_bid = self.bids[0].price.value
            best_ask = self.asks[0].price.value
            if best_bid >= best_ask:
                raise ValueError(f"Order book is crossed: best bid ({best_bid}) >= best ask ({best_ask})")

        # Verify bids are in descending order
        for i in range(len(self.bids) - 1):
            if self.bids[i].price.value <= self.bids[i+1].price.value:
                raise ValueError("Bids must be ordered in descending price order")

        # Verify asks are in ascending order
        for i in range(len(self.asks) - 1):
            if self.asks[i].price.value >= self.asks[i+1].price.value:
                raise ValueError("Asks must be ordered in ascending price order")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "timestamp": self.timestamp.millis,
            "bids": [b.to_dict() for b in self.bids],
            "asks": [a.to_dict() for a in self.asks],
            "sequence_id": self.sequence_id
        }


@dataclass(frozen=True)
class TradeTick:
    """Immutable domain model representing a single executed public trade."""
    symbol: Symbol
    trade_id: int
    price: Price
    quantity: Quantity
    timestamp: ExchangeTimestamp
    side: Side

    def __post_init__(self):
        if self.trade_id < 0:
            raise ValueError(f"Trade ID cannot be negative: {self.trade_id}")
        if self.price.symbol != self.symbol:
            raise ValueError(f"Price symbol mismatch: expected {self.symbol}, got {self.price.symbol}")
        if not isinstance(self.side, Side):
            raise ValueError(f"Invalid side enum value: {self.side}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "trade_id": self.trade_id,
            "price": str(self.price.value),
            "quantity": str(self.quantity.value),
            "timestamp": self.timestamp.millis,
            "side": self.side.value
        }


@dataclass(frozen=True)
class OpenInterest:
    """Immutable domain model representing open contract positions value."""
    symbol: Symbol
    value: Quantity
    timestamp: ExchangeTimestamp

    def __post_init__(self):
        if self.value.value < 0:
            raise ValueError(f"Open Interest cannot be negative: {self.value.value}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "value": self.value.to_dict(),
            "timestamp": self.timestamp.millis
        }


@dataclass(frozen=True)
class FundingRate:
    """Immutable domain model representing perpetual swap funding rate."""
    symbol: Symbol
    rate: Decimal
    timestamp: ExchangeTimestamp
    next_funding_time: ExchangeTimestamp

    def __post_init__(self):
        if not isinstance(self.rate, Decimal):
            object.__setattr__(self, 'rate', Decimal(str(self.rate)))
        if abs(self.rate) > Decimal("0.05"):
            raise ValueError(f"Funding rate value {self.rate} is implausible (exceeds 5%)")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "rate": str(self.rate),
            "timestamp": self.timestamp.millis,
            "next_funding_time": self.next_funding_time.millis
        }


@dataclass(frozen=True)
class LiquidationEvent:
    """Immutable domain model representing a forced liquidation event."""
    symbol: Symbol
    side: Side
    price: Price
    quantity: Quantity
    timestamp: ExchangeTimestamp

    def __post_init__(self):
        if self.price.symbol != self.symbol:
            raise ValueError(f"Price symbol mismatch: expected {self.symbol}, got {self.price.symbol}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "side": self.side.value,
            "price": str(self.price.value),
            "quantity": str(self.quantity.value),
            "timestamp": self.timestamp.millis
        }


@dataclass(frozen=True)
class MarkPrice:
    """Immutable domain model representing mark price used for margin and liquidation."""
    symbol: Symbol
    price: Price
    timestamp: ExchangeTimestamp

    def __post_init__(self):
        if self.price.symbol != self.symbol:
            raise ValueError(f"Price symbol mismatch: expected {self.symbol}, got {self.price.symbol}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "price": str(self.price.value),
            "timestamp": self.timestamp.millis
        }


@dataclass(frozen=True)
class IndexPrice:
    """Immutable domain model representing index price based on spot component basket."""
    symbol: Symbol
    price: Price
    timestamp: ExchangeTimestamp

    def __post_init__(self):
        if self.price.symbol != self.symbol:
            raise ValueError(f"Price symbol mismatch: expected {self.symbol}, got {self.price.symbol}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "price": str(self.price.value),
            "timestamp": self.timestamp.millis
        }


@dataclass(frozen=True)
class PremiumIndex:
    """Immutable domain model representing perpetual swap premium index."""
    symbol: Symbol
    value: Decimal
    timestamp: ExchangeTimestamp

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, 'value', Decimal(str(self.value)))

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "value": str(self.value),
            "timestamp": self.timestamp.millis
        }


@dataclass(frozen=True)
class MarketState:
    """Immutable domain model representing a composite summary of market variables."""
    symbol: Symbol
    timestamp: ExchangeTimestamp
    mark_price: MarkPrice
    index_price: IndexPrice
    premium_index: PremiumIndex
    open_interest: OpenInterest
    funding_rate: FundingRate

    def __post_init__(self):
        for model in [self.mark_price, self.index_price, self.premium_index, self.open_interest, self.funding_rate]:
            if model.symbol != self.symbol:
                raise ValueError(f"MarketState constituent symbol mismatch: expected {self.symbol}, got {model.symbol}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "timestamp": self.timestamp.millis,
            "mark_price": self.mark_price.to_dict(),
            "index_price": self.index_price.to_dict(),
            "premium_index": self.premium_index.to_dict(),
            "open_interest": self.open_interest.to_dict(),
            "funding_rate": self.funding_rate.to_dict()
        }


@dataclass(frozen=True)
class VolumeProfile:
    """Immutable domain model representing volume profile by price bins."""
    symbol: Symbol
    timestamp: ExchangeTimestamp
    bins: Dict[Decimal, Quantity]
    value_area_high: Price
    value_area_low: Price
    point_of_control: Price

    def __post_init__(self):
        if self.value_area_low.value > self.value_area_high.value:
            raise ValueError(f"Value area low ({self.value_area_low.value}) cannot exceed high ({self.value_area_high.value})")
        if not (self.value_area_low.value <= self.point_of_control.value <= self.value_area_high.value):
            raise ValueError(f"Point of control ({self.point_of_control.value}) must fall within value area [{self.value_area_low.value}, {self.value_area_high.value}]")
        for p, q in self.bins.items():
            if not isinstance(p, Decimal):
                raise ValueError(f"VolumeProfile bin price must be Decimal, got: {type(p)}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        # Order bins by price key for serialization stability
        sorted_bins = {str(k): self.bins[k].to_dict() for k in sorted(self.bins.keys())}
        return {
            "symbol": self.symbol.value,
            "timestamp": self.timestamp.millis,
            "bins": sorted_bins,
            "value_area_high": str(self.value_area_high.value),
            "value_area_low": str(self.value_area_low.value),
            "point_of_control": str(self.point_of_control.value)
        }


@dataclass(frozen=True)
class SessionStatistics:
    """Immutable domain model representing rolling daily or session metrics."""
    symbol: Symbol
    timestamp: ExchangeTimestamp
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Quantity
    vwap: Price

    def __post_init__(self):
        if self.low.value > self.high.value:
            raise ValueError(f"Session low ({self.low.value}) cannot exceed high ({self.high.value})")
        
        # Check boundary ranges
        for p in [self.open, self.close, self.vwap]:
            if not (self.low.value <= p.value <= self.high.value):
                raise ValueError(f"Price {p.value} is outside session range [{self.low.value}, {self.high.value}]")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "timestamp": self.timestamp.millis,
            "open": str(self.open.value),
            "high": str(self.high.value),
            "low": str(self.low.value),
            "close": str(self.close.value),
            "volume": self.volume.to_dict(),
            "vwap": str(self.vwap.value)
        }
