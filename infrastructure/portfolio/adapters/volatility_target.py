from typing import Dict, List, Optional
from shared.types import Position, Signal
from shared.logger import logger
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


class VolatilityTarget:
    """Volatility targeting portfolio management"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Volatility targeting parameters
        self.target_volatility = config.get('target_volatility', 0.15)  # 15% target annual volatility
        self.lookback_period = config.get('lookback_period', 252)  # 252 trading days for annualized vol
        self.rebalance_frequency = config.get('rebalance_frequency', 21)  # Rebalance every 21 days (monthly)
        self.volatility_window = config.get('volatility_window', 60)  # Calculate volatility over 60 days
        self.max_leverage = config.get('max_leverage', 2.0)  # Max 2x leverage
        self.min_leverage = config.get('min_leverage', 0.5)  # Min 0.5x (to allow scaling down)
        self.regression_period = config.get('regression_period', 22)  # Use 22 days for mean reversion adjustment
        
        # Portfolio tracking
        self.historical_returns = {}
        self.current_weights = {}
        self.current_leverage = 1.0
        self.last_rebalance_date = datetime.now() - timedelta(days=self.rebalance_frequency)
        self.portfolio_volatilities = {}
        self.target_weights_history = []
        
        # Asset volatility tracking
        self.asset_volatilities = {}
        self.portfolio_value = config.get('initial_capital', 100000)
        
    def update_market_data(self, returns_data: Dict[str, List[float]], current_prices: Dict[str, float]):
        """Update market data with historical returns and current prices"""
        for asset, returns in returns_data.items():
            # Keep only the lookback period of returns
            self.historical_returns[asset] = returns[-self.lookback_period:]
            
            # Calculate current volatility for the asset
            if len(returns) >= 2:
                self.asset_volatilities[asset] = self._calculate_volatility(returns[-self.volatility_window:])
        
        # Update portfolio value if current prices provided
        if current_prices and self.current_weights:
            self.portfolio_value = self._calculate_portfolio_value(current_prices)
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate annualized volatility from returns"""
        if not returns:
            return 0.0
            
        # Calculate standard deviation and annualize (assuming daily returns)
        volatility = np.std(returns) * np.sqrt(252)  # 252 trading days per year
        return float(volatility)
    
    def _calculate_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate current portfolio value based on weights and prices"""
        if not current_prices or not self.current_weights:
            return self.portfolio_value  # Return previous value if no data
            
        total_value = 0.0
        for asset, weight in self.current_weights.items():
            price = current_prices.get(asset)
            if price and price > 0:
                # Calculate the value of this asset based on our weight
                asset_value = self.portfolio_value * weight
                # Adjust for price changes
                total_value += asset_value * (price / self._get_average_price(asset))
        
        # If we can't calculate properly, return the original value
        return total_value if total_value > 0 else self.portfolio_value
    
    def _get_average_price(self, asset: str) -> float:
        """Get average price for an asset (placeholder for historical price tracking)"""
        # In a real implementation, this would track historical prices
        return 100.0  # Placeholder
    
    def calculate_target_weights(self, assets: List[str], current_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Calculate target weights based on volatility targeting"""
        if not assets:
            return {}
        
        # If current weights not provided, use equal weights as starting point
        if current_weights is None:
            current_weights = {asset: 1.0 / len(assets) for asset in assets}
        
        # Calculate current portfolio volatility
        current_portfolio_vol = self._calculate_portfolio_volatility(assets, current_weights)
        
        if current_portfolio_vol == 0:
            # If current volatility is 0, use equal weights
            return current_weights
        
        # Calculate leverage factor to achieve target volatility
        leverage_factor = self.target_volatility / current_portfolio_vol
        
        # Apply leverage constraints
        leverage_factor = max(self.min_leverage, min(self.max_leverage, leverage_factor))
        
        # Adjust weights based on leverage factor
        adjusted_weights = {}
        total_weight = 0.0
        
        for asset in assets:
            # Get the volatility of this individual asset
            asset_vol = self.asset_volatilities.get(asset, 0.2)  # Default 20%
            
            if asset_vol > 0:
                # Calculate a risk parity style weight adjusted for volatility targeting
                # The weight is proportional to the current weight but adjusted by the leverage factor
                current_asset_weight = current_weights.get(asset, 1.0/len(assets))
                
                # Apply leverage to the weight
                adjusted_weight = current_asset_weight * leverage_factor
                
                # Ensure weight doesn't exceed practical limits
                adjusted_weight = max(0.01, min(0.5, adjusted_weight))  # Keep between 1% and 50%
                
                adjusted_weights[asset] = adjusted_weight
                total_weight += adjusted_weight
            else:
                # If no volatility data, maintain current weight
                adjusted_weights[asset] = current_weights.get(asset, 0)
                total_weight += adjusted_weights[asset]
        
        # Normalize weights to sum to 1
        if total_weight > 0:
            final_weights = {asset: weight / total_weight for asset, weight in adjusted_weights.items()}
        else:
            final_weights = {asset: 1.0/len(assets) for asset in assets}
        
        # Store the current leverage being applied
        self.current_leverage = leverage_factor
        
        return final_weights
    
    def _calculate_portfolio_volatility(self, assets: List[str], weights: Dict[str, float]) -> float:
        """Calculate portfolio volatility using individual asset volatilities and correlations"""
        if not assets or len(assets) == 0:
            return 0.0
            
        # For simplicity, we'll assume no correlation between assets in this example
        # A full implementation would include correlation data
        vol_squared_sum = 0.0
        
        for asset in assets:
            weight = weights.get(asset, 1.0/len(assets))
            asset_vol = self.asset_volatilities.get(asset, 0.2)  # Default 20% volatility
            vol_squared_sum += (weight * asset_vol) ** 2
        
        portfolio_volatility = np.sqrt(vol_squared_sum)
        
        return float(portfolio_volatility)
    
    def should_rebalance(self) -> bool:
        """Determine if portfolio should be rebalanced"""
        time_since_rebalance = (datetime.now() - self.last_rebalance_date).days
        
        # Rebalance if enough time has passed
        if time_since_rebalance >= self.rebalance_frequency:
            return True
            
        # Alternative: rebalance if volatility deviates significantly from target
        # For this implementation, we'll stick to time-based rebalancing
        return False
    
    def generate_rebalancing_signals(self, assets: List[str], current_prices: Dict[str, float]) -> List[Signal]:
        """Generate rebalancing signals based on volatility targeting"""
        signals = []
        
        if not self.should_rebalance():
            return signals
        
        # Calculate new target weights
        new_weights = self.calculate_target_weights(assets, self.current_weights)
        
        # Generate buy/sell signals based on weight changes
        for asset in assets:
            current_weight = self.current_weights.get(asset, 0)
            target_weight = new_weights.get(asset, 0)
            
            weight_diff = target_weight - current_weight
            threshold = 0.02  # Only signal if weight change > 2%
            
            if abs(weight_diff) > threshold:
                # Determine signal type based on weight change
                if weight_diff > 0:
                    # Need to buy more of this asset
                    signal_type = 'BUY'
                    confidence = min(1.0, weight_diff * 10)  # Higher confidence for larger changes
                else:
                    # Need to sell some of this asset
                    signal_type = 'SELL'
                    confidence = min(1.0, abs(weight_diff) * 10)  # Higher confidence for larger changes
                
                signal = Signal(
                    symbol=asset,
                    signal_type=signal_type,
                    confidence=confidence,
                    score=weight_diff,  # Score represents the direction and magnitude of change needed
                    strategy="VolTarget_Rebal",
                    timestamp=datetime.now()
                )
                
                signals.append(signal)
        
        # Update last rebalance date and current weights
        if signals:  # Only update if we're actually rebalancing
            self.last_rebalance_date = datetime.now()
            self.current_weights = new_weights
            self.target_weights_history.append({
                'date': datetime.now(),
                'weights': new_weights.copy(),
                'leverage': self.current_leverage
            })
        
        # Limit history size
        if len(self.target_weights_history) > 100:
            self.target_weights_history = self.target_weights_history[-100:]
        
        return signals
    
    def update_positions(self, positions: List[Position]):
        """Update current positions"""
        # This would update the actual positions in the portfolio
        # For this implementation, we'll just use the weights
        pass
    
    def get_volatility_report(self) -> Dict:
        """Generate a volatility targeting report"""
        return {
            'target_volatility': self.target_volatility,
            'current_volatility': self._calculate_current_portfolio_volatility(),
            'current_leverage': self.current_leverage,
            'max_leverage': self.max_leverage,
            'min_leverage': self.min_leverage,
            'rebalance_frequency_days': self.rebalance_frequency,
            'days_since_last_rebalance': (datetime.now() - self.last_rebalance_date).days,
            'should_rebalance': self.should_rebalance(),
            'portfolio_value': self.portfolio_value,
            'current_weights': self.current_weights,
            'asset_volatilities': self.asset_volatilities
        }
    
    def _calculate_current_portfolio_volatility(self) -> float:
        """Calculate the current portfolio volatility"""
        return self._calculate_portfolio_volatility(
            list(self.current_weights.keys()), 
            self.current_weights
        )
    
    def calculate_volatility_adjusted_return(self, asset_returns: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """Calculate volatility-adjusted returns for assets"""
        adjusted_returns = {}
        
        for asset, returns in asset_returns.items():
            # Get the volatility of the asset
            asset_vol = self.asset_volatilities.get(asset, 0.2)
            
            if asset_vol > 0:
                # Calculate risk-adjusted returns (Sharpe-style)
                # This adjusts returns by the inverse of volatility
                adjustment_factor = self.target_volatility / asset_vol if asset_vol > 0 else 1.0
                adjusted_returns[asset] = [r * adjustment_factor for r in returns]
            else:
                # If no volatility data, return original returns
                adjusted_returns[asset] = returns
        
        return adjusted_returns
    
    def get_dynamic_target_volatility(self, market_regime: str = "normal") -> float:
        """Get dynamic target volatility based on market conditions"""
        # Adjust target volatility based on market regime
        if market_regime == "high_volatility":
            return self.target_volatility * 0.7  # Reduce target in high vol
        elif market_regime == "low_volatility":
            return self.target_volatility * 1.2  # Increase target in low vol
        else:
            return self.target_volatility  # Normal market conditions
    
    def update_volatility_target(self, new_target: float):
        """Update the target volatility"""
        self.target_volatility = max(0.05, min(0.5, new_target))  # Keep between 5% and 50%
        logger.info(f"Updated volatility target to {self.target_volatility:.2%}")