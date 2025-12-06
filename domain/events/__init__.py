from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from domain.entities.trading_entities import Signal, Order, Position
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


@dataclass
class DomainEvent:
    """Base domain event"""
    event_type: EventType
    timestamp: datetime
    source: str  # Who generated the event
    data: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None  # For tracking related events


@dataclass
class SignalGeneratedEvent(DomainEvent):
    """Event raised when a signal is generated"""
    signal: Signal

    def __post_init__(self):
        self.event_type = EventType.SIGNAL_GENERATED


@dataclass
class OrderPlacedEvent(DomainEvent):
    """Event raised when an order is placed"""
    order: Order

    def __post_init__(self):
        self.event_type = EventType.ORDER_PLACED


@dataclass
class OrderFilledEvent(DomainEvent):
    """Event raised when an order is filled"""
    order: Order
    fill_amount: float
    fill_price: float
    
    def __post_init__(self):
        self.event_type = EventType.ORDER_FILLED


@dataclass
class PositionOpenedEvent(DomainEvent):
    """Event raised when a position is opened"""
    position: Position

    def __post_init__(self):
        self.event_type = EventType.POSITION_OPENED


@dataclass
class PositionClosedEvent(DomainEvent):
    """Event raised when a position is closed"""
    position: Position
    pnl: Money

    def __post_init__(self):
        self.event_type = EventType.POSITION_CLOSED


@dataclass
class RiskViolationEvent(DomainEvent):
    """Event raised when a risk limit is violated"""
    risk_type: str
    asset: Optional[Symbol] = None
    violation_details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.event_type = EventType.RISK_VIOLATION


@dataclass
class PortfolioRebalancedEvent(DomainEvent):
    """Event raised when portfolio is rebalanced"""
    old_positions: List[Position]
    new_positions: List[Position]
    rebalance_reason: str

    def __post_init__(self):
        self.event_type = EventType.PORTFOLIO_REBALANCED


@dataclass
class StrategyChangedEvent(DomainEvent):
    """Event raised when active strategy changes"""
    old_strategy: str
    new_strategy: str
    reason: str

    def __post_init__(self):
        self.event_type = EventType.STRATEGY_CHANGED