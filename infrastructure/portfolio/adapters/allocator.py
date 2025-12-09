from typing import Dict, List, Optional
from shared.types import Position, Balance, Order
from shared.logger import logger
from datetime import datetime
import numpy as np
import pandas as pd


class PortfolioAllocator:
    """Manages portfolio allocation across assets using various strategies"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Allocation parameters
        self.initial_capital = config.get('initial_capital', 100000)
        self.risk_free_rate = config.get('risk_free_rate', 0.02)  # 2% risk-free rate
        self.max_position_size = config.get('max_position_size', 0.1)  # Max 10% per position
        self.min_position_size = config.get('min_position_size', 0.001)  # Min 0.1% per position
        self.rebalance_threshold = config.get('rebalance_threshold', 0.05)  # Rebalance when allocation deviates by 5%
        self.max_correlation = config.get('max_correlation', 0.7)  # Max correlation between positions
        
        # Current state
        self.current_positions: Dict[str, Position] = {}
        self.current_balances: Dict[str, Balance] = {}
        self.historical_allocations = []
        self.total_value = self.initial_capital
        
        # Allocation strategies
        self.allocation_strategies = {
            'equal_weight': self.equal_weight_allocation,
            'market_cap_weighted': self.market_cap_weighted_allocation,
            'risk_parity': self.risk_parity_allocation,
            'vol_target': self.volatility_targeting_allocation,
            'max_diversification': self.max_diversification_allocation
        }
        
        # Asset characteristics (to be updated with market data)
        self.asset_volatilities = {}
        self.asset_correlations = {}
        self.asset_exposures = {}  # Sector, industry, factor exposures
    
    def update_market_data(self, market_data: Dict[str, Dict]):
        """Update market data for assets"""
        for symbol, data in market_data.items():
            if 'volatility' in data:
                self.asset_volatilities[symbol] = data['volatility']
            if 'correlation' in data:
                self.asset_correlations[symbol] = data['correlation']
    
    def update_positions(self, positions: List[Position]):
        """Update current positions"""
        self.current_positions = {pos.symbol: pos for pos in positions}
        
        # Update total portfolio value
        self.total_value = sum(
            pos.quantity * pos.entry_price for pos in self.current_positions.values()
        )
    
    def update_balance(self, balance: Balance):
        """Update cash balance"""
        self.current_balances[balance.asset] = balance
        if balance.asset.upper() in ['USD', 'USDT', 'CASH']:
            # Add cash to total value
            self.total_value += balance.available
    
    def calculate_target_allocations(self, strategy: str, assets: List[str]) -> Dict[str, float]:
        """Calculate target allocations using specified strategy"""
        if strategy not in self.allocation_strategies:
            raise ValueError(f"Unknown allocation strategy: {strategy}")
        
        return self.allocation_strategies[strategy](assets)
    
    def equal_weight_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Equal weight allocation"""
        if not assets:
            return {}
        
        weight = 1.0 / len(assets)
        return {asset: weight for asset in assets}
    
    def market_cap_weighted_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Market cap weighted allocation (requires market cap data)"""
        if not assets:
            return {}
        
        # In a real implementation, you'd get market cap data
        # For this example, we'll simulate with dummy data
        market_caps = {}
        for asset in assets:
            # Simulate market cap data
            market_caps[asset] = self.asset_volatilities.get(asset, 1.0) * 1000000  # Dummy market cap
        
        total_market_cap = sum(market_caps.values())
        
        if total_market_cap == 0:
            return {asset: 1.0/len(assets) for asset in assets}
        
        return {asset: market_caps[asset] / total_market_cap for asset in assets}
    
    def risk_parity_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Risk parity allocation based on asset volatilities"""
        if not assets:
            return {}
        
        # Get volatilities for assets (or use default)
        volatilities = [self.asset_volatilities.get(asset, 0.2) for asset in assets]
        
        # Avoid division by zero
        volatilities = [max(0.001, vol) for vol in volatilities]
        
        # Risk parity: allocate inversely to volatility
        risk_weights = [1.0 / vol for vol in volatilities]
        total_risk_weight = sum(risk_weights)
        
        return {
            asset: risk_weights[i] / total_risk_weight
            for i, asset in enumerate(assets)
        }
    
    def volatility_targeting_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Allocation to achieve target volatility"""
        target_vol = self.config.get('target_volatility', 0.15)  # 15% target volatility
        
        if not assets:
            return {}
        
        # Get current volatilities
        volatilities = [self.asset_volatilities.get(asset, 0.2) for asset in assets]
        volatilities = [max(0.001, vol) for vol in volatilities]  # Avoid zero volatility
        
        # Calculate weights to achieve target volatility
        # Simple approach: scale current weights based on target vs current volatility
        avg_vol = sum(volatilities) / len(volatilities)
        
        # If average asset volatility is higher than target, reduce weights proportionally
        adjustment_factor = target_vol / avg_vol
        equal_weights = [1.0/len(assets) for _ in assets]
        
        weights = [min(max(w * adjustment_factor, self.min_position_size), self.max_position_size) for w in equal_weights]
        
        # Normalize weights to sum to 1
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        return {asset: weights[i] for i, asset in enumerate(assets)}
    
    def max_diversification_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Maximum diversification allocation"""
        if len(assets) < 2:
            return {asset: 1.0 for asset in assets} if assets else {}
        
        # Create correlation matrix (simplified)
        n_assets = len(assets)
        # In a real implementation, this would be based on historical correlations
        correlation_matrix = np.eye(n_assets)  # Identity as default
        for i in range(n_assets):
            for j in range(i+1, n_assets):
                # Use stored correlations or default
                corr = self.asset_correlations.get((assets[i], assets[j]), 
                                                  self.asset_correlations.get((assets[j], assets[i]), 0.3))
                correlation_matrix[i, j] = correlation_matrix[j, i] = corr
        
        # Get volatilities
        vols = np.array([self.asset_volatilities.get(asset, 0.2) for asset in assets])
        vol_diag = np.diag(vols)
        cov_matrix = vol_diag @ correlation_matrix @ vol_diag
        
        # Calculate maximum diversification portfolio
        try:
            # Calculate weights that maximize diversification ratio
            ones = np.ones(n_assets)
            vol_sum = np.sum(vols)
            
            # For simplicity, use equal risk contribution as proxy for max diversification
            # In practice, you'd use an optimizer
            weights = 1 / (vols * n_assets) if vol_sum > 0 else np.ones(n_assets) / n_assets
            weights = weights / np.sum(weights)  # Normalize
            
            # Apply bounds
            weights = np.clip(weights, self.min_position_size, self.max_position_size)
            weights = weights / np.sum(weights)  # Re-normalize after clipping
            
        except Exception as e:
            logger.warning(f"Error in max diversification calculation: {e}, using equal weights")
            weights = np.ones(n_assets) / n_assets
        
        return {asset: weights[i] for i, asset in enumerate(assets)}
    
    def generate_rebalancing_orders(self, strategy: str, assets: List[str]) -> List[Order]:
        """Generate orders to rebalance portfolio to target allocations"""
        target_allocations = self.calculate_target_allocations(strategy, assets)
        
        # Calculate current allocations
        current_allocation = self._calculate_current_allocations()
        
        orders = []
        
        for asset in assets:
            target_weight = target_allocations.get(asset, 0)
            current_weight = current_allocation.get(asset, 0)
            
            # Calculate if rebalancing is needed
            weight_diff = abs(target_weight - current_weight)
            
            if weight_diff > self.rebalance_threshold:
                # Calculate target dollar value
                target_value = self.total_value * target_weight
                current_value = current_weight * self.total_value
                value_diff = target_value - current_value
                
                # Check if we have current position data
                current_position = self.current_positions.get(asset)
                current_price = self._get_current_price(asset)
                
                if current_price and current_price > 0:
                    # Calculate required quantity change
                    required_quantity = value_diff / current_price
                    
                    # For now, just generate a placeholder order
                    # In practice, you'd need more sophisticated order generation
                    if abs(required_quantity) > 0.01:  # Only if significant change
                        order_side = 'BUY' if required_quantity > 0 else 'SELL'
                        order_quantity = abs(required_quantity)
                        
                        # Create order object
                        order = Order(
                            symbol=asset,
                            side=order_side,
                            quantity=order_quantity,
                            order_type=None  # This would be set by caller
                        )
                        orders.append(order)
                        
                        logger.debug(f"Rebalancing order: {order_side} {order_quantity:.4f} of {asset}, "
                                    f"target: {target_weight:.3f}, current: {current_weight:.3f}")
        
        return orders
    
    def _calculate_current_allocations(self) -> Dict[str, float]:
        """Calculate current portfolio allocations by asset"""
        if self.total_value == 0:
            return {}
        
        allocations = {}
        for symbol, position in self.current_positions.items():
            value = position.quantity * position.entry_price
            allocations[symbol] = value / self.total_value
        
        return allocations
    
    def _get_current_price(self, asset: str) -> Optional[float]:
        """Get current price for an asset (placeholder implementation)"""
        # This would connect to real market data in production
        # For this example, we'll return a placeholder value
        return 100.0  # Placeholder price
    
    def validate_allocation(self, allocation: Dict[str, float]) -> bool:
        """Validate that an allocation is acceptable"""
        # Check that weights sum to close to 1
        total_weight = sum(allocation.values())
        if abs(total_weight - 1.0) > 0.01:  # Allow 1% tolerance
            logger.warning(f"Allocation weights sum to {total_weight}, not 1.0")
            return False
        
        # Check individual position limits
        for asset, weight in allocation.items():
            if weight > self.max_position_size:
                logger.warning(f"Position size for {asset} ({weight:.3f}) exceeds limit ({self.max_position_size})")
                return False
            if weight < -self.max_position_size:
                logger.warning(f"Short position size for {asset} ({weight:.3f}) exceeds limit ({self.max_position_size})")
                return False
        
        return True
    
    def get_risk_metrics(self) -> Dict:
        """Calculate portfolio risk metrics"""
        allocations = self._calculate_current_allocations()
        
        # Calculate portfolio volatility (simplified)
        if self.asset_volatilities and len(allocations) > 1:
            # Get allocation weights and volatilities
            assets = list(allocations.keys())
            weights = np.array([allocations[a] for a in assets])
            vols = np.array([self.asset_volatilities.get(a, 0.2) for a in assets])
            
            # Calculate portfolio volatility (assuming zero correlations for simplicity)
            portfolio_vol = np.sqrt(np.sum((weights * vols) ** 2))
        else:
            portfolio_vol = 0.0
        
        return {
            'total_value': self.total_value,
            'portfolio_volatility': portfolio_vol,
            'sharpe_ratio': (0.08 - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0,  # Placeholder return of 8%
            'current_allocations': allocations,
            'max_position_size': self.max_position_size,
            'max_correlation': self.max_correlation
        }
    
    def get_allocation_history(self) -> List[Dict]:
        """Get historical allocation data"""
        return self.historical_allocations.copy()