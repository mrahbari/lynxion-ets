from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities.trading_entities import Position, Portfolio
from domain.value_objects import Symbol, Money, Percentage


class PortfolioManagementPort(Protocol):
    """Port for portfolio management operations"""
    
    @abstractmethod
    def calculate_allocation(self, total_capital: float, symbols: List[Symbol]) -> Dict[Symbol, float]:
        """Calculate allocation for each symbol in the portfolio"""
        pass
    
    @abstractmethod
    def rebalance_portfolio(self, target_allocations: Dict[Symbol, Percentage]) -> List:
        """Rebalance the portfolio to target allocations"""
        pass
    
    @abstractmethod
    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get portfolio performance and risk metrics"""
        pass


class PositionSizingPort(Protocol):
    """Port for position sizing calculations"""
    
    @abstractmethod
    def calculate_position_size(self, symbol: Symbol, account_balance: float, risk_percentage: float) -> float:
        """Calculate appropriate position size based on risk parameters"""
        pass


class PortfolioOptimizationPort(Protocol):
    """Port for portfolio optimization algorithms"""
    
    @abstractmethod
    def optimize_allocation(self, assets: List[Symbol], constraints: Dict[str, Any]) -> Dict[Symbol, Percentage]:
        """Optimize portfolio allocation based on constraints and objectives"""
        pass