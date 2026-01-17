from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from enum import Enum
import re


@dataclass(frozen=True)
class Symbol:
    """Value object representing a trading symbol"""
    value: str

    def __post_init__(self):
        # Validate symbol format (e.g., BTC-USDT, ETHUSDC, AUSDT)
        if not re.match(r'^[A-Z]{1,10}[-A-Z]{0,1}[A-Z]{3,6}$', self.value):
            raise ValueError(f"Invalid symbol format: {self.value}")
    
    def base_asset(self) -> str:
        """Extract base asset (e.g., 'BTC' from 'BTC-USDT')"""
        if "-" in self.value:
            return self.value.split("-")[0]
        # For standard pairs like BTCUSDT, try common quote assets
        quote_assets = ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP', 'USDC']
        for qa in quote_assets:
            if self.value.endswith(qa):
                return self.value[:-len(qa)]
        # If no known quote asset found, assume the first 3-6 characters are base
        return self.value[:3] if len(self.value) > 6 else self.value[:6]
    
    def quote_asset(self) -> str:
        """Extract quote asset (e.g., 'USDT' from 'BTC-USDT')"""
        if "-" in self.value:
            return self.value.split("-")[1]
        quote_assets = ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP', 'USDC']
        for qa in quote_assets:
            if self.value.endswith(qa):
                return qa
        # If no known quote asset found, assume the last 3-6 characters are quote
        return self.value[-3:] if len(self.value) > 6 else self.value[-6:]


@dataclass(frozen=True)
class Money:
    """Value object representing monetary amounts"""
    amount: Decimal
    currency: str

    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
        if not self.currency.isalpha() or len(self.currency) < 3:
            raise ValueError(f"Invalid currency: {self.currency}")
    
    def __add__(self, other):
        if not isinstance(other, Money) or self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other):
        if not isinstance(other, Money) or self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, scalar):
        if not isinstance(scalar, (int, float, Decimal)):
            raise ValueError("Can only multiply by numeric values")
        return Money(self.amount * Decimal(str(scalar)), self.currency)
    
    def __truediv__(self, scalar):
        if not isinstance(scalar, (int, float, Decimal)) or scalar == 0:
            raise ValueError("Can only divide by non-zero numeric values")
        return Money(self.amount / Decimal(str(scalar)), self.currency)
    
    def __str__(self):
        return f"{self.amount:.2f} {self.currency}"


@dataclass(frozen=True)
class Percentage:
    """Value object representing percentage values"""
    value: Decimal

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, 'value', Decimal(str(self.value)))
        if self.value < 0 or self.value > 1:
            raise ValueError(f"Percentage value must be between 0 and 1, got {self.value}")
    
    def to_basis_points(self) -> int:
        """Convert to basis points (0.01% = 1bp)"""
        return int(self.value * 10000)
    
    def to_percentage(self) -> float:
        """Convert to percentage (e.g., 0.10 -> 10.0%)"""
        return float(self.value * 100)
    
    def __str__(self):
        return f"{self.to_percentage():.2f}%"


@dataclass(frozen=True)
class Price:
    """Value object representing price information"""
    value: Decimal
    symbol: Symbol
    timestamp: Optional[int] = None

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, 'value', Decimal(str(self.value)))
        if self.value < 0:
            raise ValueError(f"Price cannot be negative: {self.value}")


@dataclass(frozen=True)
class Volume:
    """Value object representing trading volume"""
    value: Decimal
    symbol: Symbol

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, 'value', Decimal(str(self.value)))
        if self.value < 0:
            raise ValueError(f"Volume cannot be negative: {self.value}")


@dataclass(frozen=True)
class RiskValue:
    """Value object representing risk metrics"""
    value: Decimal
    risk_type: str  # VAR, ES, MaxDrawdown, etc.
    confidence_level: Optional[Percentage] = None

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, 'value', Decimal(str(self.value)))
        if self.value < 0:
            raise ValueError(f"Risk value cannot be negative: {self.value}")
        if self.confidence_level and float(self.confidence_level) > 1:
            raise ValueError(f"Confidence level cannot exceed 100%: {self.confidence_level}")


@dataclass(frozen=True)
class Correlation:
    """Value object representing correlation between assets"""
    value: Decimal
    asset1: Symbol
    asset2: Symbol

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, 'value', Decimal(str(self.value)))
        if abs(self.value) > 1:
            raise ValueError(f"Correlation must be between -1 and 1, got {self.value}")