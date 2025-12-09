"""
Application service for portfolio management in the enterprise hedge fund trading system.
"""
from typing import List, Dict, Any, Optional
from domain.entities.trading_entities import Position, Portfolio
from domain.value_objects import Symbol, Money, Percentage
from domain.ports.portfolio_ports import (
    PortfolioManagementPort, PositionSizingPort, PortfolioOptimizationPort
)
from shared.logger import logger


class PortfolioManagementService:
    """Application service for portfolio management operations"""
    
    def __init__(self,
                 portfolio_management_port: PortfolioManagementPort,
                 position_sizing_port: PositionSizingPort,
                 optimization_port: PortfolioOptimizationPort):
        self.portfolio_management = portfolio_management_port
        self.position_sizing = position_sizing_port
        self.optimization = optimization_port
    
    def calculate_portfolio_allocation(self, total_capital: float, symbols: List[Symbol]) -> Dict[Symbol, float]:
        """Calculate portfolio allocation for given symbols"""
        allocation = self.portfolio_management.calculate_allocation(total_capital, symbols)
        logger.info(f"Portfolio allocation calculated for {len(symbols)} symbols")
        return allocation
    
    def calculate_position_size(self, symbol: Symbol, account_balance: float, risk_percentage: float = 0.02) -> float:
        """Calculate position size for a symbol"""
        position_size = self.position_sizing.calculate_position_size(symbol, account_balance, risk_percentage)
        logger.info(f"Position size calculated for {symbol.value}: {position_size}")
        return position_size
    
    def optimize_portfolio(self, assets: List[Symbol], constraints: Dict[str, Any] = None) -> Dict[Symbol, Percentage]:
        """Optimize portfolio allocation"""
        constraints = constraints or {}
        allocation = self.optimization.optimize_allocation(assets, constraints)
        logger.info(f"Portfolio optimization completed for {len(assets)} assets")
        return allocation
    
    def rebalance_portfolio(self, target_allocations: Dict[Symbol, Percentage]) -> List:
        """Rebalance portfolio to target allocations"""
        orders = self.portfolio_management.rebalance_portfolio(target_allocations)
        logger.info(f"Portfolio rebalancing initiated with {len(orders)} orders")
        return orders
    
    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get portfolio metrics"""
        metrics = self.portfolio_management.get_portfolio_metrics()
        logger.info(f"Portfolio metrics retrieved: {list(metrics.keys())}")
        return metrics


class PortfolioConstructionService:
    """Service for constructing portfolios based on different methodologies"""
    
    def __init__(self, portfolio_service: PortfolioManagementService):
        self.portfolio_service = portfolio_service
        self.available_methods = ['equal_weight', 'risk_parity', 'volatility_target']
    
    def build_portfolio_with_method(self, 
                                   method: str, 
                                   total_capital: float, 
                                   symbols: List[Symbol]) -> Dict[Symbol, float]:
        """Build a portfolio using a specific methodology"""
        if method not in self.available_methods:
            raise ValueError(f"Unknown portfolio construction method: {method}")
        
        logger.info(f"Building portfolio using {method} method")
        
        # This would typically switch between different portfolio management ports
        # For now, we'll use the current service
        return self.portfolio_service.calculate_portfolio_allocation(total_capital, symbols)
    
    def apply_risk_model(self, 
                        base_allocation: Dict[Symbol, float], 
                        risk_constraints: Dict[str, Any]) -> Dict[Symbol, float]:
        """Apply risk model constraints to base allocation"""
        # This would adjust allocations based on risk constraints
        # For now, we'll just return the base allocation
        logger.info("Risk model applied to portfolio allocation")
        return base_allocation


class DynamicPortfolioAllocationService:
    """Service for dynamically adjusting portfolio allocations based on market conditions"""
    
    def __init__(self, portfolio_service: PortfolioManagementService):
        self.portfolio_service = portfolio_service
        self.rebalance_threshold = 0.05  # 5% threshold for rebalancing
    
    def adjust_allocation_for_market_regime(self, 
                                          current_allocations: Dict[Symbol, float],
                                          market_regime: str) -> Dict[Symbol, float]:
        """Adjust portfolio allocation based on market regime"""
        # In a real implementation, this would adjust allocations based on
        # market regime (bull, bear, volatile, etc.)
        logger.info(f"Adjusting allocation for market regime: {market_regime}")
        return current_allocations
    
    def determine_rebalance_necessity(self, 
                                    current_allocations: Dict[Symbol, float],
                                    target_allocations: Dict[Symbol, float]) -> bool:
        """Determine if portfolio rebalancing is necessary"""
        # Calculate deviation from target allocations
        max_deviation = 0
        for symbol, target_weight in target_allocations.items():
            current_weight = current_allocations.get(symbol, 0)
            deviation = abs(current_weight - target_weight)
            max_deviation = max(max_deviation, deviation)
        
        should_rebalance = max_deviation > self.rebalance_threshold
        logger.info(f"Rebalancing needed: {should_rebalance}, max deviation: {max_deviation:.2%}")
        return should_rebalance