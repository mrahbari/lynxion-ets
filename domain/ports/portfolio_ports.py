from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities import Position, Portfolio
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

    @abstractmethod
    def calculate_dynamic_size(
        self,
        intent: Any,
        portfolio: Any,
        volatility: Optional[float] = None
    ) -> float:
        """Calculate dynamic position size based on drawdown, correlation, and volatility (NGDP)."""
        pass


class PortfolioOptimizationPort(Protocol):
    """Port for portfolio optimization algorithms"""
    
    @abstractmethod
    def optimize_allocation(self, assets: List[Symbol], constraints: Dict[str, Any]) -> Dict[Symbol, Percentage]:
        """Optimize portfolio allocation based on constraints and objectives"""
        pass


class PositionSizingEnginePort(Protocol):
    """Canonical position-sizing engine: named, pluggable algorithms (E3.T3).

    Distinct from ``PositionSizingPort`` (the risk-governed request interface
    whose adapters return ``0.0`` because the Risk module owns live sizing). This
    port exposes the actual sizing algorithms (kelly, fixed_risk, atr,
    volatility_target, probabilistic) behind a single adapter, preserving each
    formula exactly.
    """

    @abstractmethod
    def compute_size(self, algorithm: str, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float, **kwargs) -> float:
        """Compute a position size (in units) using the named algorithm."""
        pass

    @abstractmethod
    def available_algorithms(self) -> List[str]:
        """Return the list of supported algorithm names."""
        pass