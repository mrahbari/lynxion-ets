"""
Advanced Risk Management Service for dynamic position sizing and SL/TP management.
Implements volatility-adjusted position sizing, correlation-based risk adjustments,
market regime detection, trailing stops, dynamic take-profit levels, and time-based exits.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from domain.entities.trading_entities import Order, Position
from domain.value_objects import Money, Percentage, Symbol
from domain.entities.signal_entities import FusedSignal
from shared.logger import EnhancedLogger


class RegimeType(Enum):
    """Market regime types for risk adjustment"""
    BULLISH_TRENDING = "bullish_trending"
    BEARISH_TRENDING = "bearish_trending"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CHOPPY = "choppy"
    BREAKOUT = "breakout"
    NORMAL = "normal"


class PositionSizingMethod(Enum):
    """Different position sizing methods"""
    FIXED_FRACTION = "fixed_fraction"
    KELLY_CRITERION = "kelly_criterion"
    AT_R = "atr_based"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    CORRELATION_ADJUSTED = "correlation_adjusted"


@dataclass
class RiskAdjustmentFactors:
    """Risk adjustment factors calculated by the risk management service"""
    volatility_factor: float = 1.0
    correlation_factor: float = 1.0
    regime_factor: float = 1.0
    market_condition_factor: float = 1.0
    position_size_multiplier: float = 1.0
    stop_loss_multiplier: float = 1.0
    take_profit_multiplier: float = 1.0


class AdvancedRiskManagementService:
    """Advanced risk management service with dynamic position sizing and SL/TP management"""

    def __init__(self, 
                 base_risk_percentage: float = 0.02,  # 2% risk per trade
                 max_correlation_threshold: float = 0.7,
                 atr_period: int = 14,
                 volatility_lookback: int = 20,
                 regime_detection_lookback: int = 50):
        self.base_risk_percentage = base_risk_percentage
        self.max_correlation_threshold = max_correlation_threshold
        self.atr_period = atr_period
        self.volatility_lookback = volatility_lookback
        self.regime_detection_lookback = regime_detection_lookback
        self.logger = EnhancedLogger("AdvancedRiskManagementService")
        
        # Track portfolio correlations and market conditions
        self.position_correlations: Dict[str, Dict[str, float]] = {}
        self.market_regimes: Dict[str, RegimeType] = {}
        self.historical_data_cache: Dict[str, pd.DataFrame] = {}

    def calculate_position_size(self, 
                              symbol: Symbol, 
                              price: float, 
                              portfolio_value: float,
                              fused_signal: FusedSignal,
                              market_data: Optional[pd.DataFrame] = None) -> Tuple[float, RiskAdjustmentFactors]:
        """
        Calculate optimal position size based on multiple risk factors.
        
        Args:
            symbol: Trading symbol
            price: Current price of the symbol
            portfolio_value: Total portfolio value
            fused_signal: Fused signal with market context
            market_data: Historical market data for calculations
            
        Returns:
            Tuple of (position_size, risk_adjustment_factors)
        """
        if market_data is None:
            # In a real implementation, fetch historical data for the symbol
            market_data = self._get_historical_data(symbol)
        
        # Calculate risk adjustment factors
        factors = self._calculate_risk_adjustment_factors(symbol, market_data, fused_signal)
        
        # Base position size calculation
        base_position_value = portfolio_value * self.base_risk_percentage
        
        # Apply all risk adjustment factors
        adjusted_position_value = (base_position_value * 
                                 factors.volatility_factor * 
                                 factors.correlation_factor * 
                                 factors.regime_factor * 
                                 factors.market_condition_factor *
                                 factors.position_size_multiplier)
        
        # Calculate position size in units
        position_size = adjusted_position_value / price if price > 0 else 0
        
        # Apply minimum and maximum position size limits
        min_position_size = portfolio_value * 0.001  # Minimum 0.1% of portfolio
        max_position_size = portfolio_value * 0.1    # Maximum 10% of portfolio
        
        position_size = max(min_position_size / price if price > 0 else 0, 
                           min(max_position_size / price if price > 0 else float('inf'), position_size))
        
        self.logger.info(f"Position sizing for {symbol.value}: "
                        f"Portfolio=${portfolio_value:.2f}, Price=${price:.2f}, "
                        f"Calculated size={position_size:.4f}, Value=${position_size * price:.2f}, "
                        f"Factors: vol={factors.volatility_factor:.2f}, "
                        f"corr={factors.correlation_factor:.2f}, "
                        f"regime={factors.regime_factor:.2f}")
        
        return position_size, factors

    def _calculate_risk_adjustment_factors(self, 
                                         symbol: Symbol, 
                                         market_data: pd.DataFrame, 
                                         fused_signal: FusedSignal) -> RiskAdjustmentFactors:
        """Calculate all risk adjustment factors"""
        factors = RiskAdjustmentFactors()
        
        # Calculate volatility factor
        factors.volatility_factor = self._calculate_volatility_factor(market_data)
        
        # Calculate correlation factor
        factors.correlation_factor = self._calculate_correlation_factor(symbol)
        
        # Calculate regime factor
        factors.regime_factor = self._calculate_regime_factor(symbol, market_data)
        
        # Calculate market condition factor based on fused signal
        factors.market_condition_factor = self._calculate_market_condition_factor(fused_signal)
        
        # Calculate position size multiplier based on confidence
        factors.position_size_multiplier = min(2.0, max(0.5, float(fused_signal.confidence.value) * 2))
        
        return factors

    def _calculate_volatility_factor(self, market_data: pd.DataFrame) -> float:
        """Calculate volatility-based risk adjustment factor"""
        if len(market_data) < self.volatility_lookback:
            return 1.0
        
        # Calculate rolling volatility
        returns = market_data['close'].pct_change().dropna()
        rolling_volatility = returns.rolling(window=self.volatility_lookback).std().iloc[-1]
        
        if pd.isna(rolling_volatility):
            return 1.0
        
        # Normalize volatility (higher volatility = smaller position)
        avg_volatility = 0.02  # 2% daily volatility as baseline
        volatility_ratio = rolling_volatility / avg_volatility
        
        # Adjust position size inversely to volatility
        # Higher volatility = smaller position, lower volatility = larger position (but capped)
        factor = 1.0 / (1.0 + volatility_ratio)
        
        # Ensure factor is reasonable (between 0.3 and 1.5)
        factor = max(0.3, min(1.5, factor))
        
        return factor

    def _calculate_correlation_factor(self, symbol: Symbol) -> float:
        """Calculate correlation-based risk adjustment factor"""
        # In a real implementation, this would check correlation with other positions
        # For now, return 1.0 (no adjustment) or implement based on stored correlations
        if symbol.value in self.position_correlations:
            # Calculate average correlation with other positions
            correlations = list(self.position_correlations[symbol.value].values())
            if correlations:
                avg_correlation = sum(correlations) / len(correlations)
                # Reduce position size if highly correlated with other positions
                factor = 1.0 - (avg_correlation / 2.0)  # Reduce by up to 50% if highly correlated
                return max(0.3, factor)  # Don't go below 30% of normal size
        
        return 1.0

    def _calculate_regime_factor(self, symbol: Symbol, market_data: pd.DataFrame) -> float:
        """Calculate market regime-based risk adjustment factor"""
        if len(market_data) < self.regime_detection_lookback:
            return 1.0
        
        # Detect market regime based on price action
        regime = self._detect_market_regime(market_data)
        self.market_regimes[symbol.value] = regime
        
        # Adjust risk based on regime
        regime_multipliers = {
            RegimeType.BULLISH_TRENDING: 1.2,    # Higher position size in trending markets
            RegimeType.BEARISH_TRENDING: 1.2,    # Higher position size in trending markets
            RegimeType.HIGH_VOLATILITY: 0.7,     # Lower position size in high volatility
            RegimeType.LOW_VOLATILITY: 1.1,      # Slightly higher in low volatility
            RegimeType.CHOPPY: 0.6,              # Much lower in choppy markets
            RegimeType.BREAKOUT: 1.0,            # Normal in breakout situations
            RegimeType.NORMAL: 1.0               # Normal in normal markets
        }
        
        return regime_multipliers.get(regime, 1.0)

    def _detect_market_regime(self, market_data: pd.DataFrame) -> RegimeType:
        """Detect current market regime based on technical analysis"""
        if len(market_data) < self.regime_detection_lookback:
            return RegimeType.NORMAL
        
        closes = market_data['close'].tail(self.regime_detection_lookback).values
        highs = market_data['high'].tail(self.regime_detection_lookback).values
        lows = market_data['low'].tail(self.regime_detection_lookback).values
        
        # Calculate trend strength using linear regression
        x = np.arange(len(closes))
        slope, intercept = np.polyfit(x, closes, 1)
        trend_strength = abs(slope) / np.mean(closes) if np.mean(closes) != 0 else 0
        
        # Calculate volatility
        returns = np.diff(closes) / closes[:-1]
        volatility = np.std(returns) if len(returns) > 0 else 0
        
        # Calculate choppiness (how much price oscillates)
        atr = self._calculate_atr(highs, lows, closes)
        choppiness = atr / (np.max(closes) - np.min(closes)) if (np.max(closes) - np.min(closes)) != 0 else 1
        
        # Determine regime based on calculated metrics
        if trend_strength > 0.005:  # Strong trend
            return RegimeType.BULLISH_TRENDING if slope > 0 else RegimeType.BEARISH_TRENDING
        elif volatility > 0.02:  # High volatility
            return RegimeType.HIGH_VOLATILITY
        elif volatility < 0.005:  # Low volatility
            return RegimeType.LOW_VOLATILITY
        elif choppiness > 0.7:  # Very choppy
            return RegimeType.CHOPPY
        else:
            return RegimeType.NORMAL

    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> float:
        """Calculate Average True Range"""
        if len(highs) < 2:
            return 0.0

        # Calculate True Range components
        tr1 = highs - lows
        # For TR2 and TR3, we need to align the arrays properly
        if len(closes) > 1:
            prev_closes = closes[:-1]  # Previous closes
            tr2 = np.abs(highs[1:] - prev_closes)  # High - previous close
            tr3 = np.abs(lows[1:] - prev_closes)  # Low - previous close

            # Calculate True Range as maximum of the three
            tr = np.maximum(tr1[1:], np.maximum(tr2, tr3))
            return np.mean(tr)
        else:
            return 0.0

    def _calculate_market_condition_factor(self, fused_signal: FusedSignal) -> float:
        """Calculate risk factor based on market conditions from fused signal"""
        # Use the fused signal's confidence and regime context
        base_confidence = float(fused_signal.confidence.value)
        
        # Adjust based on regime context
        regime_context = fused_signal.regime_context.lower()
        if 'trend' in regime_context:
            return min(1.3, base_confidence * 1.5)  # Higher confidence in trending markets
        elif 'volatile' in regime_context:
            return max(0.7, base_confidence * 0.8)  # Lower in volatile markets
        elif 'chop' in regime_context or 'range' in regime_context:
            return max(0.6, base_confidence * 0.7)  # Much lower in choppy/range-bound markets
        else:
            return base_confidence  # Normal adjustment

    def calculate_sl_tp_levels(self, 
                              entry_price: float, 
                              position_side: str,  # 'LONG' or 'SHORT'
                              risk_adjustment_factors: RiskAdjustmentFactors,
                              atr_value: Optional[float] = None,
                              market_data: Optional[pd.DataFrame] = None) -> Tuple[float, float]:
        """
        Calculate dynamic stop-loss and take-profit levels based on risk factors.
        
        Args:
            entry_price: Entry price for the position
            position_side: 'LONG' or 'SHORT'
            risk_adjustment_factors: Risk adjustment factors from position sizing
            atr_value: Average True Range value (if available)
            market_data: Market data for ATR calculation (if atr_value not provided)
            
        Returns:
            Tuple of (stop_loss_price, take_profit_price)
        """
        if atr_value is None and market_data is not None:
            highs = market_data['high'].values
            lows = market_data['low'].values
            closes = market_data['close'].values
            atr_value = self._calculate_atr(highs, lows, closes)
        
        if atr_value is None:
            # Default ATR if not available
            atr_value = entry_price * 0.01  # 1% of price as default ATR
        
        # Base stop loss and take profit multipliers
        base_sl_multiplier = 2.0  # 2 ATRs for stop loss
        base_tp_multiplier = 3.0  # 3 ATRs for take profit (1:1.5 risk/reward ratio)
        
        # Apply risk adjustment factors
        sl_multiplier = base_sl_multiplier * risk_adjustment_factors.stop_loss_multiplier
        tp_multiplier = base_tp_multiplier * risk_adjustment_factors.take_profit_multiplier
        
        if position_side.upper() == 'LONG':
            # For long positions: SL below entry, TP above entry
            stop_loss_price = entry_price - (atr_value * sl_multiplier)
            take_profit_price = entry_price + (atr_value * tp_multiplier)
            
            # Ensure stop loss is not too close to entry (minimum 1% away)
            min_sl_distance = entry_price * 0.01
            stop_loss_price = max(stop_loss_price, entry_price - min_sl_distance)
            
            # Ensure take profit is above entry
            take_profit_price = max(take_profit_price, entry_price + min_sl_distance)
            
        elif position_side.upper() == 'SHORT':
            # For short positions: SL above entry, TP below entry
            stop_loss_price = entry_price + (atr_value * sl_multiplier)
            take_profit_price = entry_price - (atr_value * tp_multiplier)
            
            # Ensure stop loss is not too close to entry (minimum 1% away)
            min_sl_distance = entry_price * 0.01
            stop_loss_price = min(stop_loss_price, entry_price + min_sl_distance)
            
            # Ensure take profit is below entry
            take_profit_price = min(take_profit_price, entry_price - min_sl_distance)
        else:
            raise ValueError(f"Invalid position side: {position_side}. Must be 'LONG' or 'SHORT'")
        
        self.logger.info(f"SL/TP calculation for {position_side} position at ${entry_price:.4f}: "
                        f"SL=${stop_loss_price:.4f}, TP=${take_profit_price:.4f}, "
                        f"ATR=${atr_value:.4f}, SL_mult={sl_multiplier:.2f}, TP_mult={tp_multiplier:.2f}")
        
        return stop_loss_price, take_profit_price

    def update_trailing_stop(self, 
                           current_price: float, 
                           entry_price: float, 
                           position_side: str,
                           initial_stop_loss: float,
                           trail_percentage: float = 0.10) -> float:
        """
        Update trailing stop based on current price movement.
        
        Args:
            current_price: Current market price
            entry_price: Entry price of the position
            position_side: 'LONG' or 'SHORT'
            initial_stop_loss: Initial stop loss level
            trail_percentage: Percentage to trail behind the price (default 10%)
            
        Returns:
            Updated stop loss price
        """
        if position_side.upper() == 'LONG':
            # For long positions, trailing stop moves up as price increases
            if current_price > entry_price:
                # Calculate trailing stop level (trail_percentage behind current price)
                trailing_stop = current_price * (1 - trail_percentage)
                # Never move stop loss below initial level or below entry
                return max(initial_stop_loss, trailing_stop, entry_price * 0.95)  # Don't go below 5% of entry
            else:
                # Price is below entry, don't adjust stop loss
                return initial_stop_loss
                
        elif position_side.upper() == 'SHORT':
            # For short positions, trailing stop moves down as price decreases
            if current_price < entry_price:
                # Calculate trailing stop level (trail_percentage ahead of current price)
                trailing_stop = current_price * (1 + trail_percentage)
                # Never move stop loss above initial level or above entry
                return min(initial_stop_loss, trailing_stop, entry_price * 1.05)  # Don't go above 5% of entry
            else:
                # Price is above entry, don't adjust stop loss
                return initial_stop_loss
        else:
            raise ValueError(f"Invalid position side: {position_side}. Must be 'LONG' or 'SHORT'")

    def should_exit_on_time(self, 
                          entry_time: datetime, 
                          max_holding_period: timedelta,
                          current_time: Optional[datetime] = None) -> bool:
        """
        Determine if position should be exited based on time constraints.
        
        Args:
            entry_time: Time when position was entered
            max_holding_period: Maximum allowed holding period
            current_time: Current time (if None, uses current time)
            
        Returns:
            True if position should be exited due to time constraint
        """
        if current_time is None:
            current_time = datetime.now()
        
        holding_period = current_time - entry_time
        
        return holding_period > max_holding_period

    def validate_order_risk(self, order: Order) -> bool:
        """
        Validate order against risk management standards.
        
        Args:
            order: Order to validate
            
        Returns:
            True if order passes risk validation, False otherwise
        """
        try:
            # Check if position size is within acceptable limits
            if hasattr(order, 'quantity') and order.quantity:
                # In a real implementation, we'd check against portfolio value and risk limits
                # For now, just ensure quantity is positive and reasonable
                if order.quantity <= 0:
                    self.logger.warning(f"Order validation failed: Invalid quantity {order.quantity}")
                    return False
                
                # Check if stop loss and take profit are set appropriately
                if hasattr(order, 'stop_loss_price') and order.stop_loss_price:
                    sl_distance = abs(order.stop_loss_price.amount - order.price.amount) / order.price.amount
                    if sl_distance > 0.20:  # Stop loss more than 20% away
                        self.logger.warning(f"Order validation warning: Stop loss too far ({sl_distance:.2%})")
                
                if hasattr(order, 'take_profit_price') and order.take_profit_price:
                    tp_distance = abs(order.take_profit_price.amount - order.price.amount) / order.price.amount
                    if tp_distance < 0.01:  # Take profit less than 1% away
                        self.logger.warning(f"Order validation warning: Take profit too close ({tp_distance:.2%})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating order risk: {e}")
            return False

    def _get_historical_data(self, symbol: Symbol) -> pd.DataFrame:
        """
        Get historical data for risk calculations.
        In a real implementation, this would fetch from data provider.
        """
        # This is a placeholder - in real implementation, fetch from data provider
        # For now, return a minimal dataframe
        return pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(hours=i) for i in range(50)],
            'open': [100.0 + i * 0.1 for i in range(50)],
            'high': [100.5 + i * 0.1 for i in range(50)],
            'low': [99.5 + i * 0.1 for i in range(50)],
            'close': [100.2 + i * 0.1 for i in range(50)],
            'volume': [1000 + i * 10 for i in range(50)]
        }).sort_values('timestamp').reset_index(drop=True)


class SLTPManager:
    """Manager for Stop Loss and Take Profit levels with advanced features"""

    def __init__(self, 
                 sl_activation_pct: float = 0.02,  # 2% stop loss
                 tp_activation_pct: float = 0.03,  # 3% take profit
                 trailing_enabled: bool = True,
                 time_exit_enabled: bool = True):
        self.sl_activation_pct = sl_activation_pct
        self.tp_activation_pct = tp_activation_pct
        self.trailing_enabled = trailing_enabled
        self.time_exit_enabled = time_exit_enabled
        self.logger = EnhancedLogger("SLTPManager")

    def calculate_initial_levels(self, 
                               entry_price: float, 
                               side: str,  # 'BUY' or 'SELL'
                               atr_value: Optional[float] = None) -> Dict[str, float]:
        """
        Calculate initial stop loss and take profit levels.
        
        Args:
            entry_price: Entry price for the position
            side: Trade side ('BUY' or 'SELL')
            atr_value: Average True Range value for ATR-based levels
            
        Returns:
            Dictionary with 'stop_loss' and 'take_profit' prices
        """
        if atr_value:
            # Use ATR-based levels for more dynamic risk management
            sl_multiplier = 2.0
            tp_multiplier = 3.0
            
            if side.upper() == 'BUY':
                stop_loss = entry_price - (atr_value * sl_multiplier)
                take_profit = entry_price + (atr_value * tp_multiplier)
            elif side.upper() == 'SELL':
                stop_loss = entry_price + (atr_value * sl_multiplier)
                take_profit = entry_price - (atr_value * tp_multiplier)
            else:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")
        else:
            # Use percentage-based levels
            if side.upper() == 'BUY':
                stop_loss = entry_price * (1 - self.sl_activation_pct)
                take_profit = entry_price * (1 + self.tp_activation_pct)
            elif side.upper() == 'SELL':
                stop_loss = entry_price * (1 + self.sl_activation_pct)
                take_profit = entry_price * (1 - self.tp_activation_pct)
            else:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")

        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }

    def update_levels_dynamically(self, 
                                current_price: float,
                                entry_price: float,
                                side: str,
                                current_levels: Dict[str, float],
                                market_regime: RegimeType,
                                volatility: float) -> Dict[str, float]:
        """
        Update SL/TP levels based on market conditions and price movement.
        
        Args:
            current_price: Current market price
            entry_price: Entry price of the position
            side: Trade side ('BUY' or 'SELL')
            current_levels: Current SL/TP levels
            market_regime: Current market regime
            volatility: Current market volatility
            
        Returns:
            Updated SL/TP levels
        """
        updated_levels = current_levels.copy()
        
        # Adjust levels based on market regime
        regime_adjustments = {
            RegimeType.BULLISH_TRENDING: {'sl_mult': 0.9, 'tp_mult': 1.1},
            RegimeType.BEARISH_TRENDING: {'sl_mult': 0.9, 'tp_mult': 1.1},
            RegimeType.HIGH_VOLATILITY: {'sl_mult': 1.2, 'tp_mult': 1.2},
            RegimeType.LOW_VOLATILITY: {'sl_mult': 0.8, 'tp_mult': 0.9},
            RegimeType.CHOPPY: {'sl_mult': 0.7, 'tp_mult': 0.8},
            RegimeType.BREAKOUT: {'sl_mult': 1.0, 'tp_mult': 1.3},
            RegimeType.NORMAL: {'sl_mult': 1.0, 'tp_mult': 1.0}
        }
        
        adjustment = regime_adjustments.get(market_regime, {'sl_mult': 1.0, 'tp_mult': 1.0})
        
        # Adjust for volatility
        vol_factor = 1.0 + (volatility - 0.02)  # Adjust based on deviation from normal volatility
        
        if self.trailing_enabled:
            # Implement trailing stop logic
            if side.upper() == 'BUY':
                # For long positions, if price moves favorably, adjust stop loss up
                if current_price > entry_price:
                    # Move stop loss closer to current price but maintain minimum distance
                    new_stop_loss = current_price - (abs(entry_price - current_levels['stop_loss']) * adjustment['sl_mult'] * vol_factor)
                    updated_levels['stop_loss'] = max(updated_levels['stop_loss'], new_stop_loss)
                    
                    # Potentially adjust take profit as well
                    if current_price > current_levels['take_profit']:
                        updated_levels['take_profit'] = current_price + abs(entry_price - current_levels['take_profit'])
            elif side.upper() == 'SELL':
                # For short positions, if price moves favorably, adjust stop loss down
                if current_price < entry_price:
                    # Move stop loss closer to current price but maintain minimum distance
                    new_stop_loss = current_price + (abs(entry_price - current_levels['stop_loss']) * adjustment['sl_mult'] * vol_factor)
                    updated_levels['stop_loss'] = min(updated_levels['stop_loss'], new_stop_loss)
                    
                    # Potentially adjust take profit as well
                    if current_price < current_levels['take_profit']:
                        updated_levels['take_profit'] = current_price - abs(entry_price - current_levels['take_profit'])
        
        self.logger.info(f"Updated SL/TP levels: SL=${updated_levels['stop_loss']:.4f}, "
                        f"TP=${updated_levels['take_profit']:.4f}, "
                        f"Regime={market_regime.value}, Vol={volatility:.4f}")
        
        return updated_levels