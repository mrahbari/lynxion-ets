"""
Domain ports for the enterprise hedge fund trading system following hexagonal architecture.
"""
from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities.trading_entities import Signal, Order, Position, Balance
from domain.value_objects import Symbol, Money, Percentage


class SignalPort(Protocol):
    """Port for signal generation and processing"""
    
    @abstractmethod
    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal for the given symbol"""
        pass
    
    @abstractmethod
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal and return enhanced signal"""
        pass


class OrderManagementPort(Protocol):
    """Port for order management operations"""
    
    @abstractmethod
    def place_order(self, order: Order) -> str:
        """Place an order and return order ID"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: Symbol) -> bool:
        """Cancel an order by ID and symbol"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str, symbol: Symbol) -> str:
        """Get the status of an order"""
        pass


class MarketDataPort(Protocol):
    """Port for market data operations"""
    
    @abstractmethod
    def get_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for symbol"""
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: Symbol, period: str) -> List[float]:
        """Get historical prices for symbol"""
        pass


class PositionManagementPort(Protocol):
    """Port for position management"""
    
    @abstractmethod
    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get current position for symbol"""
        pass
    
    @abstractmethod
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        pass


class RiskManagementPort(Protocol):
    """Port for risk management operations"""
    
    @abstractmethod
    def validate_order_risk(self, order: Order) -> bool:
        """Validate if an order passes risk checks"""
        pass
    
    @abstractmethod
    def check_portfolio_risk(self) -> bool:
        """Check if portfolio is within risk limits"""
        pass
    
    @abstractmethod
    def get_portfolio_exposure(self) -> Money:
        """Get total portfolio exposure"""
        pass
    
    @abstractmethod
    def is_risk_limit_exceeded(self) -> bool:
        """Check if any risk limits are exceeded"""
        pass


class EnginePort(Protocol):
    """Port for engine operations in hexagonal architecture"""

    @abstractmethod
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through the engine"""
        pass

    @abstractmethod
    def should_process_signal(self, signal: Signal) -> bool:
        """Check if the engine should process this signal"""
        pass

    @abstractmethod
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update the engine with new market data"""
        pass

    @abstractmethod
    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        pass


class StrategyPort(Protocol):
    """Port for strategy operations in hexagonal architecture"""
    
    @abstractmethod
    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal for the given symbol"""
        pass
    
    @abstractmethod
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update strategy with new market data"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: Signal, account_balance: float) -> float:
        """Calculate appropriate position size for a signal"""
        pass


class FusionPort(Protocol):
    """Port for signal fusion operations"""
    
    @abstractmethod
    def fuse_signals(self, signals: List[Signal]) -> Signal:
        """Fuse multiple signals into a single signal"""
        pass


class RiskGovernorPort(Protocol):
    """Port for risk governance operations"""
    
    @abstractmethod
    def validate_signal(self, signal: Signal) -> bool:
        """Validate if a signal passes risk checks"""
        pass
    
    @abstractmethod
    def validate_order(self, order: Order) -> bool:
        """Validate if an order passes risk checks"""
        pass
    
    @abstractmethod
    def check_portfolio_risk(self) -> bool:
        """Check if portfolio risk is within limits"""
        pass
    
    @abstractmethod
    def is_kill_switch_activated(self) -> bool:
        """Check if kill switch should be activated"""
        pass
    
    @abstractmethod
    def get_max_position_size(self, symbol: Symbol) -> float:
        """Get maximum allowed position size for symbol"""
        pass


class BrokerPort(Protocol):
    """Port for broker operations"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the broker"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the broker"""
        pass
    
    @abstractmethod
    def place_order(self, order: Order) -> str:
        """Place an order and return order ID"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: Symbol) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str, symbol: Symbol) -> str:
        """Get order status"""
        pass
    
    @abstractmethod
    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get position for symbol"""
        pass
    
    @abstractmethod
    def get_balance(self, asset: str = None) -> List[Balance]:
        """Get account balance"""
        pass


class DataProviderPort(Protocol):
    """Port for data provider operations"""
    
    @abstractmethod
    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for symbol"""
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical data for symbol"""
        pass
    
    @abstractmethod
    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """Subscribe to real-time market data for symbol"""
        pass