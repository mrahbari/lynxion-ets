"""Canonical market-data domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from domain.value_objects import Symbol


@dataclass
class MarketData:
    """Domain entity representing market data"""
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
