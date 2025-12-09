from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    OCO = "OCO"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"

@dataclass
class MarketData:
    symbol: str
    price: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None

@dataclass
class Signal:
    symbol: str
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    score: float  # -1.0 to 1.0
    strategy: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"
    client_order_id: Optional[str] = None
    strategy: Optional[str] = None

@dataclass
class Fill:
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    order_id: str
    fee: float = 0.0
    fee_currency: str = ""

@dataclass
class Position:
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    unrealized_pnl: float
    timestamp: datetime

@dataclass
class Balance:
    asset: str
    total: float
    available: float
    reserved: float
    timestamp: datetime