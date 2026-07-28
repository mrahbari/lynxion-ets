from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from domain.entities import (
    Signal,
    Order,
    Position,
    OrderBookSnapshot,
    TradeTick,
    OpenInterest,
    FundingRate,
    LiquidationEvent,
)
from domain.value_objects import Symbol, Money


class EventType(Enum):
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    RISK_VIOLATION = "RISK_VIOLATION"
    PORTFOLIO_REBALANCED = "PORTFOLIO_REBALANCED"
    STRATEGY_CHANGED = "STRATEGY_CHANGED"
    ORDER_BOOK_UPDATED = "ORDER_BOOK_UPDATED"
    TRADE_RECEIVED = "TRADE_RECEIVED"
    OPEN_INTEREST_UPDATED = "OPEN_INTEREST_UPDATED"
    FUNDING_UPDATED = "FUNDING_UPDATED"
    LIQUIDATION_DETECTED = "LIQUIDATION_DETECTED"
    FEATURE_GENERATED = "FEATURE_GENERATED"


@dataclass(kw_only=True)
class DomainEvent:
    """Base domain event"""
    event_type: EventType
    timestamp: datetime
    source: str  # Who generated the event
    data: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None  # For tracking related events


@dataclass(kw_only=True)
class SignalGeneratedEvent(DomainEvent):
    """Event raised when a signal is generated"""
    signal: Signal

    def __post_init__(self):
        self.event_type = EventType.SIGNAL_GENERATED


@dataclass(kw_only=True)
class OrderPlacedEvent(DomainEvent):
    """Event raised when an order is placed"""
    order: Order

    def __post_init__(self):
        self.event_type = EventType.ORDER_PLACED


@dataclass(kw_only=True)
class OrderFilledEvent(DomainEvent):
    """Event raised when an order is filled"""
    order: Order
    fill_amount: float
    fill_price: float
    
    def __post_init__(self):
        self.event_type = EventType.ORDER_FILLED


@dataclass(kw_only=True)
class PositionOpenedEvent(DomainEvent):
    """Event raised when a position is opened"""
    position: Position

    def __post_init__(self):
        self.event_type = EventType.POSITION_OPENED


@dataclass(kw_only=True)
class PositionClosedEvent(DomainEvent):
    """Event raised when a position is closed"""
    position: Position
    pnl: Money

    def __post_init__(self):
        self.event_type = EventType.POSITION_CLOSED


@dataclass(kw_only=True)
class RiskViolationEvent(DomainEvent):
    """Event raised when a risk limit is violated"""
    risk_type: str
    asset: Optional[Symbol] = None
    violation_details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.event_type = EventType.RISK_VIOLATION


@dataclass(kw_only=True)
class PortfolioRebalancedEvent(DomainEvent):
    """Event raised when portfolio is rebalanced"""
    old_positions: List[Position]
    new_positions: List[Position]
    rebalance_reason: str

    def __post_init__(self):
        self.event_type = EventType.PORTFOLIO_REBALANCED


@dataclass(kw_only=True)
class StrategyChangedEvent(DomainEvent):
    """Event raised when active strategy changes"""
    old_strategy: str
    new_strategy: str
    reason: str

    def __post_init__(self):
        self.event_type = EventType.STRATEGY_CHANGED


@dataclass(kw_only=True)
class OrderBookUpdatedEvent(DomainEvent):
    """Event raised when an order book snapshot is received or built"""
    snapshot: OrderBookSnapshot

    def __post_init__(self):
        self.event_type = EventType.ORDER_BOOK_UPDATED


@dataclass(kw_only=True)
class TradeReceivedEvent(DomainEvent):
    """Event raised when a public trade tick is received"""
    tick: TradeTick

    def __post_init__(self):
        self.event_type = EventType.TRADE_RECEIVED


@dataclass(kw_only=True)
class OpenInterestUpdatedEvent(DomainEvent):
    """Event raised when open interest data is updated"""
    open_interest: OpenInterest

    def __post_init__(self):
        self.event_type = EventType.OPEN_INTEREST_UPDATED


@dataclass(kw_only=True)
class FundingUpdatedEvent(DomainEvent):
    """Event raised when funding rate information is updated"""
    funding_rate: FundingRate

    def __post_init__(self):
        self.event_type = EventType.FUNDING_UPDATED


@dataclass(kw_only=True)
class LiquidationDetectedEvent(DomainEvent):
    """Event raised when a forced liquidation is detected"""
    event: LiquidationEvent

    def __post_init__(self):
        self.event_type = EventType.LIQUIDATION_DETECTED


@dataclass(kw_only=True)
class FeatureGeneratedEvent(DomainEvent):
    """Event raised when a derived feature is generated"""
    feature_name: str
    feature_value: Any
    symbol: Symbol

    def __post_init__(self):
        self.event_type = EventType.FEATURE_GENERATED