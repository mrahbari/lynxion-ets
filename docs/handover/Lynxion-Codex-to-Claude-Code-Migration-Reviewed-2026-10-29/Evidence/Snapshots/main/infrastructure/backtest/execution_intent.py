"""
Execution Intent Contract - Formal contract between Strategy → Engine → Backtester.

This module defines the ExecutionIntent class which serves as a formal contract
between the Strategy, Engine, and Backtester layers to enforce execution
responsibility boundaries.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union
from enum import Enum


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class ExecutionIntent:
    """
    Immutable execution intent object that formalizes the contract between
    Strategy → Engine → Backtester layers.

    This ensures that:
    - Strategies may ONLY emit trade intent
    - Engine may accept or reject trade intent
    - Backtester may ONLY execute an accepted trade intent
    """

    # Order identification
    id: str
    timestamp: datetime

    # Core order details
    side: OrderSide
    size: float
    price: float

    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Strategy metadata
    strategy_name: Optional[str] = None
    symbol: Optional[str] = None

    def __post_init__(self):
        """Validate the execution intent after initialization."""
        if self.size <= 0:
            raise ValueError(f"Size must be positive, got {self.size}")

        if self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")

    @property
    def is_valid(self) -> bool:
        """Check if the execution intent is valid."""
        try:
            self.__post_init__()
            return True
        except (ValueError, TypeError):
            return False

    @property
    def risk_amount(self) -> float:
        """Calculate the risk amount based on stop loss if available."""
        if self.stop_loss is not None:
            if self.side == OrderSide.BUY:
                risk_per_unit = max(0.0, self.price - self.stop_loss)
            else:  # SELL
                risk_per_unit = max(0.0, self.stop_loss - self.price)
            return risk_per_unit * self.size
        return 0.0


def create_execution_intent(
    side: Union[OrderSide, str],
    size: float,
    price: float,
    timestamp: datetime,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    strategy_name: Optional[str] = None,
    symbol: Optional[str] = None,
    intent_id: Optional[str] = None
) -> ExecutionIntent:
    """
    Factory function to create an ExecutionIntent with proper validation.

    Args:
        side: Order side (BUY/SELL)
        size: Order size
        price: Order price
        timestamp: Timestamp of the intent
        stop_loss: Optional stop loss price
        take_profit: Optional take profit price
        strategy_name: Name of the strategy that generated the intent
        symbol: Trading symbol
        intent_id: Optional custom ID (auto-generated if not provided)

    Returns:
        ExecutionIntent: A validated execution intent object
    """
    import uuid

    if isinstance(side, str):
        side = OrderSide(side.lower())

    intent_id = intent_id or f"intent_{uuid.uuid4().hex[:8]}"

    return ExecutionIntent(
        id=intent_id,
        timestamp=timestamp,
        side=side,
        size=size,
        price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        strategy_name=strategy_name,
        symbol=symbol
    )