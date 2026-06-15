"""Canonical ``SignalType`` enum (single home for the trading system)."""
from enum import Enum


class SignalType(Enum):
    """Direction/type of a trading signal."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NEUTRAL = "NEUTRAL"
