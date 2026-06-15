"""
Infrastructure implementation of the Momentum Strategy following hexagonal architecture.
Ensures momentum trades only occur when continuation probability is high.
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


class MomentumStrategyAdapter(BaseStrategyAdapter):
    """High continuation probability momentum strategy with sustainability validation"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Momentum")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_momentum_config
        system_config = get_momentum_config()

        # Merge with any passed config, prioritizing passed config
        self.config = {**system_config.get('parameters', {}), **(config or {})}

        # Use configuration values or defaults
        self.lookback_period = self.config.get("lookback_period", 20)
        self.momentum_window = self.config.get("momentum_window", 5)
        self.continuation_threshold = self.config.get("continuation_threshold", 0.01)

        # Parameters for momentum persistence validation
        self.persistence_window = self.config.get("persistence_window", 10)  # Number of periods to validate momentum persistence
        self.min_persistence_bars = self.config.get("min_persistence_bars", 3)  # Minimum bars where momentum should persist
        self.exhaustion_threshold = self.config.get("exhaustion_threshold", 0.005)  # Threshold to detect momentum exhaustion

    def _calculate_rate_of_change(self, prices: List[float], period: int) -> float:
        """Calculate rate of change for momentum measurement"""
        if len(prices) < period + 1:
            return 0.0
        
        return (prices[-1] - prices[-period-1]) / prices[-period-1] if prices[-period-1] != 0 else 0.0

    def _validate_momentum_persistence(self, closes: List[float]) -> Dict[str, Any]:
        """Validate that momentum has persisted across multiple periods"""
        if len(closes) < self.persistence_window + self.momentum_window:
            return {"persistence_valid": False, "avg_momentum": 0.0, "momentum_consistency": 0.0}

        # Calculate momentum for each period in the persistence window
        momentums = []
        for i in range(self.momentum_window, self.persistence_window):
            if len(closes) > i + self.momentum_window:
                roc = self._calculate_rate_of_change(closes[-i-1:], self.momentum_window)
                momentums.append(roc)

        if not momentums:
            return {"persistence_valid": False, "avg_momentum": 0.0, "momentum_consistency": 0.0}

        avg_momentum = sum(momentums) / len(momentums)
        momentum_signs = [1 if m >= 0 else -1 for m in momentums]
        
        # Calculate consistency (same direction)
        same_direction_count = sum(1 for sign in momentum_signs if sign == momentum_signs[0])
        consistency = same_direction_count / len(momentum_signs) if momentum_signs else 0.0

        # Check if momentum has been consistent in the same direction
        persistence_valid = (
            consistency >= 0.6 and  # At least 60% of periods in same direction
            len([m for m in momentums if abs(m) >= self.continuation_threshold]) >= self.min_persistence_bars  # Minimum strong momentum bars
        )

        return {
            "persistence_valid": persistence_valid,
            "avg_momentum": avg_momentum,
            "momentum_consistency": consistency,
            "momentum_values": momentums
        }

    def _detect_momentum_exhaustion(self, highs: List[float], lows: List[float], closes: List[float]) -> bool:
        """Detect signs of momentum exhaustion"""
        if len(closes) < 5:
            return False

        # Check for exhaustion patterns in recent bars
        recent_bars = min(5, len(closes))
        recent_closes = closes[-recent_bars:]
        recent_highs = highs[-recent_bars:]
        recent_lows = lows[-recent_bars:]

        # Calculate momentum deceleration
        if len(recent_closes) >= 3:
            # Compare recent momentum changes
            momentum_changes = [
                (recent_closes[i] - recent_closes[i-1]) / recent_closes[i-1] if recent_closes[i-1] != 0 else 0
                for i in range(1, len(recent_closes))
            ]
            
            if len(momentum_changes) >= 2:
                # Check if momentum is decelerating rapidly
                recent_acceleration = momentum_changes[-1] - (momentum_changes[-2] if len(momentum_changes) > 1 else 0)
                
                # If acceleration is negative and significant, momentum may be exhausting
                if recent_acceleration < -self.exhaustion_threshold:
                    return True

        # Check for price rejection patterns that indicate exhaustion
        current_price = closes[-1]
        prev_price = closes[-2] if len(closes) > 1 else current_price
        
        # If price moved significantly but reversed (signs of exhaustion)
        price_move = abs(current_price - prev_price) / prev_price if prev_price != 0 else 0
        if price_move > 0.02:  # Significant move (>2%)
            # Check if current bar shows rejection (long wick, close opposite to move direction)
            bar_range = recent_highs[-1] - recent_lows[-1] if len(recent_highs) > 0 and len(recent_lows) > 0 else 0
            if bar_range > 0:
                upper_wick = recent_highs[-1] - max(current_price, prev_price)
                lower_wick = min(current_price, prev_price) - recent_lows[-1]
                
                # If there's a long wick in the direction of the move, it could indicate exhaustion
                if (prev_price < current_price and upper_wick / bar_range > 0.6) or \
                   (prev_price > current_price and lower_wick / bar_range > 0.6):
                    return True

        return False

    def _assess_continuation_probability(self, closes: List[float], current_momentum: float) -> float:
        """Assess the probability that momentum will continue"""
        if len(closes) < self.lookback_period:
            return 0.3  # Default low-medium probability if insufficient data

        # Calculate various factors that influence continuation
        recent_momentum = self._calculate_rate_of_change(closes[-5:], 3)
        medium_term_momentum = self._calculate_rate_of_change(closes[-10:], 7)
        
        # Factor 1: Consistency of momentum direction
        direction_consistency_weight = self.config.get("direction_consistency_weight", 0.3)
        direction_consistency = 1.0 if (current_momentum > 0) == (recent_momentum > 0) else self.config.get("direction_inconsistency_penalty", 0.3)

        # Factor 2: Strength relative to recent history
        avg_recent_momentum = np.mean([
            self._calculate_rate_of_change(closes[-i-3:-i], 3)
            for i in range(1, min(5, len(closes)-3))
            if len(closes) > i+3
        ] or [0])

        min_strength_factor = self.config.get("min_strength_factor", 0.1)
        strength_factor = min(1.0, max(min_strength_factor, abs(current_momentum) / (abs(avg_recent_momentum) + 0.0001)))

        # Factor 3: Momentum acceleration/deceleration
        min_data_for_acceleration = self.config.get("min_data_for_acceleration", 7)
        acceleration_base = self.config.get("acceleration_base", 0.7)
        acceleration_impact = self.config.get("acceleration_impact", 0.3)
        min_acceleration_factor = self.config.get("min_acceleration_factor", 0.1)
        default_acceleration_factor = self.config.get("default_acceleration_factor", 0.5)

        if len(closes) >= min_data_for_acceleration:  # Need enough data for acceleration calculation
            prev_momentum = self._calculate_rate_of_change(closes[-6:-1], 3)
            acceleration = current_momentum - prev_momentum
            acceleration_factor = acceleration_base + (acceleration / abs(current_momentum)) * acceleration_impact if current_momentum != 0 else acceleration_base
            acceleration_factor = max(min_acceleration_factor, min(1.0, acceleration_factor))
        else:
            acceleration_factor = default_acceleration_factor

        # Combine factors with weighted average
        direction_weight = self.config.get("direction_weight", 0.3)
        strength_weight = self.config.get("strength_weight", 0.3)
        acceleration_weight = self.config.get("acceleration_weight", 0.4)

        continuation_prob = (
            direction_consistency * direction_weight +
            strength_factor * strength_weight +
            acceleration_factor * acceleration_weight
        )

        return continuation_prob

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal using high continuation probability momentum logic"""
        if len(self.data_buffer) < max(self.lookback_period, self.momentum_window + 5):
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least {max(self.lookback_period, self.momentum_window + 5)}")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]

            if len(closes) < max(self.lookback_period, self.momentum_window + 5):
                self.logger.debug(f"Not enough close prices for {self.name}: {len(closes)}")
                return None

            current_price = closes[-1]

            # Calculate current momentum
            current_momentum = self._calculate_rate_of_change(closes, self.momentum_window)

            # Validate momentum persistence
            persistence_validation = self._validate_momentum_persistence(closes)

            # Check for momentum exhaustion
            momentum_exhausted = self._detect_momentum_exhaustion(highs, lows, closes)

            # Assess continuation probability
            continuation_probability = self._assess_continuation_probability(closes, current_momentum)

            # Determine signal based on high continuation probability criteria
            final_signal_type = SignalType.HOLD
            final_confidence_factor = self.config.get("default_confidence_factor", 0.3)
            final_score = 0.0

            # Define thresholds from config
            min_continuation_probability = self.config.get("min_continuation_probability", 0.6)

            # Only trade if:
            # 1. Momentum is strong enough
            # 2. Momentum has shown persistence
            # 3. Continuation probability is high
            # 4. Momentum is not exhausted
            if (abs(current_momentum) >= self.continuation_threshold and
                persistence_validation["persistence_valid"] and
                continuation_probability >= min_continuation_probability and  # High continuation probability
                not momentum_exhausted):

                # Bullish momentum setup
                if current_momentum > 0:
                    final_signal_type = SignalType.BUY
                    # Confidence based on continuation probability and momentum persistence
                    persistence_confidence = persistence_validation["momentum_consistency"]
                    final_confidence_factor = min(1.0, (continuation_probability + persistence_confidence) / 2)
                    final_score = min(1.0, current_momentum * 10)

                # Bearish momentum setup
                elif current_momentum < 0:
                    final_signal_type = SignalType.SELL
                    # Confidence based on continuation probability and momentum persistence
                    persistence_confidence = persistence_validation["momentum_consistency"]
                    final_confidence_factor = min(1.0, (continuation_probability + persistence_confidence) / 2)
                    final_score = max(-1.0, current_momentum * 10)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                timestamp=datetime.now(),
                source_layer="HighContinuationProbabilityMomentum",
                metadata={
                    "current_momentum": current_momentum,
                    "momentum_window": self.momentum_window,
                    "continuation_probability": continuation_probability,
                    "persistence_validation": persistence_validation,
                    "momentum_exhausted": momentum_exhausted,
                    "current_price": current_price,
                    "continuation_probability_assessed": True,
                    "persistence_validated": True,
                    "exhaustion_checked": True
                }
            )

            # Log signal if generated
            if final_signal_type != SignalType.HOLD:
                self.logger.info(f"{self.name} generated signal: {signal.signal_type.name} with confidence {float(signal.confidence.value):.3f} for {symbol.value}")
                self.logger.info(f"Momentum: {current_momentum:.4f}, Continuation Prob: {continuation_probability:.2f}, Persistence Valid: {persistence_validation['persistence_valid']}")

            return signal

        except Exception as e:
            self.logger.error(f"Error in {self.name} strategy: {e}")
            import traceback
            traceback.print_exc()
            return None