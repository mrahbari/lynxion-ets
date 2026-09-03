"""Canonical order/execution domain entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from domain.value_objects import Symbol, Money, Percentage
from domain.entities.position import PositionSide
from domain.entities.signal import Signal, FusedSignal
from domain.enums.order_side import OrderSide  # canonical enum home; re-exported here


@dataclass
class ExecutionIntent:
    """Domain entity representing execution intent from Strategy layer.
    This is where strategy selection occurs."""
    symbol: Symbol
    strategy_name: str  # Strategy selection happens HERE
    side: OrderSide
    intent_confidence: Percentage  # 0.0 to 1.0
    risk_parameters: Dict[str, Any]  # SL, TP, position sizing parameters
    timestamp: datetime
    fused_signal: Optional[FusedSignal] = None  # Reference to the fused signal that triggered this
    metadata: Optional[Dict[str, Any]] = None
    requested_leverage: Optional[Decimal] = None

    def __post_init__(self):
        if not 0.0 <= float(self.intent_confidence.value) <= 1.0:
            raise ValueError("Intent confidence must be between 0.0 and 1.0")


@dataclass
class Order:
    """Domain entity representing a trading order.

    Canonical merge of the two historical ``Order`` definitions: it carries
    both ``parent_signal`` (legacy ``trading_entities``) and
    ``parent_execution_intent`` (legacy ``signal_entities``); both optional.
    """
    symbol: Symbol
    side: OrderSide
    quantity: Decimal
    price: Optional[Money] = None
    order_type: str = "MARKET"
    position_side: Optional[PositionSide] = None
    stop_price: Optional[Money] = None
    time_in_force: str = "GTC"
    client_order_id: Optional[str] = None
    strategy_name: Optional[str] = None  # Only set by Strategy layer
    timestamp: Optional[datetime] = None
    parent_signal: Optional[Signal] = None  # Reference to the signal that created this order
    parent_execution_intent: Optional[ExecutionIntent] = None  # Reference to the intent that created this order
    risk_adjusted_quantity: Optional[Decimal] = None
    stop_loss_price: Optional[Money] = None
    take_profit_price: Optional[Money] = None
    requested_leverage: Optional[Decimal] = None

    def is_market_order(self) -> bool:
        return self.order_type.upper() == "MARKET"

    def is_limit_order(self) -> bool:
        return self.order_type.upper() == "LIMIT"


@dataclass
class Fill:
    """Domain entity representing a trade fill"""
    symbol: Symbol
    side: OrderSide
    quantity: Decimal
    price: Money
    timestamp: datetime
    order_id: str
    fee: Money
    fee_currency: str = ""
    trade_id: Optional[str] = None

    def calculate_value(self) -> Money:
        """Calculate the total value of this fill"""
        return Money(self.quantity * self.price.amount, self.price.currency)
