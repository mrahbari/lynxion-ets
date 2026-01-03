from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from decimal import Decimal
from domain.value_objects import Symbol, Money, Percentage


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NEUTRAL = "NEUTRAL"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class MarketObservation:
    """Domain entity representing raw market observations from Watcher layer.
    Should NOT contain strategy information or trading decisions."""
    symbol: Symbol
    observation_type: str  # e.g., 'volatility_expansion', 'momentum_spike', 'liquidity_imbalance'
    observation_value: float  # raw value of the observation
    confidence: Percentage  # 0.0 to 1.0
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not 0.0 <= float(self.confidence.value) <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class InterpretedSignal:
    """Domain entity representing interpreted signals from Engine layer.
    Contains direction and strength but no strategy selection."""
    symbol: Symbol
    signal_type: SignalType  # Only direction (BUY/SELL/NEUTRAL/HOLD)
    direction: float  # -1.0 to 1.0 (short to long)
    strength: float  # 0.0 to 1.0
    confidence: Percentage  # 0.0 to 1.0
    timestamp: datetime
    source_watcher: Optional[str] = None  # Which watcher generated the observation
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not 0.0 <= float(self.confidence.value) <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if not -1.0 <= self.direction <= 1.0:
            raise ValueError("Direction must be between -1.0 and 1.0")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("Strength must be between 0.0 and 1.0")


@dataclass
class FusedSignal:
    """Domain entity representing fused signals from Fusion layer.
    Contains dominant bias but no strategy selection."""
    symbol: Symbol
    dominant_bias: SignalType
    direction: float  # -1.0 to 1.0 (short to long)
    dominance_score: float  # 0.0 to 1.0
    regime_context: str  # e.g., 'trending', 'volatile', 'normal'
    confidence: Percentage  # 0.0 to 1.0
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not 0.0 <= float(self.confidence.value) <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if not 0.0 <= self.dominance_score <= 1.0:
            raise ValueError("Dominance score must be between 0.0 and 1.0")
        if not -1.0 <= self.direction <= 1.0:
            raise ValueError("Direction must be between -1.0 and 1.0")


@dataclass
class ExecutionIntent:
    """Domain entity representing execution intent from Strategy layer.
    This is where strategy selection occurs."""
    symbol: Symbol
    strategy_name: str  # Strategy selection happens HERE
    side: OrderSide
    intent_confidence: Percentage  # 0.0 to 1.0
    risk_parameters: Dict[str, Any]  # SL, TP, position sizing parameters
    timestamp: datetime
    fused_signal: Optional[FusedSignal] = None  # Reference to the fused signal that triggered this
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not 0.0 <= float(self.intent_confidence.value) <= 1.0:
            raise ValueError("Intent confidence must be between 0.0 and 1.0")


@dataclass
class Order:
    """Domain entity representing a trading order"""
    symbol: Symbol
    side: OrderSide
    quantity: Decimal
    price: Optional[Money] = None
    order_type: str = "MARKET"
    position_side: Optional[PositionSide] = None
    stop_price: Optional[Money] = None
    time_in_force: str = "GTC"
    client_order_id: Optional[str] = None
    strategy_name: Optional[str] = None  # Only set by Strategy layer
    timestamp: Optional[datetime] = None
    parent_execution_intent: Optional[ExecutionIntent] = None  # Reference to the intent that created this order
    risk_adjusted_quantity: Optional[Decimal] = None
    stop_loss_price: Optional[Money] = None
    take_profit_price: Optional[Money] = None

    def is_market_order(self) -> bool:
        return self.order_type.upper() == "MARKET"

    def is_limit_order(self) -> bool:
        return self.order_type.upper() == "LIMIT"


@dataclass
class Fill:
    """Domain entity representing a trade fill"""
    symbol: Symbol
    side: OrderSide
    quantity: Decimal
    price: Money
    timestamp: datetime
    order_id: str
    fee: Money
    fee_currency: str = ""
    trade_id: Optional[str] = None

    def calculate_value(self) -> Money:
        """Calculate the total value of this fill"""
        return Money(self.quantity * self.price.amount, self.price.currency)


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