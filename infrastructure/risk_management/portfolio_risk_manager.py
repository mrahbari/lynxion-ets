"""
Portfolio-level risk management system to control overall exposure
across all positions and strategies.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import threading
import time
import numpy as np
from scipy import stats

class PortfolioRiskLimits:
    """Define portfolio-level risk limits."""
    
    def __init__(self):
        # Maximum total portfolio drawdown allowed
        self.max_portfolio_drawdown = 0.05  # 5%
        
        # Maximum allocation to single strategy
        self.max_strategy_allocation = 0.30  # 30%
        
        # Maximum allocation to single symbol
        self.max_symbol_allocation = 0.10  # 10%
        
        # Maximum leverage
        self.max_leverage = 1.0  # No leverage for conservative approach
        
        # Maximum daily loss
        self.max_daily_loss = 0.02  # 2% per day
        
        # Minimum account balance threshold
        self.min_account_balance = 1000.0  # $1000

class PositionTracker:
    """Track individual positions and their risk."""
    
    def __init__(self, symbol: str, side: str, size: float, entry_price: float):
        self.symbol = symbol
        self.side = side  # 'long' or 'short'
        self.size = size
        self.entry_price = entry_price
        self.entry_time = datetime.now()
        self.current_pnl = 0.0
        self.max_unrealized_pnl = 0.0 if self.side == 'long' else float('inf')
        self.min_unrealized_pnl = float('inf') if self.side == 'long' else 0.0
        self.peak_time = self.entry_time
        self.valley_time = self.entry_time

class RegimeAwareRiskModel:
    """
    Redesigned Risk Model with regime-adaptive, correlation-aware, and volatility-normalized features.

    Mathematical Formula:
    Risk_Score = (Volatility_Factor * Volatility_Normalizer) *
                 (Correlation_Factor * Correlation_Penalty) *
                 (Drawdown_Factor * Drawdown_Multiplier) *
                 (Regime_Factor * Regime_Multiplier)

    Where:
    - Volatility_Normalizer = 1 / (1 + (current_volatility / baseline_volatility))
    - Correlation_Penalty = 1 - (avg_correlation_with_portfolio * correlation_penalty_factor)
    - Drawdown_Multiplier = exp(-current_drawdown / max_expected_drawdown)
    - Regime_Multiplier = regime_specific_risk_multiplier
    """

    def __init__(self,
                 baseline_volatility: float = 0.02,  # 2% daily baseline
                 correlation_penalty_factor: float = 0.5,
                 max_expected_drawdown: float = 0.20,  # 20% max expected drawdown
                 regime_risk_multipliers: Optional[Dict[str, float]] = None,
                 volatility_window: int = 20,
                 correlation_window: int = 30):

        self.baseline_volatility = baseline_volatility
        self.correlation_penalty_factor = correlation_penalty_factor
        self.max_expected_drawdown = max_expected_drawdown
        self.volatility_window = volatility_window
        self.correlation_window = correlation_window

        # Default regime risk multipliers
        self.regime_risk_multipliers = regime_risk_multipliers or {
            "calm": 0.8,
            "moderate": 1.0,
            "stress": 1.5,
            "crisis": 2.5
        }

    def calculate_risk_metrics(self,
                              prices: List[float],
                              portfolio_returns: List[float],
                              correlation_matrix: Optional[np.ndarray] = None,
                              current_drawdown: float = 0.0,
                              regime_context: str = "normal") -> Dict[str, float]:
        """
        Calculate comprehensive risk metrics with regime adaptation.
        """
        # Calculate volatility (volatility-normalized)
        volatility = self._calculate_volatility(prices)
        volatility_normalizer = self._calculate_volatility_normalizer(volatility)

        # Calculate correlation exposure (correlation-aware)
        correlation_exposure = self._calculate_correlation_exposure(
            prices, portfolio_returns, correlation_matrix
        )
        correlation_penalty = self._calculate_correlation_penalty(correlation_exposure)

        # Calculate drawdown sensitivity (drawdown-sensitive)
        drawdown_multiplier = self._calculate_drawdown_multiplier(current_drawdown)

        # Determine regime and apply regime-specific adjustments
        regime = self._classify_regime(prices, volatility, correlation_exposure)
        regime_multiplier = self.regime_risk_multipliers.get(regime, 1.0)

        # Calculate composite risk score
        risk_score = (volatility_normalizer *
                     correlation_penalty *
                     drawdown_multiplier *
                     regime_multiplier)

        # Calculate risk adjustments for SL/TP and position sizing
        stop_loss_adjustment = self._calculate_stop_loss_adjustment(
            volatility, correlation_exposure, regime
        )
        take_profit_adjustment = self._calculate_take_profit_adjustment(
            volatility, correlation_exposure, regime
        )
        position_size_adjustment = self._calculate_position_size_adjustment(
            risk_score, current_drawdown
        )

        # Calculate overall confidence in risk assessment
        confidence = self._calculate_risk_confidence(
            len(prices), volatility, correlation_exposure, regime
        )

        return {
            'volatility': volatility,
            'correlation': correlation_exposure,
            'drawdown': current_drawdown,
            'regime': regime,
            'risk_score': min(1.0, max(0.01, risk_score)),  # Clamp to reasonable range
            'confidence': confidence,
            'stop_loss_adjustment': stop_loss_adjustment,
            'take_profit_adjustment': take_profit_adjustment,
            'position_size_adjustment': position_size_adjustment
        }

    def _calculate_volatility(self, prices: List[float]) -> float:
        """
        Calculate rolling volatility from price data.
        """
        if len(prices) < 2:
            return self.baseline_volatility

        returns = np.diff(prices) / prices[:-1]
        if len(returns) < 2:
            return self.baseline_volatility

        # Calculate rolling volatility
        if len(returns) > self.volatility_window:
            recent_returns = returns[-self.volatility_window:]
        else:
            recent_returns = returns

        volatility = float(np.std(recent_returns))
        return max(0.001, volatility)  # Minimum volatility floor

    def _calculate_volatility_normalizer(self, current_volatility: float) -> float:
        """
        Calculate volatility normalizer to adjust risk based on current volatility.
        """
        ratio = current_volatility / self.baseline_volatility
        normalizer = 1.0 / (1.0 + ratio)
        return max(0.1, normalizer)  # Don't go below 10% of base risk

    def _calculate_correlation_exposure(self,
                                      asset_prices: List[float],
                                      portfolio_returns: List[float],
                                      correlation_matrix: Optional[np.ndarray] = None) -> float:
        """
        Calculate correlation exposure with portfolio.
        """
        if correlation_matrix is not None and correlation_matrix.shape[0] > 1:
            # Use provided correlation matrix to calculate average correlation
            # Exclude self-correlation (diagonal)
            n = correlation_matrix.shape[0]
            if n > 1:
                correlations = []
                for i in range(n):
                    for j in range(i+1, n):
                        correlations.append(abs(correlation_matrix[i, j]))
                return float(np.mean(correlations)) if correlations else 0.1

        # Calculate correlation with portfolio returns if no matrix provided
        if len(asset_prices) < 2 or len(portfolio_returns) < 2:
            return 0.1  # Default low correlation

        # Align lengths of both series
        min_len = min(len(asset_prices)-1, len(portfolio_returns))
        asset_returns = np.diff(asset_prices[:min_len+1]) / asset_prices[:min_len]
        portfolio_returns_aligned = portfolio_returns[-min_len:]

        if len(asset_returns) < 2 or len(portfolio_returns_aligned) < 2:
            return 0.1

        # Calculate correlation coefficient
        correlation = np.corrcoef(asset_returns, portfolio_returns_aligned)[0, 1]
        return abs(float(correlation)) if not np.isnan(correlation) else 0.1

    def _calculate_correlation_penalty(self, correlation_exposure: float) -> float:
        """
        Calculate penalty based on correlation with portfolio.
        """
        penalty = correlation_exposure * self.correlation_penalty_factor
        return max(0.1, 1.0 - penalty)  # Don't go below 10% of base risk

    def _calculate_drawdown_multiplier(self, current_drawdown: float) -> float:
        """
        Calculate adjustment based on current portfolio drawdown.
        """
        if self.max_expected_drawdown <= 0:
            return 1.0

        drawdown_ratio = current_drawdown / self.max_expected_drawdown
        multiplier = np.exp(-drawdown_ratio)
        return max(0.05, multiplier)  # Don't go below 5% of base risk

    def _classify_regime(self, prices: List[float], volatility: float, correlation: float) -> str:
        """
        Classify current risk regime based on multiple factors.
        """
        # Calculate volatility percentile relative to historical
        if len(prices) > 100:
            historical_volatilities = []
            for i in range(100, len(prices)):
                window_prices = prices[i-100:i]
                window_returns = np.diff(window_prices) / window_prices[:-1]
                historical_volatilities.append(np.std(window_returns))

            if historical_volatilities:
                vol_percentile = stats.percentileofscore(historical_volatilities, volatility)

                if vol_percentile >= 90 and correlation >= 0.7:
                    return "crisis"
                elif vol_percentile >= 75 and correlation >= 0.5:
                    return "stress"
                elif vol_percentile >= 50:
                    return "moderate"

        # Default classification based on absolute levels
        if volatility > self.baseline_volatility * 2.0 and correlation > 0.6:
            return "crisis"
        elif volatility > self.baseline_volatility * 1.5 and correlation > 0.4:
            return "stress"
        elif volatility > self.baseline_volatility * 1.2:
            return "moderate"
        else:
            return "calm"

    def _calculate_stop_loss_adjustment(self, volatility: float, correlation: float, regime: str) -> float:
        """
        Calculate stop loss adjustment based on risk factors.
        """
        # Base adjustment on volatility
        vol_adjustment = 1.0 + (volatility / self.baseline_volatility)

        # Add correlation penalty (higher correlation = wider stops needed)
        corr_adjustment = 1.0 + (correlation * 0.5)

        # Add regime multiplier
        regime_multiplier = self.regime_risk_multipliers[regime]

        adjustment = vol_adjustment * corr_adjustment * regime_multiplier
        return min(3.0, adjustment)  # Cap at 3x adjustment

    def _calculate_take_profit_adjustment(self, volatility: float, correlation: float, regime: str) -> float:
        """
        Calculate take profit adjustment based on risk factors.
        """
        # In high volatility/correlation regimes, be more conservative with TP
        vol_factor = max(0.7, 1.0 - (volatility / self.baseline_volatility) * 0.3)
        corr_factor = max(0.8, 1.0 - correlation * 0.2)

        # In stress/crisis, be more conservative
        regime_multiplier = {
            "calm": 1.1,
            "moderate": 1.0,
            "stress": 0.85,
            "crisis": 0.7
        }[regime]

        adjustment = vol_factor * corr_factor * regime_multiplier
        return max(0.5, adjustment)  # Don't go below 50% of base TP

    def _calculate_position_size_adjustment(self, risk_score: float, current_drawdown: float) -> float:
        """
        Calculate position size adjustment based on overall risk score and drawdown.
        """
        # Position size inversely related to risk score
        risk_adjustment = 1.0 / (1.0 + risk_score * 2.0)

        # Further reduce if in drawdown
        drawdown_factor = max(0.3, 1.0 - (current_drawdown / 0.1))  # Reduce by 10% per 1% drawdown

        adjustment = risk_adjustment * drawdown_factor
        return max(0.1, adjustment)  # Don't go below 10% of normal position size

    def _calculate_risk_confidence(self, data_points: int, volatility: float,
                                  correlation: float, regime: str) -> float:
        """
        Calculate confidence in risk assessment based on data quality and market conditions.
        """
        # More data points = higher confidence
        data_confidence = min(1.0, data_points / 100.0)  # Full confidence at 100+ data points

        # Lower confidence in high volatility or high correlation environments
        vol_confidence = max(0.3, 1.0 - (volatility / 0.1))  # Lower confidence if vol > 10%
        corr_confidence = max(0.4, 1.0 - correlation)  # Lower confidence with high correlation

        # Lower confidence in stress/crisis regimes
        regime_confidence = {
            "calm": 1.0,
            "moderate": 0.85,
            "stress": 0.6,
            "crisis": 0.4
        }[regime]

        # Combine all confidence factors
        confidence = (data_confidence * 0.4 +
                     vol_confidence * 0.2 +
                     corr_confidence * 0.2 +
                     regime_confidence * 0.2)

        return max(0.1, min(1.0, confidence))

    def validate_trade_risk(self,
                           entry_price: float,
                           stop_loss: float,
                           take_profit: float,
                           position_size: float,
                           risk_metrics: Dict[str, float],
                           max_risk_per_trade: float = 0.02) -> Tuple[bool, List[str]]:
        """
        Validate that a trade meets risk management criteria.
        """
        issues = []

        # Calculate actual risk per trade
        risk_distance = abs(entry_price - stop_loss)
        position_value = entry_price * position_size
        risk_amount = risk_distance * position_size
        risk_percentage = risk_amount / position_value if position_value > 0 else 0

        # Check if risk per trade exceeds maximum
        if risk_percentage > max_risk_per_trade:
            issues.append(f"Risk per trade ({risk_percentage:.2%}) exceeds maximum allowed ({max_risk_per_trade:.2%})")

        # Check risk-reward ratio based on regime and correlation
        reward_distance = abs(take_profit - entry_price)
        risk_reward_ratio = reward_distance / risk_distance if risk_distance > 0 else float('inf')

        # Minimum RR requirements vary by regime
        min_rr_by_regime = {
            "calm": 1.5,
            "moderate": 1.8,
            "stress": 2.0,
            "crisis": 2.5
        }
        min_required_rr = min_rr_by_regime[risk_metrics['regime']]

        if risk_reward_ratio < min_required_rr:
            issues.append(f"Risk-reward ratio ({risk_reward_ratio:.2f}) below minimum required for {risk_metrics['regime']} regime ({min_required_rr})")

        # Check if stop loss is too tight given volatility
        min_sl_distance = entry_price * (risk_metrics['volatility'] * 2.0)  # At least 2x volatility for SL
        if risk_distance < min_sl_distance:
            issues.append(f"Stop loss distance (${risk_distance:.4f}) too tight for current volatility (minimum: ${min_sl_distance:.4f})")

        # Check if take profit is achievable given market conditions
        max_tp_distance = entry_price * (risk_metrics['volatility'] * 8.0)  # Max 8x volatility for TP
        if reward_distance > max_tp_distance:
            issues.append(f"Take profit distance (${reward_distance:.4f}) too wide for current volatility (maximum: ${max_tp_distance:.4f})")

        # Check correlation impact on position sizing
        if risk_metrics['correlation'] > 0.7 and position_size > (position_value * 0.05):  # If high correlation, max 5% of portfolio
            issues.append(f"Position size too large given high correlation ({risk_metrics['correlation']:.2f}) with portfolio")

        is_valid = len(issues) == 0
        return is_valid, issues


class PortfolioRiskManager:
    """Manage portfolio-level risk controls."""

    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_pnl = 0.0
        self.daily_pnl_reset_time = datetime.now().date()

        self.positions: Dict[str, PositionTracker] = {}  # trade_id -> PositionTracker
        self.strategy_allocations: Dict[str, float] = {}  # strategy_name -> allocated_amount
        self.symbol_allocations: Dict[str, float] = {}   # symbol -> allocated_amount

        self.limits = PortfolioRiskLimits()
        self.lock = threading.Lock()
        self.active = True

        # Add the redesigned risk model
        self.regime_aware_risk_model = RegimeAwareRiskModel()
        
    def update_position(self, trade_id: str, symbol: str, strategy: str, 
                       side: str, size: float, price: float) -> bool:
        """Update position and check risk limits."""
        with self.lock:
            if not self.active:
                return False
                
            # Check if we should allow this position based on limits
            if not self._check_position_risk(symbol, strategy, size, price):
                return False
                
            # Create/update position
            self.positions[trade_id] = PositionTracker(symbol, side, size, price)
            
            # Update allocations
            self._update_allocations(strategy, symbol, size * price)
            
            return True
            
    def update_pnl(self, trade_id: str, current_price: float) -> float:
        """Update PnL for a position and return current PnL."""
        with self.lock:
            if trade_id not in self.positions:
                return 0.0
                
            pos = self.positions[trade_id]
            multiplier = 1 if pos.side == 'long' else -1
            pos.current_pnl = (current_price - pos.entry_price) * pos.size * multiplier
            
            # Update peak/valley tracking for drawdown calculation
            if pos.current_pnl > pos.max_unrealized_pnl:
                pos.max_unrealized_pnl = pos.current_pnl
                pos.peak_time = datetime.now()
            elif pos.current_pnl < pos.min_unrealized_pnl:
                pos.min_unrealized_pnl = pos.current_pnl
                pos.valley_time = datetime.now()
                
            return pos.current_pnl
            
    def close_position(self, trade_id: str, exit_price: float) -> float:
        """Close a position and return realized PnL."""
        with self.lock:
            if trade_id not in self.positions:
                return 0.0
                
            pos = self.positions[trade_id]
            multiplier = 1 if pos.side == 'long' else -1
            realized_pnl = (exit_price - pos.entry_price) * pos.size * multiplier
            
            # Update capital and daily PnL
            self.current_capital += realized_pnl
            self.daily_pnl += realized_pnl
            
            # Remove position and update allocations
            allocated_amount = pos.size * pos.entry_price
            self._remove_allocations(pos.symbol, pos.strategy, allocated_amount)
            del self.positions[trade_id]
            
            # Check if we need to reset daily PnL
            if datetime.now().date() != self.daily_pnl_reset_time:
                self.daily_pnl = 0.0
                self.daily_pnl_reset_time = datetime.now().date()
            
            return realized_pnl
            
    def _check_position_risk(self, symbol: str, strategy: str, size: float, price: float) -> bool:
        """Check if a new position violates risk limits."""
        position_value = size * price
        
        # Check total portfolio drawdown
        total_allocated = sum(pos.size * pos.entry_price for pos in self.positions.values())
        total_pnl = self.current_capital - self.initial_capital + self.daily_pnl
        portfolio_drawdown = abs(total_pnl) / self.initial_capital if self.initial_capital > 0 else 0
        
        if portfolio_drawdown > self.limits.max_portfolio_drawdown:
            return False
            
        # Check strategy allocation limit
        current_strategy_alloc = self.strategy_allocations.get(strategy, 0.0)
        if (current_strategy_alloc + position_value) / self.current_capital > self.limits.max_strategy_allocation:
            return False
            
        # Check symbol allocation limit
        current_symbol_alloc = self.symbol_allocations.get(symbol, 0.0)
        if (current_symbol_alloc + position_value) / self.current_capital > self.limits.max_symbol_allocation:
            return False
            
        # Check daily loss limit
        if self.daily_pnl < -abs(self.current_capital * self.limits.max_daily_loss):
            return False
            
        # Check minimum account balance
        if self.current_capital < self.limits.min_account_balance:
            return False
            
        return True
        
    def _update_allocations(self, strategy: str, symbol: str, amount: float):
        """Update strategy and symbol allocation tracking."""
        self.strategy_allocations[strategy] = self.strategy_allocations.get(strategy, 0.0) + amount
        self.symbol_allocations[symbol] = self.symbol_allocations.get(symbol, 0.0) + amount
        
    def _remove_allocations(self, symbol: str, strategy: str, amount: float):
        """Remove allocation tracking when position is closed."""
        self.strategy_allocations[strategy] = max(0, self.strategy_allocations.get(strategy, 0.0) - amount)
        self.symbol_allocations[symbol] = max(0, self.symbol_allocations.get(symbol, 0.0) - amount)
        
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio risk summary."""
        with self.lock:
            total_allocated = sum(pos.size * pos.entry_price for pos in self.positions.values())
            total_pnl = self.current_capital - self.initial_capital + self.daily_pnl
            portfolio_drawdown = abs(total_pnl) / self.initial_capital if self.initial_capital > 0 else 0
            
            return {
                "current_capital": self.current_capital,
                "total_allocated": total_allocated,
                "daily_pnl": self.daily_pnl,
                "total_pnl": total_pnl,
                "portfolio_drawdown": portfolio_drawdown,
                "active_positions_count": len(self.positions),
                "strategy_allocations": self.strategy_allocations.copy(),
                "symbol_allocations": self.symbol_allocations.copy(),
                "limits": {
                    "max_portfolio_drawdown": self.limits.max_portfolio_drawdown,
                    "max_strategy_allocation": self.limits.max_strategy_allocation,
                    "max_symbol_allocation": self.limits.max_symbol_allocation,
                    "max_daily_loss": self.limits.max_daily_loss,
                    "min_account_balance": self.limits.min_account_balance
                }
            }
            
    def emergency_stop(self):
        """Emergency stop all trading activity."""
        with self.lock:
            self.active = False
            
    def resume_trading(self):
        """Resume trading after emergency stop."""
        with self.lock:
            self.active = True

# Global portfolio risk manager instance
portfolio_risk_manager = PortfolioRiskManager()