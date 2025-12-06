from typing import Dict, List, Optional
from shared.types import Position
from shared.logger import logger
from datetime import datetime
import numpy as np
import scipy.optimize as optimize


class RiskParity:
    """Risk parity portfolio optimization"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Risk parity parameters
        self.target_risk_contribution = config.get('target_risk_contribution', 1.0)  # Equal risk contribution
        self.risk_budgets = config.get('risk_budgets', {})  # Custom risk budgets for assets
        self.max_weight = config.get('max_weight', 0.2)  # Max 20% weight per asset
        self.min_weight = config.get('min_weight', 0.005)  # Min 0.5% weight per asset
        self.risk_parity_tolerance = config.get('risk_parity_tolerance', 1e-6)
        self.max_iterations = config.get('max_iterations', 1000)
        
        # Market data
        self.covariance_matrix = None
        self.volatilities = {}
        self.correlations = {}
        
        # Portfolio tracking
        self.current_weights = {}
        self.current_positions = {}
    
    def update_market_data(self, volatility_data: Dict[str, float], correlation_data: Optional[Dict] = None):
        """Update market data for risk parity calculation"""
        self.volatilities = volatility_data
        if correlation_data:
            self.correlations = correlation_data
        
        # Build covariance matrix if we have complete data
        self._build_covariance_matrix()
    
    def _build_covariance_matrix(self):
        """Build the covariance matrix from volatilities and correlations"""
        if not self.volatilities:
            return
            
        assets = list(self.volatilities.keys())
        n = len(assets)
        
        # Start with diagonal volatilities
        self.covariance_matrix = np.eye(n)
        for i, asset in enumerate(assets):
            self.covariance_matrix[i, i] = self.volatilities[asset] ** 2
        
        # Apply correlations if available
        if self.correlations:
            for i in range(n):
                for j in range(i+1, n):
                    asset1, asset2 = assets[i], assets[j]
                    # Check for correlation coefficient
                    corr = self.correlations.get((asset1, asset2), 
                                                self.correlations.get((asset2, asset1), 0.0))
                    vol1 = self.volatilities[asset1]
                    vol2 = self.volatilities[asset2]
                    
                    self.covariance_matrix[i, j] = self.covariance_matrix[j, i] = corr * vol1 * vol2
    
    def calculate_risk_parity_weights(self, assets: List[str], custom_risk_budgets: Optional[Dict] = None) -> Dict[str, float]:
        """Calculate risk parity weights for given assets"""
        if not assets:
            return {}
        
        # Use custom risk budgets if provided, otherwise use default
        risk_budgets = custom_risk_budgets or self.risk_budgets or {}
        
        # Ensure risk budgets sum to 1.0
        if risk_budgets:
            total_budget = sum(risk_budgets.get(asset, self.target_risk_contribution) for asset in assets)
            if total_budget > 0:
                normalized_risk_budgets = {
                    asset: risk_budgets.get(asset, self.target_risk_contribution) / total_budget
                    for asset in assets
                }
            else:
                normalized_risk_budgets = {asset: 1.0/len(assets) for asset in assets}
        else:
            # Equal risk budget for all assets
            normalized_risk_budgets = {asset: 1.0/len(assets) for asset in assets}
        
        if not self.covariance_matrix or len(assets) != self.covariance_matrix.shape[0]:
            # If no covariance matrix, use simplified approach based on volatility
            weights = self._calculate_volatility_based_weights(assets, normalized_risk_budgets)
            return weights
        
        # Calculate risk parity weights with bounds
        try:
            weights = self._optimize_risk_parity(assets, normalized_risk_budgets)
            return weights
        except Exception as e:
            logger.error(f"Error in risk parity optimization: {e}")
            # Fallback to volatility-based approach
            return self._calculate_volatility_based_weights(assets, normalized_risk_budgets)
    
    def _calculate_volatility_based_weights(self, assets: List[str], risk_budgets: Dict[str, float]) -> Dict[str, float]:
        """Calculate simplified risk parity weights based on volatilities only"""
        # Calculate weights as inverse of volatility, normalized by risk budget
        weights = {}
        total_inv_vol = 0
        
        for asset in assets:
            vol = self.volatilities.get(asset, 0.2)  # Default to 20% vol
            if vol > 0:
                # Weight is proportional to risk budget divided by volatility
                inv_vol = risk_budgets[asset] / vol
                weights[asset] = inv_vol
                total_inv_vol += inv_vol
        
        if total_inv_vol > 0:
            # Normalize weights
            weights = {asset: w / total_inv_vol for asset, w in weights.items()}
        else:
            # If all volatilities are zero, use equal weights
            weights = {asset: 1.0/len(assets) for asset in assets}
        
        # Apply bounds
        weights = self._apply_weight_bounds(weights)
        
        return weights
    
    def _optimize_risk_parity(self, assets: List[str], risk_budgets: Dict[str, float]) -> Dict[str, float]:
        """Optimize portfolio weights to achieve risk parity"""
        n = len(assets)
        
        def risk_parity_objective(weights):
            """Objective function for risk parity optimization"""
            # Portfolio variance
            portfolio_variance = weights.T @ self.covariance_matrix @ weights
            
            if portfolio_variance <= 0:
                return 1e10  # Return large value for invalid portfolio variance
            
            # Marginal risk contributions
            marginal_contributions = (self.covariance_matrix @ weights) / np.sqrt(portfolio_variance)
            
            # Risk contributions
            risk_contributions = weights * marginal_contributions
            
            # Target risk contribution
            target_contributions = [risk_budgets[assets[i]] * np.sqrt(portfolio_variance) for i in range(n)]
            
            # Difference between actual and target risk contributions
            diff = risk_contributions - target_contributions
            
            # Return sum of squared differences
            return np.sum(diff ** 2)
        
        # Constraints: weights sum to 1
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
        ]
        
        # Bounds for weights (min and max)
        bounds = [(self.min_weight, self.max_weight) for _ in range(n)]
        
        # Initial guess (equal weights)
        x0 = np.ones(n) / n
        
        # Optimize
        result = optimize.minimize(
            risk_parity_objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': self.max_iterations, 'ftol': self.risk_parity_tolerance}
        )
        
        if not result.success:
            logger.warning(f"Risk parity optimization failed: {result.message}")
            # Fallback to equal weights
            weights = np.ones(n) / n
        else:
            weights = result.x
        
        # Apply bounds again in case optimizer didn't respect them perfectly
        weights = np.clip(weights, self.min_weight, self.max_weight)
        # Re-normalize after clipping
        weights = weights / np.sum(weights)
        
        return {assets[i]: weights[i] for i in range(n)}
    
    def _apply_weight_bounds(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Apply minimum and maximum weight bounds to weights"""
        # First, clip weights to bounds
        bounded_weights = {
            asset: min(max(weight, self.min_weight), self.max_weight)
            for asset, weight in weights.items()
        }
        
        # Due to clipping, weights may no longer sum to 1, so we normalize
        total_weight = sum(bounded_weights.values())
        if total_weight > 0:
            normalized_weights = {
                asset: weight / total_weight
                for asset, weight in bounded_weights.items()
            }
        else:
            # This shouldn't happen in practice, but just in case
            normalized_weights = weights
        
        return normalized_weights
    
    def calculate_portfolio_risk_metrics(self, weights: Dict[str, float], assets: List[str]) -> Dict:
        """Calculate portfolio risk metrics"""
        if not assets or not self.covariance_matrix:
            return {}
        
        # Convert weights to array based on asset order
        ordered_weights = np.array([weights.get(asset, 0) for asset in assets])
        
        # Calculate portfolio variance
        portfolio_variance = ordered_weights.T @ self.covariance_matrix @ ordered_weights
        portfolio_volatility = np.sqrt(portfolio_variance) if portfolio_variance > 0 else 0
        
        # Calculate marginal risk contributions
        marginal_contributions = (self.covariance_matrix @ ordered_weights) / portfolio_volatility if portfolio_volatility > 0 else np.zeros(len(assets))
        
        # Calculate risk contributions
        risk_contributions = ordered_weights * marginal_contributions
        
        # Calculate risk contribution percentages
        total_risk = np.sum(risk_contributions)
        risk_contribution_pct = risk_contributions / total_risk if total_risk != 0 else np.zeros(len(assets))
        
        # Create metrics dict
        risk_metrics = {
            'portfolio_volatility': portfolio_volatility,
            'portfolio_variance': portfolio_variance,
            'total_risk_contribution': float(total_risk),
            'risk_contributions': {assets[i]: float(risk_contributions[i]) for i in range(len(assets))},
            'risk_contribution_percentages': {assets[i]: float(risk_contribution_pct[i]) for i in range(len(assets))},
            'risk_concentration': float(np.max(risk_contribution_pct))  # Max individual contribution
        }
        
        return risk_metrics
    
    def update_positions(self, positions: List[Position]):
        """Update current positions"""
        self.current_positions = {pos.symbol: pos for pos in positions}
    
    def get_current_weights(self) -> Dict[str, float]:
        """Get current portfolio weights"""
        return self.current_weights
    
    def calculate_risk_budget_variances(self, assets: List[str], weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate risk budget variances for monitoring"""
        if not assets or not self.covariance_matrix:
            return {}
        
        ordered_weights = np.array([weights.get(asset, 0) for asset in assets])
        n = len(assets)
        
        # Get the current portfolio variance
        portfolio_variance = ordered_weights.T @ self.covariance_matrix @ ordered_weights
        
        if portfolio_variance <= 0:
            return {asset: 0.0 for asset in assets}
        
        # Calculate marginal risk contributions (derivative of portfolio var w.r.t. weights)
        marginal_risks = (self.covariance_matrix @ ordered_weights) / portfolio_variance
        
        # Calculate individual risk contributions
        risk_contributions = {assets[i]: ordered_weights[i] * marginal_risks[i] for i in range(n)}
        
        return risk_contributions
    
    def risk_parity_report(self, assets: List[str]) -> Dict:
        """Generate a risk parity report"""
        weights = self.calculate_risk_parity_weights(assets)
        risk_metrics = self.calculate_portfolio_risk_metrics(weights, assets)
        
        report = {
            'assets': assets,
            'calculated_weights': weights,
            'risk_metrics': risk_metrics,
            'risk_budgets': self.risk_budgets,
            'volatilities': {asset: self.volatilities.get(asset, 0) for asset in assets}
        }
        
        return report