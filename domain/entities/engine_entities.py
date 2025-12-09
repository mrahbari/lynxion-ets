"""
Domain entities for engine operations in the enterprise hedge fund trading system.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from decimal import Decimal


@dataclass
class EngineResult:
    """
    Domain entity representing the result of an engine computation.
    This is used by analysis engines that process raw market data and return
    a score and signal that can later be converted to trading signals.
    """
    score: float  # Numeric score between 0.0 and 1.0, where 0.5 is neutral
    signal: str   # Signal type, typically 'long', 'short', or 'none'
    metadata: Optional[Dict[str, Any]] = None  # Additional information from the engine

    def __post_init__(self):
        """Validate the engine result after initialization"""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Score must be between 0.0 and 1.0")
        if self.signal not in ['long', 'short', 'none', 'buy', 'sell', 'hold']:
            raise ValueError(f"Signal must be one of: long, short, none, buy, sell, hold. Got: {self.signal}")

    @property
    def is_bullish(self) -> bool:
        """Check if the result indicates a bullish signal"""
        return self.signal in ['long', 'buy']

    @property
    def is_bearish(self) -> bool:
        """Check if the result indicates a bearish signal"""
        return self.signal in ['short', 'sell']

    @property
    def is_neutral(self) -> bool:
        """Check if the result indicates a neutral signal"""
        return self.signal in ['none', 'hold']

    @property
    def confidence(self) -> float:
        """Calculate normalized confidence from the score (distance from 0.5)"""
        return abs(self.score - 0.5) * 2  # Range 0.0 to 1.0