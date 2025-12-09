"""
Use cases for portfolio management functionality in the enterprise hedge fund trading system.
"""
from typing import List, Dict, Any
from domain.value_objects import Symbol, Money, Percentage
from application.services.portfolio_services import PortfolioManagementService


class CalculatePortfolioAllocationUseCase:
    """Use case for calculating portfolio allocation"""
    
    def __init__(self, portfolio_management_service: PortfolioManagementService):
        self.portfolio_management_service = portfolio_management_service
    
    def execute(self, total_capital: float, symbols: List[Symbol]) -> Dict[Symbol, float]:
        """Execute the use case to calculate portfolio allocation"""
        return self.portfolio_management_service.calculate_portfolio_allocation(total_capital, symbols)


class CalculatePositionSizeUseCase:
    """Use case for calculating position size"""
    
    def __init__(self, portfolio_management_service: PortfolioManagementService):
        self.portfolio_management_service = portfolio_management_service
    
    def execute(self, symbol: Symbol, account_balance: float, risk_percentage: float = 0.02) -> float:
        """Execute the use case to calculate position size"""
        return self.portfolio_management_service.calculate_position_size(symbol, account_balance, risk_percentage)


class OptimizePortfolioUseCase:
    """Use case for optimizing portfolio allocation"""
    
    def __init__(self, portfolio_management_service: PortfolioManagementService):
        self.portfolio_management_service = portfolio_management_service
    
    def execute(self, assets: List[Symbol], constraints: Dict[str, Any] = None) -> Dict[Symbol, Percentage]:
        """Execute the use case to optimize portfolio"""
        return self.portfolio_management_service.optimize_portfolio(assets, constraints)


class RebalancePortfolioUseCase:
    """Use case for rebalancing portfolio"""
    
    def __init__(self, portfolio_management_service: PortfolioManagementService):
        self.portfolio_management_service = portfolio_management_service
    
    def execute(self, target_allocations: Dict[Symbol, Percentage]) -> List:
        """Execute the use case to rebalance portfolio"""
        return self.portfolio_management_service.rebalance_portfolio(target_allocations)


class GetPortfolioMetricsUseCase:
    """Use case for getting portfolio metrics"""
    
    def __init__(self, portfolio_management_service: PortfolioManagementService):
        self.portfolio_management_service = portfolio_management_service
    
    def execute(self) -> Dict[str, Any]:
        """Execute the use case to get portfolio metrics"""
        return self.portfolio_management_service.get_portfolio_metrics()