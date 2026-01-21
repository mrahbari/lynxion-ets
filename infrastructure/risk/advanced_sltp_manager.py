"""
Advanced SL/TP Logic with volatility-normalized and structure-aware features.
Implements regime-adaptive stop loss and take profit levels.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


class PositionSide(Enum):
    """Position side enumeration"""
    LONG = "long"
    SHORT = "short"


class RegimeType(Enum):
    """Market regime types"""
    BULLISH_TRENDING = "bullish_trending"
    BEARISH_TRENDING = "bearish_trending"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CHOPPY = "choppy"
    BREAKOUT = "breakout"
    NORMAL = "normal"


@dataclass
class SLTPLevels:
    """Container for SL/TP levels"""
    stop_loss: float
    take_profit: float
    sl_distance: float  # Distance from entry in price terms
    tp_distance: float  # Distance from entry in price terms
    sl_atr_multiple: float  # SL distance in ATR multiples
    tp_atr_multiple: float  # TP distance in ATR multiples
    regime_adjusted: bool  # Whether levels were adjusted for regime


class AdvancedSLTPManager:
    """
    Advanced SL/TP management with volatility normalization and structure awareness.
    
    Key features:
    - Volatility-normalized SL/TP distances using ATR
    - Structure-aware levels based on support/resistance
    - Regime-adaptive adjustments
    - Priority-based execution (SL > TP for simultaneous hits)
    """
    
    def __init__(self,
                 default_sl_atr_multiplier: float = 2.0,
                 default_tp_atr_multiplier: float = 3.0,
                 min_risk_reward_ratio: float = 1.0,
                 max_risk_reward_ratio: float = 3.0,
                 support_resistance_buffer: float = 0.005,  # 0.5% buffer around S/R levels
                 regime_sl_multipliers: Optional[Dict[str, float]] = None,
                 regime_tp_multipliers: Optional[Dict[str, float]] = None):
        
        self.default_sl_atr_multiplier = default_sl_atr_multiplier
        self.default_tp_atr_multiplier = default_tp_atr_multiplier
        self.min_risk_reward_ratio = min_risk_reward_ratio
        self.max_risk_reward_ratio = max_risk_reward_ratio
        self.support_resistance_buffer = support_resistance_buffer
        
        # Regime-specific multipliers for SL/TP
        self.regime_sl_multipliers = regime_sl_multipliers or {
            RegimeType.BULLISH_TRENDING.value: 1.5,
            RegimeType.BEARISH_TRENDING.value: 1.5,
            RegimeType.HIGH_VOLATILITY.value: 2.5,
            RegimeType.LOW_VOLATILITY.value: 1.8,
            RegimeType.CHOPPY.value: 1.2,
            RegimeType.BREAKOUT.value: 2.0,
            RegimeType.NORMAL.value: 2.0
        }
        
        self.regime_tp_multipliers = regime_tp_multipliers or {
            RegimeType.BULLISH_TRENDING.value: 3.5,
            RegimeType.BEARISH_TRENDING.value: 3.5,
            RegimeType.HIGH_VOLATILITY.value: 4.0,
            RegimeType.LOW_VOLATILITY.value: 2.5,
            RegimeType.CHOPPY.value: 2.0,
            RegimeType.BREAKOUT.value: 4.0,
            RegimeType.NORMAL.value: 3.0
        }

    def calculate_levels(self,
                        entry_price: float,
                        position_side: PositionSide,
                        atr_value: float,
                        regime: RegimeType,
                        support_level: Optional[float] = None,
                        resistance_level: Optional[float] = None,
                        volatility: Optional[float] = None,
                        trend_strength: Optional[float] = None) -> SLTPLevels:
        """
        Calculate SL/TP levels with all advanced features.

        For LONG positions:
        - SL below entry (but above support if provided)
        - TP above entry (but below resistance if provided)

        For SHORT positions:
        - SL above entry (but below resistance if provided)
        - TP below entry (but above support if provided)
        """
        # Get regime-specific multipliers
        sl_multiplier = self.regime_sl_multipliers.get(regime.value, self.default_sl_atr_multiplier)
        tp_multiplier = self.regime_tp_multipliers.get(regime.value, self.default_tp_atr_multiplier)

        # Adjust multipliers based on trend strength if provided
        if trend_strength is not None:
            # Stronger trends get wider stops/profits to avoid premature exits
            trend_adjustment = 1.0 + (abs(trend_strength) * 0.2)
            sl_multiplier *= trend_adjustment
            tp_multiplier *= trend_adjustment

        # Calculate base SL/TP distances using ATR
        sl_distance = atr_value * sl_multiplier
        tp_distance = atr_value * tp_multiplier

        # Apply volatility normalization - in high volatility environments,
        # we want wider stops to avoid whipsaws
        if volatility is not None:
            volatility_factor = max(1.0, volatility / 0.02)  # Normalize to 2% baseline
            sl_distance *= volatility_factor
            tp_distance *= volatility_factor

        # Calculate base levels
        if position_side == PositionSide.LONG:
            base_sl = entry_price - sl_distance
            base_tp = entry_price + tp_distance
        else:  # SHORT
            base_sl = entry_price + sl_distance
            base_tp = entry_price - tp_distance

        # Apply structure awareness (support/resistance levels)
        final_sl, final_tp = self._apply_structure_awareness(
            base_sl, base_tp, entry_price, position_side,
            support_level, resistance_level
        )

        # Ensure minimum risk-reward ratio
        final_sl, final_tp = self._ensure_min_risk_reward_ratio(
            entry_price, final_sl, final_tp, position_side
        )

        # Additional market structure validation
        final_sl, final_tp = self._validate_market_structure(
            entry_price, final_sl, final_tp, position_side,
            support_level, resistance_level
        )

        # Calculate distances from entry
        sl_dist_from_entry = abs(final_sl - entry_price)
        tp_dist_from_entry = abs(final_tp - entry_price)

        # Calculate ATR multiples for reporting
        sl_atr_mult = sl_dist_from_entry / atr_value if atr_value > 0 else sl_multiplier
        tp_atr_mult = tp_dist_from_entry / atr_value if atr_value > 0 else tp_multiplier

        return SLTPLevels(
            stop_loss=final_sl,
            take_profit=final_tp,
            sl_distance=sl_dist_from_entry,
            tp_distance=tp_dist_from_entry,
            sl_atr_multiple=sl_atr_mult,
            tp_atr_multiple=tp_atr_mult,
            regime_adjusted=True
        )

    def _validate_market_structure(self,
                                 entry_price: float,
                                 sl_price: float,
                                 tp_price: float,
                                 position_side: PositionSide,
                                 support_level: Optional[float],
                                 resistance_level: Optional[float]) -> Tuple[float, float]:
        """
        Validate SL/TP levels against market structure (support/resistance).

        This ensures more realistic levels that respect key technical levels.
        """
        final_sl = sl_price
        final_tp = tp_price

        if position_side == PositionSide.LONG:
            # For long positions, ensure SL is not too close to support or TP too close to resistance
            if support_level is not None:
                # Ensure stop loss is not below key support (unless it's a breakdown scenario)
                # But allow some buffer for false breakouts
                min_sl = support_level * 0.995  # Allow 0.5% below support for false breakouts
                final_sl = max(final_sl, min_sl)

            if resistance_level is not None:
                # Ensure take profit is not too close to resistance (to avoid rejection)
                max_tp = resistance_level * 0.998  # Stay 0.2% below resistance to avoid rejection
                final_tp = min(final_tp, max_tp)

        else:  # SHORT
            # For short positions, ensure SL is not too close to resistance or TP too close to support
            if resistance_level is not None:
                # Ensure stop loss is not above key resistance (unless it's a breakdown scenario)
                max_sl = resistance_level * 1.005  # Allow 0.5% above resistance for false breakouts
                final_sl = min(final_sl, max_sl)

            if support_level is not None:
                # Ensure take profit is not too close to support (to avoid rejection)
                min_tp = support_level * 1.002  # Stay 0.2% above support to avoid rejection
                final_tp = max(final_tp, min_tp)

        return final_sl, final_tp

    def _apply_structure_awareness(self,
                                  base_sl: float,
                                  base_tp: float,
                                  entry_price: float,
                                  position_side: PositionSide,
                                  support_level: Optional[float],
                                  resistance_level: Optional[float]) -> Tuple[float, float]:
        """
        Apply structure awareness to SL/TP levels based on support/resistance.
        """
        final_sl = base_sl
        final_tp = base_tp
        
        if position_side == PositionSide.LONG:
            # For long positions: SL should not be below major support, TP should not be above major resistance
            if support_level is not None:
                # Place SL above support level with buffer
                min_sl = support_level * (1 + self.support_resistance_buffer)
                final_sl = max(final_sl, min_sl)
            
            if resistance_level is not None:
                # Place TP below resistance level with buffer
                max_tp = resistance_level * (1 - self.support_resistance_buffer)
                final_tp = min(final_tp, max_tp)
                
        else:  # SHORT
            # For short positions: SL should not be above major resistance, TP should not be below major support
            if resistance_level is not None:
                # Place SL below resistance level with buffer
                max_sl = resistance_level * (1 - self.support_resistance_buffer)
                final_sl = min(final_sl, max_sl)
            
            if support_level is not None:
                # Place TP above support level with buffer
                min_tp = support_level * (1 + self.support_resistance_buffer)
                final_tp = max(final_tp, min_tp)
        
        return final_sl, final_tp

    def _ensure_min_risk_reward_ratio(self,
                                     entry_price: float,
                                     sl_price: float,
                                     tp_price: float,
                                     position_side: PositionSide) -> Tuple[float, float]:
        """
        Ensure minimum risk-reward ratio is maintained.
        """
        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
        
        current_rr = reward / risk if risk > 0 else float('inf')
        
        if current_rr < self.min_risk_reward_ratio:
            # Increase TP distance to meet minimum RR
            required_reward = risk * self.min_risk_reward_ratio
            
            if position_side == PositionSide.LONG:
                tp_price = entry_price + required_reward
            else:  # SHORT
                tp_price = entry_price - required_reward
        
        elif current_rr > self.max_risk_reward_ratio:
            # Reduce TP distance to meet maximum RR (avoid unreachable targets)
            max_reward = risk * self.max_risk_reward_ratio
            
            if position_side == PositionSide.LONG:
                tp_price = entry_price + max_reward
            else:  # SHORT
                tp_price = entry_price - max_reward
        
        return sl_price, tp_price

    def check_exit_conditions(self,
                           current_price: float,
                           high_price: float,
                           low_price: float,
                           sl_price: float,
                           tp_price: float,
                           position_side: PositionSide) -> Tuple[Optional[float], Optional[str]]:
        """
        Check if SL or TP conditions are met with proper priority.

        For simultaneous hits, realistic execution based on order book dynamics.
        In real markets, the stop loss order is typically placed first and has priority.
        """
        exit_price = None
        exit_type = None

        if position_side == PositionSide.LONG:
            # For long positions: SL triggered if low <= SL, TP triggered if high >= TP
            sl_hit = low_price <= sl_price
            tp_hit = high_price >= tp_price

            if sl_hit and tp_hit:
                # Both hit in same candle - in real markets, SL orders often have priority
                # as they are usually placed first and represent risk management
                # Also, SL orders are often market orders when triggered, taking priority
                exit_price, exit_type = sl_price, 'SL'
            elif sl_hit:
                exit_price, exit_type = sl_price, 'SL'
            elif tp_hit:
                exit_price, exit_type = tp_price, 'TP'

        else:  # SHORT
            # For short positions: SL triggered if high >= SL, TP triggered if low <= TP
            sl_hit = high_price >= sl_price
            tp_hit = low_price <= tp_price

            if sl_hit and tp_hit:
                # Both hit in same candle - SL orders typically have priority
                exit_price, exit_type = sl_price, 'SL'
            elif sl_hit:
                exit_price, exit_type = sl_price, 'SL'
            elif tp_hit:
                exit_price, exit_type = tp_price, 'TP'

        return exit_price, exit_type

    def update_trailing_stop(self,
                           current_price: float,
                           entry_price: float,
                           initial_stop_loss: float,
                           position_side: PositionSide,
                           trail_activation_percent: float = 0.02,  # 2% activation
                           trail_distance_percent: float = 0.01,   # 1% trail distance
                           atr_value: Optional[float] = None) -> float:  # ATR for dynamic trailing
        """
        Update trailing stop based on price movement with ATR-based dynamic trailing.
        """
        if atr_value is not None:
            # Use ATR-based trailing for more dynamic adjustment
            dynamic_trail_distance = atr_value * 0.5  # Use half ATR as trailing distance
            trail_distance = max(dynamic_trail_distance, entry_price * trail_distance_percent)
        else:
            trail_distance = entry_price * trail_distance_percent

        if position_side == PositionSide.LONG:
            # For long positions, activate trailing stop when price moves favorably by activation percent
            activation_price = entry_price * (1 + trail_activation_percent)

            if current_price >= activation_price:
                # Trail behind the highest price seen after activation
                trailing_stop = current_price - trail_distance
                # Never move stop loss below initial level
                return max(initial_stop_loss, trailing_stop)
            else:
                # Not activated yet, keep initial stop
                return initial_stop_loss

        else:  # SHORT
            # For short positions, activate trailing stop when price moves favorably by activation percent
            activation_price = entry_price * (1 - trail_activation_percent)

            if current_price <= activation_price:
                # Trail ahead of the lowest price seen after activation
                trailing_stop = current_price + trail_distance
                # Never move stop loss above initial level
                return min(initial_stop_loss, trailing_stop)
            else:
                # Not activated yet, keep initial stop
                return initial_stop_loss

    def calculate_dynamic_levels(self,
                               entry_price: float,
                               position_side: PositionSide,
                               market_data: pd.DataFrame,
                               regime: RegimeType,
                               support_level: Optional[float] = None,
                               resistance_level: Optional[float] = None) -> SLTPLevels:
        """
        Calculate dynamic SL/TP levels based on market data analysis.
        """
        # Calculate ATR from market data
        atr_value = self._calculate_atr(market_data)
        
        # Calculate volatility
        volatility = self._calculate_volatility(market_data)
        
        # Calculate trend strength
        trend_strength = self._calculate_trend_strength(market_data)
        
        # Calculate levels using all advanced features
        return self.calculate_levels(
            entry_price=entry_price,
            position_side=position_side,
            atr_value=atr_value,
            regime=regime,
            support_level=support_level,
            resistance_level=resistance_level,
            volatility=volatility,
            trend_strength=trend_strength
        )

    def _calculate_atr(self, market_data: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average True Range from market data.
        """
        if len(market_data) < period:
            # Calculate from available data if not enough for full period
            period = len(market_data)
        
        if len(market_data) < 2:
            return 0.02 * market_data['close'].iloc[0] if len(market_data) > 0 else 1.0

        high = market_data['high'].values[-period:]
        low = market_data['low'].values[-period:]
        close = market_data['close'].values[-period:]
        
        # Calculate True Range
        tr = np.zeros(len(high))
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(high)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        return np.mean(tr)

    def _calculate_volatility(self, market_data: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate volatility from market data.
        """
        if len(market_data) < period:
            period = len(market_data)
        
        if len(market_data) < 2:
            return 0.02  # Default 2% volatility

        returns = np.log(market_data['close'] / market_data['close'].shift(1)).dropna().tail(period)
        return float(np.std(returns))

    def _calculate_trend_strength(self, market_data: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate trend strength using linear regression.
        """
        if len(market_data) < period:
            period = len(market_data)
        
        if len(market_data) < 5:
            return 0.0

        prices = market_data['close'].tail(period).values
        x = np.arange(len(prices))
        
        # Calculate slope and correlation
        slope, _, r_value, _, _ = stats.linregress(x, prices)
        
        # Normalize by price level and multiply by correlation strength
        trend_strength = (slope / np.mean(prices)) * r_value if np.mean(prices) > 0 else 0.0
        
        # Clamp to reasonable range
        return max(-1.0, min(1.0, trend_strength))


class SLTPValidationService:
    """
    Service to validate SL/TP levels before execution.
    """
    
    def __init__(self, sltp_manager: AdvancedSLTPManager):
        self.manager = sltp_manager

    def validate_levels(self,
                      entry_price: float,
                      sl_price: float,
                      tp_price: float,
                      position_side: PositionSide,
                      max_sl_distance_percent: float = 0.10,  # 10% max SL distance
                      min_tp_distance_percent: float = 0.01,  # 1% min TP distance
                      min_rr_ratio: float = 0.5,              # 1:2 minimum risk-reward
                      max_rr_ratio: float = 5.0) -> Tuple[bool, List[str]]:  # 1:5 maximum risk-reward
        """
        Validate SL/TP levels for reasonableness with realistic constraints.
        """
        issues = []

        # Check if SL and TP are on correct sides of entry
        if position_side == PositionSide.LONG:
            if sl_price >= entry_price:
                issues.append(f"SL ({sl_price}) must be below entry price ({entry_price}) for long position")
            if tp_price <= entry_price:
                issues.append(f"TP ({tp_price}) must be above entry price ({entry_price}) for long position")
        else:  # SHORT
            if sl_price <= entry_price:
                issues.append(f"SL ({sl_price}) must be above entry price ({entry_price}) for short position")
            if tp_price >= entry_price:
                issues.append(f"TP ({tp_price}) must be below entry price ({entry_price}) for short position")

        # Check distance reasonableness
        sl_distance_pct = abs(sl_price - entry_price) / entry_price
        tp_distance_pct = abs(tp_price - entry_price) / entry_price

        if sl_distance_pct > max_sl_distance_percent:
            issues.append(f"SL distance ({sl_distance_pct:.2%}) exceeds maximum allowed ({max_sl_distance_percent:.2%})")

        if tp_distance_pct < min_tp_distance_percent:
            issues.append(f"TP distance ({tp_distance_pct:.2%}) below minimum required ({min_tp_distance_percent:.2%})")

        # Check risk-reward ratio
        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
        rr_ratio = reward / risk if risk > 0 else float('inf')

        if rr_ratio < min_rr_ratio:
            issues.append(f"Risk-reward ratio ({rr_ratio:.2f}) too low, minimum recommended is {min_rr_ratio}")

        if rr_ratio > max_rr_ratio:
            issues.append(f"Risk-reward ratio ({rr_ratio:.2f}) too high, maximum recommended is {max_rr_ratio}. Unreachable targets may lead to unfilled orders.")

        # Additional validations for realistic levels
        if position_side == PositionSide.LONG:
            # For long positions, ensure SL is not too tight (at least few ATRs away)
            min_sl_distance = entry_price * 0.005  # Minimum 0.5% for realistic SL
            if abs(entry_price - sl_price) < min_sl_distance:
                issues.append(f"Stop loss too tight. Minimum recommended distance is 0.5% ({min_sl_distance:.2f})")
        else:  # SHORT
            # For short positions, ensure SL is not too tight
            min_sl_distance = entry_price * 0.005  # Minimum 0.5% for realistic SL
            if abs(entry_price - sl_price) < min_sl_distance:
                issues.append(f"Stop loss too tight. Minimum recommended distance is 0.5% ({min_sl_distance:.2f})")

        is_valid = len(issues) == 0
        return is_valid, issues


# Global instances
sltp_manager = AdvancedSLTPManager()
validation_service = SLTPValidationService(sltp_manager)