"""Canonical ``OrderSide`` enum (single home for the trading system)."""
from enum import Enum


class OrderSide(Enum):
    """Side of an order."""
    BUY = "BUY"
    SELL = "SELL"
