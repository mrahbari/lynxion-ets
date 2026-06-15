"""
Infrastructure implementation of the Trend Follow Strategy following hexagonal architecture.
"""
from typing import List, Optional, Dict, Any
from domain.entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import numpy as np
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class TrendFollowStrategyAdapter(BaseStrategyAdapter):
    """Established regime trend following strategy with structure validation"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("TrendFollow")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_trend_following_config
        system_config = get_trend_following_config()

        # Merge with any passed config, prioritizing passed config
        self.config = {**system_config.get('parameters', {}), **(config or {})}

        # Use configuration values or defaults
        self.lookback_period = self.config.get("lookback_period", 50)
        self.ma_type = self.config.get("ma_type", "EMA")
        self.ma_period = self.config.get("ma_period", 20)
        self.trend_strength_threshold = self.config.get("trend_strength_threshold", 0.01)

        # Parameters for established trend detection
        self.structure_window = self.config.get("structure_window", 20)  # Window to check for higher highs/lower lows
        self.pullback_threshold = self.config.get("pullback_threshold", 0.005)  # Threshold to identify pullbacks
        self.chop_threshold = self.config.get("chop_threshold", 0.002)  # Threshold to identify choppy markets

    def _is_established_trend(self, highs: List[float], lows: List[float], closes: List[float]) -> Dict[str, Any]:
        """Check if there's an established trend with higher-highs/higher-lows or lower-lows/lower-highs"""
        if len(highs) < self.structure_window:
            return {"is_established": False, "direction": None, "strength": 0}

        # Look for higher highs and higher lows (bullish trend)
        bullish_count = 0
        bearish_count = 0

        # Check for structure in segments
        segment_size = max(5, self.structure_window // 4)  # Divide window into segments

        for i in range(segment_size, len(highs[-self.structure_window:]), segment_size):
            if i + segment_size >= len(highs[-self.structure_window:]):
                break

            # Get early and late segments
            early_segment = highs[-self.structure_window:-self.structure_window+i]
            late_segment = highs[-self.structure_window+i:-self.structure_window+i+segment_size]

            if len(early_segment) > 0 and len(late_segment) > 0:
                early_high = max(early_segment)
                late_high = max(late_segment)

                if late_high > early_high:
                    bullish_count += 1
                elif late_high < early_high:
                    bearish_count += 1

        # Check lows as well
        for i in range(segment_size, len(lows[-self.structure_window:]), segment_size):
            if i + segment_size >= len(lows[-self.structure_window:]):
                break

            # Get early and late segments
            early_segment = lows[-self.structure_window:-self.structure_window+i]
            late_segment = lows[-self.structure_window+i:-self.structure_window+i+segment_size]

            if len(early_segment) > 0 and len(late_segment) > 0:
                early_low = min(early_segment)
                late_low = min(late_segment)

                if late_low > early_low:
                    bullish_count += 1
                elif late_low < early_low:
                    bearish_count += 1

        # Determine trend based on structure
        trend_strength = abs(bullish_count - bearish_count) / max(1, (bullish_count + bearish_count))

        is_bullish = bullish_count > bearish_count and bullish_count >= 2
        is_bearish = bearish_count > bullish_count and bearish_count >= 2

        if is_bullish:
            return {"is_established": True, "direction": "BULLISH", "strength": trend_strength}
        elif is_bearish:
            return {"is_established": True, "direction": "BEARISH", "strength": trend_strength}
        else:
            return {"is_established": False, "direction": None, "strength": 0}

    def _is_choppy_market(self, highs: List[float], lows: List[float], closes: List[float]) -> bool:
        """Check if the market is choppy with overlapping price action"""
        if len(closes) < 10:
            return False

        # Calculate average true range as a measure of volatility
        atr_values = []
        for i in range(1, min(10, len(highs))):
            tr = max(
                highs[-i] - lows[-i],  # Current high - low
                abs(highs[-i] - closes[-i-1]) if i+1 < len(closes) else 0,  # High - prev close
                abs(lows[-i] - closes[-i-1]) if i+1 < len(closes) else 0   # Low - prev close
            )
            atr_values.append(tr)

        if not atr_values:
            return False

        avg_atr = sum(atr_values) / len(atr_values)
        current_price = closes[-1] if closes else 1.0

        # Calculate the range of recent prices
        recent_range = max(closes[-10:]) - min(closes[-10:]) if len(closes) >= 10 else 0

        # Get choppiness parameters from config
        choppiness_atr_multiplier = self.config.get("choppiness_atr_multiplier", 0.5)
        max_overlapping_candles = self.config.get("max_overlapping_candles", 6)

        # If the recent range is small relative to the ATR, it might be choppy
        # Also check if there are many overlapping candles
        overlapping_count = 0
        for i in range(1, min(10, len(closes))):
            if abs(closes[-i] - closes[-i-1]) < avg_atr * choppiness_atr_multiplier:  # Less than configured ATR movement
                overlapping_count += 1

        # Market is considered choppy if:
        # 1. Recent range is small relative to ATR, OR
        # 2. Many overlapping candles
        return (recent_range / current_price < self.chop_threshold) or (overlapping_count > max_overlapping_candles)

    def _is_pullback_opportunity(self, closes: List[float], trend_direction: str) -> bool:
        """Check if current price represents a pullback opportunity in the trend direction"""
        if len(closes) < 5:
            return False

        current_price = closes[-1]
        recent_high = max(closes[-5:])
        recent_low = min(closes[-5:])

        # Get pullback thresholds from config
        pullback_min_threshold = self.config.get("pullback_min_threshold", self.pullback_threshold)
        pullback_max_threshold = self.config.get("pullback_max_threshold", 0.8)

        if trend_direction == "BULLISH":
            # For bullish trend, check if price is pulling back from recent high
            pullback_ratio = (recent_high - current_price) / (recent_high - recent_low) if recent_high != recent_low else 0.5
            return pullback_min_threshold < pullback_ratio < pullback_max_threshold  # Good pullback zone
        elif trend_direction == "BEARISH":
            # For bearish trend, check if price is pulling back from recent low
            pullback_ratio = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
            return pullback_min_threshold < pullback_ratio < pullback_max_threshold  # Good pullback zone
        else:
            return False

    def _is_at_trend_extremes(self, closes: List[float], trend_direction: str) -> bool:
        """Check if current price is at trend extremes (to avoid entry)"""
        if len(closes) < 10:
            return False

        current_price = closes[-1]
        recent_high = max(closes[-10:])
        recent_low = min(closes[-10:])

        # Get extreme threshold from config. 0.99 blocks entry whenever price is
        # within 1% of the 10-bar high — on the configured 1m timeframe that is
        # nearly every bar (BUYs would need a ≥1% dip, rare on 1m) → signal
        # starvation. 0.999 (within 0.1% of high) is the 1m-appropriate "avoid the
        # very top" calibration, preserving the intent.
        trend_extreme_threshold = self.config.get("trend_extreme_threshold", 0.999)

        if trend_direction == "BULLISH":
            # Check if we're near the recent high (extreme)
            return (current_price / recent_high) > trend_extreme_threshold  # Within threshold of recent high
        elif trend_direction == "BEARISH":
            # Check if we're near the recent low (extreme)
            return (recent_low / current_price) > trend_extreme_threshold  # Within threshold of recent low
        else:
            return False

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal using established regime trend following logic with structure validation"""
        if len(self.data_buffer) < max(self.ma_period + 1, self.structure_window):
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least {max(self.ma_period + 1, self.structure_window)}")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]

            if len(closes) < max(self.ma_period + 1, self.structure_window):
                self.logger.debug(f"Not enough close prices for {self.name}: {len(closes)}")
                return None

            # Calculate trend indicators
            current_price = closes[-1]

            # Check if market is choppy (block trades if true)
            if self._is_choppy_market(highs, lows, closes):
                self.logger.debug(f"Choppy market detected for {self.name}, blocking trade")
                return None

            # Check if there's an established trend with proper structure
            trend_info = self._is_established_trend(highs, lows, closes)

            if not trend_info["is_established"]:
                self.logger.debug(f"No established trend detected for {self.name}")
                return None

            # Calculate moving averages for secondary confirmation
            calculated_ma_short = self.calculate_ema(closes, self.ma_period)
            calculated_ma_long = self.calculate_ema(closes, min(self.lookback_period, len(closes)))

            if not calculated_ma_short or not calculated_ma_long:
                self.logger.debug(f"Could not calculate moving averages for {self.name}")
                return None

            # Confirm trend direction aligns with moving average relationship
            ma_trend_direction = "BULLISH" if calculated_ma_short > calculated_ma_long else "BEARISH"
            if ma_trend_direction != trend_info["direction"]:
                self.logger.debug(f"Trend structure and MA direction mismatch for {self.name}")
                return None

            # Calculate momentum
            momentum_period = min(10, len(closes) - 1)
            if momentum_period > 0 and len(closes) > momentum_period:
                computed_momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1]
            else:
                computed_momentum = 0

            # Determine signal based on established trend criteria
            final_signal_type = SignalType.HOLD
            final_confidence_factor = self.config.get("default_confidence_factor", 0.3)
            final_score = 0.0

            # Only enter if:
            # 1. There's an established trend with proper structure
            # 2. We're in a pullback opportunity (not at extremes)
            # 3. Momentum is in the right direction
            trend_direction = trend_info["direction"]

            if (trend_direction and
                self._is_pullback_opportunity(closes, trend_direction) and
                not self._is_at_trend_extremes(closes, trend_direction)):

                # Bullish setup: established uptrend with pullback opportunity
                if trend_direction == "BULLISH" and computed_momentum > 0:
                    final_signal_type = SignalType.BUY
                    # Confidence based on trend strength and pullback quality
                    confidence_trend = min(1.0, trend_info["strength"] * 2)
                    confidence_momentum = min(1.0, abs(computed_momentum) * 10)
                    final_confidence_factor = (confidence_trend + confidence_momentum) / 2
                    final_score = min(1.0, computed_momentum * 10)

                # Bearish setup: established downtrend with pullback opportunity
                elif trend_direction == "BEARISH" and computed_momentum < 0:
                    final_signal_type = SignalType.SELL
                    # Confidence based on trend strength and pullback quality
                    confidence_trend = min(1.0, trend_info["strength"] * 2)
                    confidence_momentum = min(1.0, abs(computed_momentum) * 10)
                    final_confidence_factor = (confidence_trend + confidence_momentum) / 2
                    final_score = max(-1.0, computed_momentum * 10)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                timestamp=datetime.now(),
                source_layer="EstablishedRegimeTrendFollow",
                metadata={
                    "trend_direction": trend_info["direction"],
                    "trend_strength": trend_info["strength"],
                    "is_established_trend": trend_info["is_established"],
                    "momentum": computed_momentum,
                    "ma_short": calculated_ma_short,
                    "ma_long": calculated_ma_long,
                    "current_price": current_price,
                    "is_pullback_opportunity": self._is_pullback_opportunity(closes, trend_info["direction"]) if trend_info["direction"] else False,
                    "is_at_trend_extremes": self._is_at_trend_extremes(closes, trend_info["direction"]) if trend_info["direction"] else False,
                    "is_choppy_market": self._is_choppy_market(highs, lows, closes),
                    "established_trend_checked": True,
                    "choppy_market_filtered": True,
                    "pullback_opportunity_checked": True,
                    "trend_extremes_filtered": True
                }
            )

            # Log signal if generated
            if final_signal_type != SignalType.HOLD:
                self.logger.info(f"{self.name} generated signal: {signal.signal_type.name} with confidence {float(signal.confidence.value):.3f} for {symbol.value}")
                self.logger.info(f"Established {trend_info['direction'].lower()} trend with strength {trend_info['strength']:.2f}")

            return signal

        except Exception as e:
            self.logger.error(f"Error in {self.name} strategy: {e}")
            import traceback
            traceback.print_exc()
            return None