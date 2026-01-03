"""
Domain ports for the enterprise hedge fund trading system following hexagonal architecture.
"""
from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities.signal_entities import MarketObservation, InterpretedSignal, FusedSignal, ExecutionIntent, Order, Position, Balance
from domain.value_objects import Symbol, Money, Percentage


class SignalPort(Protocol):
    """Port for signal generation and processing"""

    @abstractmethod
    def generate_signal(self, symbol: Symbol) -> Optional[InterpretedSignal]:
        """Generate a signal for the given symbol"""
        pass

    @abstractmethod
    def process_signal(self, signal: InterpretedSignal) -> InterpretedSignal:
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
    def process_signal(self, signal: InterpretedSignal) -> InterpretedSignal:
        """Process a signal through the engine"""
        pass

    @abstractmethod
    def should_process_signal(self, signal: InterpretedSignal) -> bool:
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


class ObservationProcessorPort(Protocol):
    """Port for processing raw market observations into interpreted signals"""

    @abstractmethod
    def process_observation(self, observation: MarketObservation) -> Optional[InterpretedSignal]:
        """Process a raw market observation into an interpreted signal"""
        pass


class StrategyPort(Protocol):
    """Port for strategy operations in hexagonal architecture - the ONLY layer that selects strategies"""

    @abstractmethod
    def evaluate_fused_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate a fused signal and return execution intent if strategy accepts it"""
        pass

    @abstractmethod
    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Check if the strategy should execute based on the fused signal"""
        pass

    @abstractmethod
    def select_strategy(self, fused_signal: FusedSignal) -> str:
        """Select the appropriate strategy based on the fused signal and market conditions"""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy"""
        pass

    @abstractmethod
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update strategy with new market data"""
        pass


class FusionPort(Protocol):
    """Port for signal fusion operations"""

    @abstractmethod
    def fuse_signals(self, signals: List[InterpretedSignal]) -> FusedSignal:
        """Fuse multiple interpreted signals into a single fused signal"""
        pass


class RiskGovernorPort(Protocol):
    """Port for risk governance operations"""

    @abstractmethod
    def validate_signal(self, signal: InterpretedSignal) -> bool:
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