"""Canonical account-related domain entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
from domain.value_objects import Money
from domain.entities.position import Position


@dataclass
class Balance:
    """Domain entity representing an account balance"""
    asset: str
    total: Decimal
    available: Decimal
    reserved: Decimal
    timestamp: datetime

    def to_money(self) -> Money:
        """Convert balance to Money value object"""
        return Money(self.total, self.asset)


@dataclass
class TradingAccount:
    """Domain entity representing a trading account"""
    account_id: str
    broker_name: str
    account_type: str
    balances: Dict[str, Money]  # asset -> balance
    positions: List[Position]
    created_at: datetime
    is_active: bool = True
    leverage: float = 1.0
    trading_limits: Optional[Dict[str, Any]] = None

    def get_balance(self, asset: str) -> Money:
        """Get balance for a specific asset"""
        return self.balances.get(asset, Money(0, asset))
