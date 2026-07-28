from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any


class Side(Enum):
    """Execution order side (BUY/SELL)"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type for execution modeling"""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"


class LiquidityType(Enum):
    """Liquidity classification for fee modeling"""
    MAKER = "MAKER"
    TAKER = "TAKER"


@dataclass(frozen=True)
class ExchangeTimestamp:
    """Immutable value object representing exchange epoch time in milliseconds."""
    millis: int

    def __post_init__(self):
        if not isinstance(self.millis, int) or self.millis <= 0:
            raise ValueError(f"Exchange timestamp must be a positive integer, got: {self.millis}")

    def to_datetime(self) -> datetime:
        """Convert timestamp to timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.millis / 1000.0, tz=timezone.utc)

    def to_millis(self) -> int:
        """Return the raw millisecond representation."""
        return self.millis

    def __lt__(self, other: 'ExchangeTimestamp') -> bool:
        if not isinstance(other, ExchangeTimestamp):
            return NotImplemented
        return self.millis < other.millis

    def __le__(self, other: 'ExchangeTimestamp') -> bool:
        if not isinstance(other, ExchangeTimestamp):
            return NotImplemented
        return self.millis <= other.millis

    def __gt__(self, other: 'ExchangeTimestamp') -> bool:
        if not isinstance(other, ExchangeTimestamp):
            return NotImplemented
        return self.millis > other.millis

    def __ge__(self, other: 'ExchangeTimestamp') -> bool:
        if not isinstance(other, ExchangeTimestamp):
            return NotImplemented
        return self.millis >= other.millis


@dataclass(frozen=True)
class Quantity:
    """Immutable value object representing asset quantity."""
    value: Decimal
    unit: str

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, 'value', Decimal(str(self.value)))
        if self.value < 0:
            raise ValueError(f"Quantity value cannot be negative: {self.value}")
        if not self.unit or not self.unit.strip():
            raise ValueError("Quantity unit cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "value": str(self.value),
            "unit": self.unit
        }
