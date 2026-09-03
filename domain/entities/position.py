"""Canonical position-related domain entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
from decimal import Decimal
from domain.value_objects import Symbol, Money, Percentage
from domain.enums.position_side import PositionSide  # canonical enum home; re-exported here


@dataclass
class Position:
    """Domain entity representing an open position"""
    symbol: Symbol
    side: PositionSide
    quantity: Decimal
    entry_price: Money
    timestamp: datetime
    unrealized_pnl: Optional[Money] = None
    realized_pnl: Money = Money(0, "USD")
    margin_used: Optional[Money] = None
    strategy_name: Optional[str] = None
    mark_price: Optional[float] = 0.0
    leverage: Optional[Decimal] = None
    isolated: Optional[bool] = None

    def calculate_unrealized_pnl(self, current_price: Money) -> Money:
        """Calculate unrealized P&L based on current market price"""
        if self.side == PositionSide.LONG:
            pnl_amount = (current_price.amount - self.entry_price.amount) * self.quantity
        elif self.side == PositionSide.SHORT:
            pnl_amount = (self.entry_price.amount - current_price.amount) * self.quantity
        else:  # FLAT
            pnl_amount = 0

        return Money(pnl_amount, current_price.currency)

    def is_open(self) -> bool:
        """Check if the position is currently open"""
        return self.side != PositionSide.FLAT and self.quantity > 0


@dataclass
class Portfolio:
    """Domain entity representing the trading portfolio"""
    positions: List[Position]
    cash_balance: Money
    total_value: Money
    timestamp: datetime
    strategy_weights: Optional[Dict[str, Percentage]] = None

    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get a specific position by symbol"""
        for pos in self.positions:
            if pos.symbol == symbol:
                return pos
        return None

    def calculate_total_exposure(self) -> Money:
        """Calculate total portfolio exposure (sum of absolute position values)"""
        exposure = 0
        for pos in self.positions:
            if pos.quantity > 0 and pos.entry_price.amount > 0:
                exposure += float(pos.quantity) * pos.entry_price.amount
        return Money(exposure, self.total_value.currency)
