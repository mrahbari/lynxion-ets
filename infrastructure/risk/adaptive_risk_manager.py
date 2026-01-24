"""
Advanced Adaptive Risk Manager with regime-adaptive, correlation-aware, drawdown-sensitive, and volatility-normalized features.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


class RegimeType(Enum):
    """Market regime types for risk adjustment"""
    BULLISH_TRENDING = "bullish_trending"
    BEARISH_TRENDING = "bearish_trending"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CHOPPY = "choppy"
    BREAKOUT = "breakout"
    NORMAL = "normal"


@dataclass
class RiskMetrics:
    """Container for risk metrics"""
    total_exposure: float
    number_of_positions: int
    total_pnl: float
    daily_pnl: float
    current_drawdown: float
    volatility: float
    correlation_risk: float
    regime_factor: float
    equity: float


class AdaptiveRiskManager:
    """
    Advanced risk management system with adaptive features:
    - Regime-adaptive risk parameters
    - Correlation-aware position sizing
    - Drawdown-sensitive risk scaling
    - Volatility-normalized risk allocation
    """
    
    def __init__(self,
                 max_portfolio_exposure: float = 100000,
                 max_position_exposure: float = 50000,
                 base_risk_per_trade: float = 0.01,  # 1%
                 max_daily_loss_pct: float = 0.05,    # 5%
                 max_drawdown_pct: float = 0.15,      # 15%
                 max_correlation: float = 0.7,
                 fees_per_trade: float = 0.1,
                 slippage_tolerance: float = 0.001,
                 volatility_lookback: int = 20,
                 correlation_lookback: int = 30,
                 drawdown_recovery_factor: float = 0.5):
        
        # Base risk parameters
        self.max_portfolio_exposure = max_portfolio_exposure
        self.max_position_exposure = max_position_exposure
        self.base_risk_per_trade = base_risk_per_trade
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_correlation = max_correlation
        self.fees_per_trade = fees_per_trade
        self.slippage_tolerance = slippage_tolerance
        
        # Adaptive parameters
        self.volatility_lookback = volatility_lookback
        self.correlation_lookback = correlation_lookback
        self.drawdown_recovery_factor = drawdown_recovery_factor
        
        # State tracking
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.equity_curve: List[float] = []
        self.violations: List[str] = []
        self.daily_start = datetime.now().date()
        self.starting_equity = max_portfolio_exposure
        
        # Regime tracking
        self.current_regime = RegimeType.NORMAL
        self.regime_confidence = 0.5
        self.regime_history: List[Tuple[RegimeType, float, datetime]] = []
        
        # Correlation tracking
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self.correlation_history: Dict[str, List[Tuple[float, datetime]]] = {}
        
        # Drawdown tracking
        self.peak_equity = max_portfolio_exposure
        self.drawdown_duration = 0
        self.recovery_phase = False
        
        # Volatility tracking
        self.asset_volatilities: Dict[str, float] = {}
        self.market_volatility = 0.0

    def calculate_regime_adjusted_risk(self, regime: RegimeType, confidence: float) -> float:
        """
        Calculate risk adjustment based on market regime and confidence.
        
        Formula: base_risk * regime_multiplier * confidence_factor
        """
        # Regime-specific risk multipliers
        regime_multipliers = {
            RegimeType.BULLISH_TRENDING: 1.2,    # Higher risk in trending markets
            RegimeType.BEARISH_TRENDING: 1.2,    # Higher risk in trending markets  
            RegimeType.HIGH_VOLATILITY: 0.6,     # Lower risk in high volatility
            RegimeType.LOW_VOLATILITY: 1.1,      # Slightly higher in low volatility
            RegimeType.CHOPPY: 0.5,              # Much lower in choppy markets
            RegimeType.BREAKOUT: 0.8,            # Moderate risk in breakout situations
            RegimeType.NORMAL: 1.0               # Normal risk in normal markets
        }
        
        regime_multiplier = regime_multipliers.get(regime, 1.0)
        
        # Confidence-based adjustment (higher confidence = higher risk allowance)
        confidence_factor = 0.5 + (confidence * 0.5)  # Maps 0-1 to 0.5-1.0
        
        return self.base_risk_per_trade * regime_multiplier * confidence_factor

    def calculate_correlation_adjusted_risk(self, symbol: str, portfolio_symbols: List[str]) -> float:
        """
        Calculate risk adjustment based on correlation with existing positions.
        
        Formula: base_risk * (1 - avg_correlation_penalty)
        """
        if not portfolio_symbols:
            return 1.0
            
        total_correlation = 0.0
        correlation_count = 0
        
        for other_symbol in portfolio_symbols:
            if other_symbol != symbol:
                # Get correlation between symbols
                correlation = self._get_correlation(symbol, other_symbol)
                if correlation is not None:
                    total_correlation += abs(correlation)
                    correlation_count += 1
        
        if correlation_count == 0:
            return 1.0
            
        avg_correlation = total_correlation / correlation_count
        
        # Calculate penalty: higher correlation = lower risk allocation
        correlation_penalty = max(0, min(1, (avg_correlation - self.max_correlation) / (1 - self.max_correlation)))
        
        return max(0.1, 1 - correlation_penalty)  # At least 10% of base risk

    def calculate_drawdown_adjusted_risk(self) -> float:
        """
        Calculate risk adjustment based on current drawdown.
        
        Formula: base_risk * drawdown_recovery_factor^(drawdown_severity)
        """
        current_drawdown = self.calculate_drawdown()
        
        if current_drawdown <= 0:
            return 1.0  # No drawdown, full risk allocation
            
        # Normalize drawdown to 0-1 scale relative to max drawdown
        normalized_drawdown = min(current_drawdown / self.max_drawdown_pct, 1.0)
        
        # Apply exponential decay based on drawdown severity
        drawdown_factor = pow(self.drawdown_recovery_factor, normalized_drawdown * 5)
        
        # Ensure factor is between 0.05 and 1.0
        return max(0.05, drawdown_factor)

    def calculate_volatility_normalized_risk(self, symbol: str, volatility: Optional[float] = None) -> float:
        """
        Calculate risk adjustment based on asset volatility.
        
        Formula: base_risk / (1 + volatility_factor)
        """
        if volatility is None:
            volatility = self.asset_volatilities.get(symbol, 0.02)  # Default 2% daily vol
            
        # Normalize volatility relative to baseline (2% daily)
        baseline_vol = 0.02
        volatility_ratio = volatility / baseline_vol
        
        # Adjust risk inversely to volatility (higher vol = lower risk allocation)
        # But cap the adjustment to prevent extreme changes
        risk_adjustment = 1.0 / (1.0 + min(2.0, volatility_ratio))
        
        return max(0.2, risk_adjustment)  # Don't go below 20% of base risk

    def calculate_position_size(self, 
                              symbol: str,
                              entry_price: float, 
                              stop_loss: float,
                              portfolio_equity: float,
                              regime: RegimeType,
                              regime_confidence: float,
                              volatility: Optional[float] = None,
                              correlation_symbols: Optional[List[str]] = None,
                              drawdown_factor_override: Optional[float] = None) -> Tuple[float, Dict[str, float]]:
        """
        Calculate position size with all adaptive risk factors.
        
        Formula: 
        position_size = (portfolio_equity * base_risk * regime_factor * correlation_factor * 
                        drawdown_factor * volatility_factor) / |entry_price - stop_loss|
        """
        # Calculate all risk factors
        regime_factor = self.calculate_regime_adjusted_risk(regime, regime_confidence)
        correlation_factor = self.calculate_correlation_adjusted_risk(
            symbol, correlation_symbols or list(self.positions.keys())
        )
        drawdown_factor = drawdown_factor_override or self.calculate_drawdown_adjusted_risk()
        volatility_factor = self.calculate_volatility_normalized_risk(symbol, volatility)
        
        # Calculate risk-adjusted risk amount
        risk_amount = (portfolio_equity * 
                      self.base_risk_per_trade * 
                      regime_factor * 
                      correlation_factor * 
                      drawdown_factor * 
                      volatility_factor)
        
        # Calculate position size based on stop loss distance
        risk_distance = abs(entry_price - stop_loss)
        if risk_distance <= 0:
            risk_distance = entry_price * 0.01  # Default 1% stop if not provided
            
        position_size = risk_amount / risk_distance
        
        # Apply portfolio-level constraints
        max_position_by_exposure = self.max_position_exposure / entry_price if entry_price > 0 else float('inf')
        position_size = min(position_size, max_position_by_exposure)
        
        current_total_exposure = sum(pos['size'] * pos['entry_price'] for pos in self.positions.values())
        remaining_portfolio_capacity = self.max_portfolio_exposure - current_total_exposure
        max_position_by_portfolio = remaining_portfolio_capacity / entry_price if entry_price > 0 else float('inf')
        position_size = min(position_size, max_position_by_portfolio)
        
        # Ensure position size is positive
        position_size = max(position_size, 0.0)
        
        # Return position size and all factors for transparency
        factors = {
            'regime_factor': regime_factor,
            'correlation_factor': correlation_factor,
            'drawdown_factor': drawdown_factor,
            'volatility_factor': volatility_factor,
            'final_risk_amount': risk_amount,
            'risk_distance': risk_distance
        }
        
        return position_size, factors

    def update_regime(self, regime: RegimeType, confidence: float, market_data: Optional[Dict] = None):
        """Update current market regime and related metrics."""
        self.current_regime = regime
        self.regime_confidence = confidence
        self.regime_history.append((regime, confidence, datetime.now()))
        
        # Update market volatility if market data is provided
        if market_data and 'returns' in market_data:
            self.market_volatility = np.std(market_data['returns'])

    def update_correlation(self, symbol1: str, symbol2: str, correlation: float):
        """Update correlation between two symbols."""
        if symbol1 not in self.correlation_matrix:
            self.correlation_matrix[symbol1] = {}
        if symbol2 not in self.correlation_matrix:
            self.correlation_matrix[symbol2] = {}
            
        self.correlation_matrix[symbol1][symbol2] = correlation
        self.correlation_matrix[symbol2][symbol1] = correlation
        
        # Update correlation history
        if symbol1 not in self.correlation_history:
            self.correlation_history[symbol1] = []
        if symbol2 not in self.correlation_history:
            self.correlation_history[symbol2] = []
            
        self.correlation_history[symbol1].append((correlation, datetime.now()))
        self.correlation_history[symbol2].append((correlation, datetime.now()))

    def _get_correlation(self, symbol1: str, symbol2: str) -> Optional[float]:
        """Get correlation between two symbols."""
        if symbol1 in self.correlation_matrix and symbol2 in self.correlation_matrix[symbol1]:
            return self.correlation_matrix[symbol1][symbol2]
        return None

    def update_asset_volatility(self, symbol: str, volatility: float):
        """Update volatility for a specific asset."""
        self.asset_volatilities[symbol] = volatility

    def calculate_drawdown(self) -> float:
        """Calculate current drawdown based on equity curve."""
        if not self.equity_curve:
            current_equity = self.starting_equity + self.total_pnl
        else:
            current_equity = self.equity_curve[-1]
            
        if self.peak_equity == 0:
            return 0.0
            
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        # Update peak equity if current equity is higher
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.drawdown_duration = 0
            self.recovery_phase = True
        elif current_equity < self.peak_equity:
            self.drawdown_duration += 1
            if drawdown > 0.01:  # If drawdown > 1%, not in recovery phase
                self.recovery_phase = False
                
        return max(0.0, drawdown)

    def is_trading_allowed(self) -> bool:
        """Check if trading is allowed based on risk limits."""
        # Check daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / self.starting_equity if self.starting_equity > 0 else 0
        if daily_loss_pct > self.max_daily_loss_pct:
            self.violations.append(f"Daily loss limit exceeded: {daily_loss_pct:.2%} > {self.max_daily_loss_pct:.2%}")
            return False

        # Check drawdown limit
        current_drawdown = self.calculate_drawdown()
        if current_drawdown > self.max_drawdown_pct:
            self.violations.append(f"Drawdown limit exceeded: {current_drawdown:.2%} > {self.max_drawdown_pct:.2%}")
            return False

        return True

    def get_risk_metrics(self) -> RiskMetrics:
        """Get comprehensive risk metrics."""
        current_drawdown = self.calculate_drawdown()
        
        # Calculate portfolio volatility if possible
        volatility = self.market_volatility
        
        # Calculate correlation risk (average correlation of all positions)
        correlation_risk = 0.0
        if self.positions:
            total_corr = 0.0
            corr_count = 0
            for symbol in self.positions:
                for other_symbol in self.positions:
                    if symbol != other_symbol:
                        corr = self._get_correlation(symbol, other_symbol)
                        if corr is not None:
                            total_corr += abs(corr)
                            corr_count += 1
            correlation_risk = total_corr / corr_count if corr_count > 0 else 0.0
        
        current_equity = self.starting_equity + self.total_pnl
        
        return RiskMetrics(
            total_exposure=self.get_total_exposure(),
            number_of_positions=len(self.positions),
            total_pnl=self.total_pnl,
            daily_pnl=self.daily_pnl,
            current_drawdown=current_drawdown,
            volatility=volatility,
            correlation_risk=correlation_risk,
            regime_factor=self.calculate_regime_adjusted_risk(self.current_regime, self.regime_confidence),
            equity=current_equity
        )

    def get_total_exposure(self) -> float:
        """Get total portfolio exposure."""
        return sum(pos['size'] * pos['entry_price'] for pos in self.positions.values())

    def enter_position(self, 
                      symbol: str, 
                      entry_price: float, 
                      size: float,
                      stop_loss: float, 
                      take_profit: float,
                      regime: RegimeType,
                      timestamp: Optional[datetime] = None) -> bool:
        """Enter a new position with risk validation."""
        if not self.validate_position_entry(symbol, size, entry_price):
            return False

        if timestamp is None:
            timestamp = datetime.now()

        # Store position details
        self.positions[symbol] = {
            'entry_price': entry_price,
            'size': size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': timestamp,
            'regime': regime.value,
            'risk_amount': size * abs(entry_price - stop_loss)
        }

        return True

    def validate_position_entry(self, symbol: str, size: float, entry_price: float) -> bool:
        """Validate if a position entry is allowed based on risk constraints."""
        # Check if we're within position size limits
        position_value = size * entry_price
        if position_value > self.max_position_exposure:
            self.violations.append(f"{symbol}: Position size ${position_value:.2f} exceeds max position limit ${self.max_position_exposure}")
            return False

        # Check portfolio exposure limits
        current_exposure = sum(pos['size'] * pos['entry_price'] for pos in self.positions.values())
        if current_exposure + position_value > self.max_portfolio_exposure:
            self.violations.append(f"{symbol}: Portfolio exposure would exceed limit ${self.max_portfolio_exposure}")
            return False

        return True

    def exit_position(self, symbol: str, exit_price: float) -> float:
        """Exit a position and return PnL."""
        if symbol not in self.positions:
            return 0.0

        position = self.positions[symbol]
        
        # Calculate PnL (assuming long position for simplicity)
        pnl = (exit_price - position['entry_price']) * position['size']
        
        # Account for fees and slippage
        total_cost = self.fees_per_trade + (abs(pnl) * self.slippage_tolerance)
        pnl -= total_cost

        # Update daily and total PnL
        self.daily_pnl += pnl
        self.total_pnl += pnl

        # Update equity curve
        current_equity = self.starting_equity + self.total_pnl
        self.equity_curve.append(current_equity)

        # Remove position
        del self.positions[symbol]

        return pnl

    def reset_daily_counters(self):
        """Reset daily counters."""
        self.daily_pnl = 0.0
        self.daily_start = datetime.now().date()


# Global instance
adaptive_risk_manager = AdaptiveRiskManager()