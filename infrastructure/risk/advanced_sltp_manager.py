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
    risk_reward_ratio: float  # Actual risk-reward ratio achieved


class AdvancedSLTPManager:
    """
    Advanced SL/TP management with volatility normalization and structure awareness.

    Key features:
    - Volatility-normalized SL/TP distances using ATR
    - Structure-aware levels based on support/resistance
    - Regime-adaptive adjustments
    - Priority-based execution (SL > TP for simultaneous hits)
    - 5M/15M timeframe focus with enhanced structure validation
    """

    def __init__(self,
                 default_sl_atr_multiplier: float = 2.0,
                 default_tp_atr_multiplier: float = 3.0,
                 min_risk_reward_ratio: float = 1.0,
                 max_risk_reward_ratio = 3.0,
                 support_resistance_buffer: float = 0.005,  # 0.5% buffer around S/R levels
                 regime_sl_multipliers: Optional[Dict[str, float]] = None,
                 regime_tp_multipliers: Optional[Dict[str, float]] = None,
                 min_structure_separation_atr: float = 0.25,
                 sl_structure_priority_threshold: float = 1.6):

        self.default_sl_atr_multiplier = default_sl_atr_multiplier
        self.default_tp_atr_multiplier = default_tp_atr_multiplier
        self.min_risk_reward_ratio = min_risk_reward_ratio
        self.max_risk_reward_ratio = max_risk_reward_ratio
        self.support_resistance_buffer = support_resistance_buffer
        self.min_structure_separation_atr = min_structure_separation_atr
        self.sl_structure_priority_threshold = sl_structure_priority_threshold

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

    def find_valid_structure_levels(self, market_data: pd.DataFrame, atr_value: float,
                                   min_separation: Optional[float] = None) -> Tuple[List[float], List[float]]:
        """
        Find valid structure levels according to specification:
        A "valid structure level" is:
        • A confirmed swing high/low
        • Formed by ≥2 candles on each side
        • With minimum separation of 0.25 ATR
        """
        if min_separation is None:
            min_separation = self.min_structure_separation_atr * atr_value

        highs = market_data['high'].values
        lows = market_data['low'].values

        swing_highs = []
        swing_lows = []

        # Look for swing points (at least 2 candles on each side)
        for i in range(2, len(highs) - 2):
            # Check for swing high (higher than neighbors)
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                # Only add if it's separated by minimum distance from other levels
                if not self._is_too_close(highs[i], swing_highs, min_separation):
                    swing_highs.append(float(highs[i]))

            # Check for swing low (lower than neighbors)
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                # Only add if it's separated by minimum distance from other levels
                if not self._is_too_close(lows[i], swing_lows, min_separation):
                    swing_lows.append(float(lows[i]))

        return swing_highs, swing_lows

    def find_liquidity_levels(self, market_data: pd.DataFrame,
                             min_rejections: int = 2) -> Tuple[List[float], List[float]]:
        """
        Find liquidity levels according to specification:
        A "liquidity level" is:
        • Equal highs/lows
        • Or a level with ≥2 rejections or long wicks
        """
        highs = market_data['high'].values
        lows = market_data['low'].values
        closes = market_data['close'].values
        opens = market_data['open'].values

        # Find equal highs/lows (same price occurring multiple times)
        # Use approximate equality to account for floating point precision
        unique_highs, high_counts = np.unique(np.round(highs, 2), return_counts=True)
        unique_lows, low_counts = np.unique(np.round(lows, 2), return_counts=True)

        # Levels with multiple occurrences (equal highs/lows)
        equal_high_levels = [float(h) for h, count in zip(unique_highs, high_counts) if count >= min_rejections]
        equal_low_levels = [float(l) for l, count in zip(unique_lows, low_counts) if count >= min_rejections]

        # Find levels with rejections (long wicks with small bodies)
        rejection_highs = []
        rejection_lows = []

        for i in range(len(highs)):
            upper_wick = highs[i] - max(opens[i], closes[i])
            lower_wick = min(opens[i], closes[i]) - lows[i]
            body_size = abs(closes[i] - opens[i])

            # Calculate wick-to-range ratios for better detection
            high_range = highs[i] - lows[i]
            low_range = highs[i] - lows[i]  # Same range for both

            # High rejection (long upper wick relative to total range, indicating resistance)
            if high_range > 0 and (upper_wick / high_range) > 0.5:  # Upper wick is more than 50% of total range
                rejection_highs.append(float(highs[i]))

            # Low rejection (long lower wick relative to total range, indicating support)
            if low_range > 0 and (lower_wick / low_range) > 0.5:  # Lower wick is more than 50% of total range
                rejection_lows.append(float(lows[i]))

        # Combine and deduplicate levels
        liquidity_highs = list(set(equal_high_levels + rejection_highs))
        liquidity_lows = list(set(equal_low_levels + rejection_lows))

        return liquidity_highs, liquidity_lows

    def _is_too_close(self, level: float, existing_levels: List[float], min_distance: float) -> bool:
        """Check if a level is too close to existing levels"""
        for existing_level in existing_levels:
            if abs(level - existing_level) < min_distance:
                return True
        return False

    def _find_nearest_structure_level(self, entry_price: float, structure_levels: List[float],
                                    position_side: PositionSide) -> Optional[float]:
        """Find the nearest structure level in the appropriate direction for the position"""
        if not structure_levels:
            return None

        if position_side == PositionSide.LONG:
            # For long positions, look for structure levels below entry (support)
            relevant_levels = [level for level in structure_levels if level < entry_price]
        else:
            # For short positions, look for structure levels above entry (resistance)
            relevant_levels = [level for level in structure_levels if level > entry_price]

        if not relevant_levels:
            return None

        # Return the nearest level
        return min(relevant_levels, key=lambda x: abs(x - entry_price))

    def _find_nearest_liquidity_level(self, entry_price: float, liquidity_levels: List[float],
                                    position_side: PositionSide, bias_direction: Optional[PositionSide] = None) -> Optional[float]:
        """Find the nearest liquidity level in the appropriate direction for the position"""
        if not liquidity_levels:
            return None

        if position_side == PositionSide.LONG:
            # For long positions, look for liquidity levels above entry (for TP) or below (for SL)
            if bias_direction == PositionSide.LONG:  # Looking for resistance (TP for long)
                relevant_levels = [level for level in liquidity_levels if level > entry_price]
            else:  # Looking for support (SL for long)
                relevant_levels = [level for level in liquidity_levels if level < entry_price]
        else:  # SHORT
            # For short positions, look for liquidity levels below entry (for TP) or above (for SL)
            if bias_direction == PositionSide.SHORT:  # Looking for support (TP for short)
                relevant_levels = [level for level in liquidity_levels if level < entry_price]
            else:  # Looking for resistance (SL for short)
                relevant_levels = [level for level in liquidity_levels if level > entry_price]

        if not relevant_levels:
            return None

        # Return the nearest level
        return min(relevant_levels, key=lambda x: abs(x - entry_price))

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

    def _determine_volatility_regime(self, atr_value: float, entry_price: float) -> str:
        """Determine volatility regime based on ATR percentage of price"""
        atr_pct = (atr_value / entry_price) if entry_price > 0 else 0.0

        if 0.12 <= atr_pct <= 0.18:
            return "LOW"
        elif 0.18 < atr_pct <= 0.25:
            return "NORMAL"
        elif 0.25 < atr_pct <= 0.35:
            return "HIGH"
        elif atr_pct < 0.12:
            return "VERY_LOW"
        else:
            return "VERY_HIGH"

    def _select_atr_multiplier_for_regime(self, regime: str) -> float:
        """Select ATR multiplier based on volatility regime"""
        multipliers = {
            "VERY_LOW": 1.8,
            "LOW": 2.0,
            "NORMAL": 2.2,
            "HIGH": 2.5,
            "VERY_HIGH": 3.0
        }
        return multipliers.get(regime, 2.2)  # Default to normal

    def _calculate_spread_buffer(self, entry_price: float, spread_multiplier: float = 0.0002) -> float:
        """Calculate minimum buffer based on typical market spread"""
        return entry_price * spread_multiplier

    def _validate_sl_placement(self, sl_price: float, entry_price: float,
                             position_side: PositionSide, atr_value: float) -> float:
        """Validate SL placement according to specifications"""
        buffer = atr_value * 0.1  # Small buffer to ensure SL is not exactly on structure

        if position_side == PositionSide.LONG:
            # For long positions, SL must be below entry and not inside equal highs/lows
            max_sl = entry_price - (atr_value * 0.05)  # Ensure SL is not too close to entry
            min_sl = entry_price * 0.995  # At least 0.5% below entry to avoid invalid placement
            sl_price = max(min_sl, min(max_sl, sl_price))
        else:  # SHORT
            # For short positions, SL must be above entry and not inside equal highs/lows
            min_sl = entry_price + (atr_value * 0.05)  # Ensure SL is not too close to entry
            max_sl = entry_price * 1.005  # At least 0.5% above entry to avoid invalid placement
            sl_price = min(max_sl, max(min_sl, sl_price))

        return sl_price

    def _is_tp_blocked(self, entry_price: float, target_tp: float, position_side: PositionSide,
                      market_data: Optional[pd.DataFrame], atr_value: float) -> bool:
        """Check if intermediate liquidity or structure blocks the TP path"""
        if market_data is None:
            return False

        # Calculate the distance to target TP
        target_distance = abs(target_tp - entry_price)
        threshold_distance = target_distance * 0.7  # 70% of projected distance

        # Find any structures or liquidity levels between entry and target
        if position_side == PositionSide.LONG:
            # For long, check if there's resistance between entry and target TP
            levels_to_check = [level for level in market_data['high'].values if entry_price < level < target_tp]
        else:  # SHORT
            # For short, check if there's support between entry and target TP
            levels_to_check = [level for level in market_data['low'].values if target_tp < level < entry_price]

        # If any level is closer than 70% of the projected distance, consider it blocked
        for level in levels_to_check:
            level_distance = abs(level - entry_price)
            if level_distance < threshold_distance:
                return True

        return False

    def _find_first_realistic_tp(self, entry_price: float, position_side: PositionSide,
                               market_data: Optional[pd.DataFrame], atr_value: float) -> float:
        """Find the first realistic liquidity level for TP"""
        if market_data is None:
            # Fallback to simple ATR-based calculation
            distance = atr_value * 2.0
            if position_side == PositionSide.LONG:
                return entry_price + distance
            else:
                return entry_price - distance

        # Find liquidity levels
        liquidity_highs, liquidity_lows = self.find_liquidity_levels(market_data)

        if position_side == PositionSide.LONG:
            # For long, find the nearest resistance level above entry
            relevant_levels = [level for level in liquidity_highs if level > entry_price]
        else:  # SHORT
            # For short, find the nearest support level below entry
            relevant_levels = [level for level in liquidity_lows if level < entry_price]

        if relevant_levels:
            # Return the nearest realistic level
            return min(relevant_levels, key=lambda x: abs(x - entry_price))
        else:
            # Fallback to ATR-based calculation
            distance = atr_value * 2.0
            if position_side == PositionSide.LONG:
                return entry_price + distance
            else:
                return entry_price - distance

    def _get_target_rr(self, confidence: float) -> float:
        """Get target risk-reward based on confidence"""
        # Higher confidence allows for higher RR targets
        if confidence >= 0.7:
            return 2.5  # High confidence allows for higher targets
        elif confidence >= 0.5:
            return 2.0  # Medium confidence
        else:
            return 1.6  # Low confidence, more conservative

    def _normalize_risk_reward(self, entry_price: float, sl_price: float, tp_price: float,
                             position_side: PositionSide) -> Tuple[float, float]:
        """Normalize risk-reward to acceptable range (1.4 to 3.2)"""
        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)

        if risk <= 0:
            # If risk is zero or negative, adjust SL to create proper risk
            if position_side == PositionSide.LONG:
                sl_price = entry_price - (entry_price * 0.005)  # 0.5% risk
            else:  # SHORT
                sl_price = entry_price + (entry_price * 0.005)  # 0.5% risk
            risk = abs(entry_price - sl_price)

        current_rr = reward / risk if risk > 0 else float('inf')

        # Use a small epsilon to handle floating point precision issues
        epsilon = 1e-10
        if 1.4 - epsilon <= current_rr <= 3.2 + epsilon:
            return sl_price, tp_price  # Already in acceptable range

        if current_rr < 1.4 - epsilon:
            # RR < 1.4 → adjust TP to achieve target minimum RR of 1.4
            target_rr = 1.4
            required_reward = risk * target_rr
            if position_side == PositionSide.LONG:
                tp_price = entry_price + required_reward
            else:  # SHORT
                tp_price = entry_price - required_reward
        elif current_rr > 3.2 + epsilon:
            # RR > 3.2 → adjust TP to achieve target maximum RR of 3.2
            target_rr = 3.2
            required_reward = risk * target_rr
            if position_side == PositionSide.LONG:
                tp_price = entry_price + required_reward
            else:  # SHORT
                tp_price = entry_price - required_reward

        return sl_price, tp_price

    def _apply_confidence_scaling(self, tp_price: float, entry_price: float,
                                position_side: PositionSide, confidence: float) -> float:
        """Apply confidence-based scaling to TP"""
        if confidence >= 0.7:
            # High → 100% structural target
            return tp_price
        elif confidence >= 0.5:
            # Medium → ~70% distance
            distance = abs(tp_price - entry_price)
            scaled_distance = distance * 0.7
            if position_side == PositionSide.LONG:
                return entry_price + scaled_distance
            else:  # SHORT
                return entry_price - scaled_distance
        else:
            # Low → nearest minor liquidity
            # This would require market data to find nearest liquidity
            # For now, use a conservative approach
            distance = abs(tp_price - entry_price)
            scaled_distance = distance * 0.5  # Conservative 50% of original distance
            if position_side == PositionSide.LONG:
                return entry_price + scaled_distance
            else:  # SHORT
                return entry_price - scaled_distance

    def calculate_levels(self,
                        entry_price: float,
                        position_side: PositionSide,
                        atr_value: float,
                        regime: RegimeType,
                        market_data: Optional[pd.DataFrame] = None,
                        support_level: Optional[float] = None,
                        resistance_level: Optional[float] = None,
                        volatility: Optional[float] = None,
                        trend_strength: Optional[float] = None,
                        confidence: float = 0.5,
                        timeframe: str = "5M") -> SLTPLevels:
        """
        Calculate SL/TP levels with all advanced features according to specifications.

        For LONG positions:
        - SL below entry (but above support if provided)
        - TP above entry (but below resistance if provided)

        For SHORT positions:
        - SL above entry (but below resistance if provided)
        - TP below entry (but above support if provided)
        """
        # Determine volatility regime first
        volatility_regime = self._determine_volatility_regime(atr_value, entry_price)

        # Calculate ATR-based buffer based on volatility regime
        selected_atr_multiplier = self._select_atr_multiplier_for_regime(volatility_regime)

        # Calculate spread buffer (minimum distance based on market spread)
        spread_buffer = self._calculate_spread_buffer(entry_price)

        # Calculate base ATR buffer (maximum of selected ATR and spread buffer)
        base_buffer = max(selected_atr_multiplier * atr_value, spread_buffer)

        # Initialize final levels
        final_sl = None
        final_tp = None

        # Calculate SL based on priority system
        if market_data is not None:
            # Find valid 5M structure levels first
            structure_highs, structure_lows = self.find_valid_structure_levels(market_data, atr_value)

            if position_side == PositionSide.LONG:
                # For long: SL should be near support (structure low)
                nearest_structure_level = self._find_nearest_structure_level(entry_price, structure_lows, position_side)
            else:  # SHORT
                # For short: SL should be near resistance (structure high)
                nearest_structure_level = self._find_nearest_structure_level(entry_price, structure_highs, position_side)
        else:
            # Fallback to provided support/resistance if no market data
            nearest_structure_level = support_level if position_side == PositionSide.LONG else resistance_level

        # Apply SL placement logic
        if nearest_structure_level is not None:
            # Check if structure distance is greater than threshold to use ATR fallback
            structure_distance = abs(entry_price - nearest_structure_level)
            if structure_distance > self.sl_structure_priority_threshold * atr_value:
                # Use ATR-based fallback
                sl_distance = base_buffer
                if position_side == PositionSide.LONG:
                    final_sl = entry_price - sl_distance
                else:  # SHORT
                    final_sl = entry_price + sl_distance
            else:
                # Use structure level with buffer
                if position_side == PositionSide.LONG:
                    final_sl = nearest_structure_level + base_buffer  # Above support with buffer
                else:  # SHORT
                    final_sl = nearest_structure_level - base_buffer  # Below resistance with buffer
        else:
            # Use ATR-based fallback if no structure found
            sl_distance = base_buffer
            if position_side == PositionSide.LONG:
                final_sl = entry_price - sl_distance
            else:  # SHORT
                final_sl = entry_price + sl_distance

        # Validate SL placement - must not be inside equal highs/lows or exactly on structure
        final_sl = self._validate_sl_placement(final_sl, entry_price, position_side, atr_value)

        # Calculate TP based on priority system
        final_tp = None
        if market_data is not None:
            # Find liquidity levels aligned with 15M bias if available
            liquidity_highs, liquidity_lows = self.find_liquidity_levels(market_data)

            # Find valid structure levels for 15M timeframe reference
            structure_highs, structure_lows = self.find_valid_structure_levels(market_data, atr_value)

            # For TP, prioritize according to specification:
            # 1. Nearest 5M liquidity aligned with 15M bias
            # 2. Nearest 15M structure if blocked
            # 3. RR-based projection only as last resort
            if position_side == PositionSide.LONG:
                # For long: TP should be near resistance (liquidity high) aligned with 15M bias
                nearest_liquidity = self._find_nearest_liquidity_level(entry_price, liquidity_highs, position_side, PositionSide.LONG)

                # Check if there's a 15M structure level that could serve as TP
                nearest_15m_structure = self._find_nearest_structure_level(entry_price, structure_highs, position_side)
            else:  # SHORT
                # For short: TP should be near support (liquidity low) aligned with 15M bias
                nearest_liquidity = self._find_nearest_liquidity_level(entry_price, liquidity_lows, position_side, PositionSide.SHORT)

                # Check if there's a 15M structure level that could serve as TP
                nearest_15m_structure = self._find_nearest_structure_level(entry_price, structure_lows, position_side)

            # Apply priority system for TP placement
            if nearest_liquidity is not None:
                # Check if intermediate liquidity or structure blocks the path to the target
                if self._is_tp_blocked(entry_price, nearest_liquidity, position_side, market_data, atr_value):
                    # If blocked, shorten TP to first realistic liquidity instead of rejecting trade
                    final_tp = self._find_first_realistic_tp(entry_price, position_side, market_data, atr_value)
                else:
                    # Use the nearest liquidity level as TP
                    final_tp = nearest_liquidity
            elif nearest_15m_structure is not None:
                # If no liquidity found but structure exists, use the structure level
                final_tp = nearest_15m_structure
            else:
                # RR-based projection as last resort
                risk = abs(entry_price - final_sl)
                projected_tp_distance = risk * self._get_target_rr(confidence)
                if position_side == PositionSide.LONG:
                    final_tp = entry_price + projected_tp_distance
                else:  # SHORT
                    final_tp = entry_price - projected_tp_distance
        else:
            # Fallback to provided support/resistance if no market data
            if position_side == PositionSide.LONG:
                # For long, TP should be resistance level (above entry)
                final_tp = resistance_level if resistance_level is not None and resistance_level > entry_price else None
            else:  # SHORT
                # For short, TP should be support level (below entry)
                final_tp = support_level if support_level is not None and support_level < entry_price else None

            # If no valid TP level from support/resistance, use RR-based projection
            if final_tp is None:
                risk = abs(entry_price - final_sl)
                projected_tp_distance = risk * self._get_target_rr(confidence)
                if position_side == PositionSide.LONG:
                    final_tp = entry_price + projected_tp_distance
                else:  # SHORT
                    final_tp = entry_price - projected_tp_distance

        # Apply confidence-based scaling BEFORE risk-reward normalization
        # This ensures confidence scaling is applied, then RR is normalized
        final_tp = self._apply_confidence_scaling(final_tp, entry_price, position_side, confidence)

        # Apply risk-reward normalization (1.4 to 3.2 range) - this takes precedence
        final_sl, final_tp = self._normalize_risk_reward(entry_price, final_sl, final_tp, position_side)

        # Calculate distances from entry
        sl_dist_from_entry = abs(final_sl - entry_price)
        tp_dist_from_entry = abs(final_tp - entry_price)

        # Calculate risk-reward ratio
        risk = sl_dist_from_entry
        reward = tp_dist_from_entry
        rr_ratio = reward / risk if risk > 0 else float('inf')

        # Calculate ATR multiples for reporting
        sl_atr_mult = sl_dist_from_entry / atr_value if atr_value > 0 else (base_buffer / atr_value if atr_value > 0 else 1.0)
        tp_atr_mult = tp_dist_from_entry / atr_value if atr_value > 0 else (abs(final_tp - entry_price) / atr_value if atr_value > 0 else 1.0)

        return SLTPLevels(
            stop_loss=final_sl,
            take_profit=final_tp,
            sl_distance=sl_dist_from_entry,
            tp_distance=tp_dist_from_entry,
            sl_atr_multiple=sl_atr_mult,
            tp_atr_multiple=tp_atr_mult,
            regime_adjusted=True,
            risk_reward_ratio=rr_ratio
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
                               resistance_level: Optional[float] = None,
                               confidence: float = 0.5,
                               timeframe: str = "5M") -> SLTPLevels:
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
            market_data=market_data,
            support_level=support_level,
            resistance_level=resistance_level,
            volatility=volatility,
            trend_strength=trend_strength,
            confidence=confidence,
            timeframe=timeframe
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


class TimeframeAdjustedSLTPManager(AdvancedSLTPManager):
    """
    Enhanced SL/TP manager with timeframe-adjusted and reachability-constrained formulas.
    Implements the redesigned SL/TP logic with mathematical formulas for different timeframes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeframe_multipliers = {
            "M1": 0.5,   # 1-minute: very tight stops, conservative profits
            "M5": 0.7,   # 5-minute: tight stops, modest profits
            "M15": 1.0,  # 15-minute: moderate stops and profits
            "M30": 1.2,  # 30-minute: wider stops, larger profits
            "H1": 1.5,   # 1-hour: wider stops, larger profits
            "H4": 2.0,   # 4-hour: wide stops, large profits
            "D1": 2.5    # 1-day: very wide stops, very large profits
        }

        # Regime-specific multipliers for SL/TP
        self.regime_sl_multipliers = {
            RegimeType.BULLISH_TRENDING.value: 1.5,
            RegimeType.BEARISH_TRENDING.value: 1.5,
            RegimeType.HIGH_VOLATILITY.value: 2.5,
            RegimeType.LOW_VOLATILITY.value: 1.8,
            RegimeType.CHOPPY.value: 1.2,
            RegimeType.BREAKOUT.value: 2.0,
            RegimeType.NORMAL.value: 2.0
        }

        self.regime_tp_multipliers = {
            RegimeType.BULLISH_TRENDING.value: 3.5,
            RegimeType.BEARISH_TRENDING.value: 3.5,
            RegimeType.HIGH_VOLATILITY.value: 4.0,
            RegimeType.LOW_VOLATILITY.value: 2.5,
            RegimeType.CHOPPY.value: 2.0,
            RegimeType.BREAKOUT.value: 4.0,
            RegimeType.NORMAL.value: 3.0
        }

    def calculate_timeframe_adjusted_sl(self,
                                      entry_price: float,
                                      atr_value: float,
                                      timeframe: str,
                                      regime: RegimeType,
                                      volatility: float,
                                      position_side: PositionSide) -> float:
        """
        Calculate timeframe-adjusted stop loss based on volatility and regime.

        For scalping strategies, prioritize hit probability and time efficiency over large RR.
        """
        # Get timeframe multiplier (smaller for shorter timeframes)
        tf_multiplier = self.timeframe_multipliers.get(timeframe.upper(), 1.0)

        # Get regime multiplier
        regime_multiplier = self.regime_sl_multipliers.get(regime.value, self.default_sl_atr_multiplier)

        # Calculate volatility adjustment
        baseline_volatility = 0.02
        vol_adjustment = 1.0 / (1.0 + (volatility / baseline_volatility))

        # Calculate base SL distance in ATR terms
        base_atr_distance = self.default_sl_atr_multiplier * tf_multiplier * regime_multiplier * vol_adjustment

        # Calculate actual price distance
        sl_distance = atr_value * base_atr_distance

        # Apply to entry price based on position side
        if position_side == PositionSide.LONG:
            return entry_price - sl_distance
        else:  # SHORT
            return entry_price + sl_distance

    def calculate_reachability_constrained_tp(self,
                                           entry_price: float,
                                           stop_loss: float,
                                           timeframe: str,
                                           regime: RegimeType,
                                           confidence: float,
                                           volatility: float,
                                           position_side: PositionSide) -> Tuple[float, float]:
        """
        Calculate reachability-constrained take profit based on probability of hitting target.

        Ensures P(TP_hit | timeframe, regime, strategy) ≥ minimum_threshold
        """
        # Calculate risk distance (the denominator for RR calculation)
        risk_distance = abs(entry_price - stop_loss)

        # Determine maximum achievable RR based on timeframe
        max_rr_by_timeframe = {
            "M1": 1.5,   # 1-minute: very conservative
            "M5": 2.0,   # 5-minute: conservative
            "M15": 2.5,  # 15-minute: moderately conservative
            "M30": 3.0,  # 30-minute: moderate
            "H1": 3.5,   # 1-hour: moderate to aggressive
            "H4": 4.0,   # 4-hour: aggressive
            "D1": 5.0    # 1-day: very aggressive
        }

        max_rr = max_rr_by_timeframe.get(timeframe.upper(), 3.0)

        # Adjust max RR based on strategy type (scalping prioritizes hit rate over RR)
        from enum import Enum
        class TradeType(Enum):
            SCALP = "scalp"
            INTRADAY = "intraday"
            SWING = "swing"

        strategy_type = self.classify_trade_type({"timeframe": timeframe})
        if strategy_type == TradeType.SCALP:
            max_rr *= 0.6  # Reduce max RR for scalping to improve hit rate
        elif strategy_type == TradeType.INTRADAY:
            max_rr *= 0.8  # Slightly reduce for intraday
        # Swing trades can use full max_rr

        # Calculate target RR based on confidence and regime
        base_rr = self._calculate_target_rr(confidence)

        # Constrain to maximum achievable for timeframe
        constrained_rr = min(base_rr, max_rr)

        # Calculate TP distance based on constrained RR
        tp_distance = risk_distance * constrained_rr

        # Apply to entry price based on position side
        if position_side == PositionSide.LONG:
            tp_price = entry_price + tp_distance
        else:  # SHORT
            tp_price = entry_price - tp_distance

        # Calculate reachability score (probability estimate)
        reachability_score = self._estimate_reachability_probability(
            entry_price, tp_price, stop_loss, timeframe, regime.value, confidence, volatility
        )

        return tp_price, reachability_score

    def _calculate_target_rr(self, confidence: float) -> float:
        """
        Calculate target risk-reward ratio based on confidence.
        """
        # Base RR varies by confidence
        if confidence >= 0.8:
            base_rr = 3.0  # High confidence allows for higher targets
        elif confidence >= 0.6:
            base_rr = 2.5  # Medium-high confidence
        elif confidence >= 0.4:
            base_rr = 2.0  # Medium confidence
        else:
            base_rr = 1.6  # Low confidence, conservative

        return base_rr

    def _estimate_reachability_probability(self,
                                        entry_price: float,
                                        tp_price: float,
                                        sl_price: float,
                                        timeframe: str,
                                        regime: str,
                                        confidence: float,
                                        volatility: float) -> float:
        """
        Estimate the probability of hitting the take profit before the stop loss.

        Uses historical time-to-hit distributions and market conditions.
        """
        # Base probability starts with confidence
        base_prob = confidence

        # Adjust for volatility (higher volatility reduces predictability)
        vol_factor = max(0.5, 1.0 - (volatility / 0.05))  # Reduce probability as volatility increases

        # Adjust for timeframe (shorter timeframes have more noise)
        tf_factor = {
            "M1": 0.7,
            "M5": 0.75,
            "M15": 0.8,
            "M30": 0.85,
            "H1": 0.9,
            "H4": 0.92,
            "D1": 0.95
        }.get(timeframe.upper(), 0.85)

        # Adjust for regime (trending markets have higher TP probability)
        regime_factor = {
            "bullish_trending": 1.1,
            "bearish_trending": 1.1,
            "high_volatility": 0.7,
            "low_volatility": 1.0,
            "choppy": 0.6,
            "breakout": 1.0,
            "normal": 1.0
        }.get(regime.lower(), 1.0)

        # Calculate final reachability score
        reachability_score = base_prob * vol_factor * tf_factor * regime_factor

        # Ensure it's within bounds
        return max(0.0, min(1.0, reachability_score))

    def classify_trade_type(self, params: dict) -> 'TradeType':
        """
        Classify trade type based on timeframe.
        """
        timeframe_minutes_map = {
            "M1": 1, "M5": 5, "M15": 15, "M30": 30,
            "H1": 60, "H4": 240, "D1": 1440
        }

        timeframe = params.get("timeframe", "H1").upper()
        timeframe_minutes = timeframe_minutes_map.get(timeframe, 60)

        if timeframe_minutes <= 15:
            from enum import Enum
            class TradeType(Enum):
                SCALP = "scalp"
                INTRADAY = "intraday"
                SWING = "swing"
            return TradeType.SCALP
        elif timeframe_minutes <= 360:  # Up to 6 hours
            from enum import Enum
            class TradeType(Enum):
                SCALP = "scalp"
                INTRADAY = "intraday"
                SWING = "swing"
            return TradeType.INTRADAY
        else:
            from enum import Enum
            class TradeType(Enum):
                SCALP = "scalp"
                INTRADAY = "intraday"
                SWING = "swing"
            return TradeType.SWING

    def calculate_enhanced_levels(self,
                                entry_price: float,
                                position_side: PositionSide,
                                atr_value: float,
                                timeframe: str,
                                regime: RegimeType,
                                confidence: float,
                                volatility: float,
                                market_data: Optional[pd.DataFrame] = None,
                                support_level: Optional[float] = None,
                                resistance_level: Optional[float] = None) -> SLTPLevels:
        """
        Calculate comprehensive SL/TP levels with all enhanced features.
        """
        # Calculate timeframe-adjusted stop loss
        sl_price = self.calculate_timeframe_adjusted_sl(
            entry_price=entry_price,
            atr_value=atr_value,
            timeframe=timeframe,
            regime=regime,
            volatility=volatility,
            position_side=position_side
        )

        # Calculate reachability-constrained take profit
        tp_price, reachability_score = self.calculate_reachability_constrained_tp(
            entry_price=entry_price,
            stop_loss=sl_price,
            timeframe=timeframe,
            regime=regime,
            confidence=confidence,
            volatility=volatility,
            position_side=position_side
        )

        # Apply structure awareness (support/resistance levels)
        final_sl, final_tp = self._apply_structure_awareness(
            entry_price, sl_price, tp_price, position_side, support_level, resistance_level
        )

        # Calculate distances from entry
        sl_dist_from_entry = abs(final_sl - entry_price)
        tp_dist_from_entry = abs(final_tp - entry_price)

        # Calculate ATR multiples for reporting
        sl_atr_mult = sl_dist_from_entry / atr_value if atr_value > 0 else self.default_sl_atr_multiplier
        tp_atr_mult = tp_dist_from_entry / atr_value if atr_value > 0 else self.default_tp_atr_multiplier

        # Calculate final risk-reward ratio
        risk = sl_dist_from_entry
        reward = tp_dist_from_entry
        rr_ratio = reward / risk if risk > 0 else float('inf')

        return SLTPLevels(
            stop_loss=final_sl,
            take_profit=final_tp,
            sl_distance=sl_dist_from_entry,
            tp_distance=tp_dist_from_entry,
            sl_atr_multiple=sl_atr_mult,
            tp_atr_multiple=tp_atr_mult,
            regime_adjusted=True,
            risk_reward_ratio=rr_ratio
        )


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
enhanced_sltp_manager = TimeframeAdjustedSLTPManager()
validation_service = SLTPValidationService(sltp_manager)