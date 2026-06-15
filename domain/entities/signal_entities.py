"""Backward-compatibility shim (E4.T1).

The canonical entity definitions now live in the split modules under
``domain.entities`` (``signal``, ``order``, ``position``, ``market_data``,
``account``). This module re-exports them so existing
``from domain.entities import ...`` imports keep working
unchanged. It is removed in E4.T2 once importers are migrated.
"""

from domain.entities.signal import (
    SignalType,
    Signal,
    MarketObservation,
    InterpretedSignal,
    FusedSignal,
)
from domain.entities.order import OrderSide, Order, Fill, ExecutionIntent
from domain.entities.position import PositionSide, Position, Portfolio
from domain.entities.market_data import MarketData
from domain.entities.account import Balance, TradingAccount

__all__ = [
    "SignalType",
    "OrderSide",
    "PositionSide",
    "MarketObservation",
    "InterpretedSignal",
    "FusedSignal",
    "ExecutionIntent",
    "Order",
    "Fill",
    "Position",
    "Portfolio",
    "MarketData",
    "Balance",
    "TradingAccount",
]
