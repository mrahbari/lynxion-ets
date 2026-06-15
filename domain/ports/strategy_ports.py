"""
Domain ports for the Strategy layer in the enterprise hedge fund trading system.
Following hexagonal architecture principles.
"""
from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities import FusedSignal, ExecutionIntent
from domain.value_objects import Symbol


class StrategyPort(Protocol):
    """Port for strategy operations in hexagonal architecture"""

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


class StrategyManagerPort(Protocol):
    """Port for managing multiple strategies"""

    @abstractmethod
    def evaluate_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate a fused signal across all available strategies"""
        pass

    @abstractmethod
    def get_active_strategies(self) -> List[str]:
        """Get list of active strategy names"""
        pass

    @abstractmethod
    def add_strategy(self, strategy: StrategyPort):
        """Add a strategy to the manager"""
        pass