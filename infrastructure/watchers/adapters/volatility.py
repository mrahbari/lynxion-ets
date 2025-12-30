from .base_watcher import BaseWatcher
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
import os
from decimal import Decimal


class VolatilityWatcher(BaseWatcher):
    """Volatility Watcher - analyzes market volatility patterns"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 20, period: int = 14):
        super().__init__(name, symbol, broker_service, target_broker)

        # Configuration from environment with defaults
        self.enabled = os.getenv('VOLATILITY_WATCHER_ENABLED', 'true').lower() == 'true'

        # Only set logger if enabled, otherwise use mock logger
        if self.enabled:
            self.logger = logger
        else:
            # Create a mock logger that doesn't log anything when disabled
            class MockLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
            self.logger = MockLogger()

        self.lookback = lookback
        self.period = period
        self.price_history = []
        self.atr_history = []

        # Use more conservative thresholds to reduce constant firing
        self.volatility_expansion_threshold = 1.5  # 50% above average
        self.volatility_compression_threshold = 0.5  # 50% below average

        # Track previous regime to detect changes
        self.previous_regime = "normal"
        self.regime_change_detected = False
        self.signal_cooldown = 0
        self.max_cooldown = 5  # Prevent signal spamming

    def update_data(self, data: dict):
        """Update with new market data"""
        if not self.enabled:
            return

        if 'close' in data:
            self.price_history.append(data['close'])
            if len(self.price_history) > self.lookback * 3:
                self.price_history.pop(0)

        # Calculate and store ATR if we have enough data
        if len(self.price_history) >= 2:
            current_atr = self.calculate_atr()
            self.atr_history.append(current_atr)
            if len(self.atr_history) > self.lookback * 3:
                self.atr_history.pop(0)

    def _analyze_impl(self, symbol: Symbol) -> Signal:
        """Analyze volatility and return a signal"""
        if not self.enabled:
            return None

        if len(self.price_history) < self.lookback or len(self.atr_history) < 10:  # Require more data
            return None

        current_volatility = self.atr_history[-1] if self.atr_history else 0
        avg_volatility = np.mean(self.atr_history[-self.lookback:]) if len(self.atr_history) >= self.lookback else np.mean(self.atr_history)

        if avg_volatility == 0:
            return None

        # Calculate volatility ratio to determine regime
        volatility_ratio = current_volatility / avg_volatility if avg_volatility != 0 else 1

        # Determine current volatility regime
        current_regime = self.get_current_volatility_regime(current_volatility, avg_volatility, volatility_ratio)

        # Check if regime has changed since last analysis
        self.regime_change_detected = (current_regime != self.previous_regime)

        # Update previous regime for next iteration
        self.previous_regime = current_regime

        # Generate signals based on current volatility regime, not just regime changes
        # This allows for more actionable trading signals
        should_emit = True  # Always emit a signal based on current conditions

        # Apply cooldown to prevent frequent signals
        if self.signal_cooldown > 0:
            self.signal_cooldown -= 1
            # Still return a signal but with lower confidence during cooldown
            confidence_percentage = Percentage(Decimal(str(0.1)))  # Low confidence during cooldown

            signal = Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                confidence=confidence_percentage,
                score=0.0,
                strategy_name=self.name,  # Changed from 'strategy' to 'strategy_name' for domain compatibility
                timestamp=datetime.now(),
                source_engine=self.name,  # Add source engine for tracking
                metadata={
                    'regime': current_regime,
                    'volatility_ratio': volatility_ratio,
                    'current_volatility': current_volatility,
                    'average_volatility': avg_volatility,
                    'explanation': f"Current volatility regime: {current_regime}, in cooldown period"
                }
            )
            return signal

        # Calculate score based on volatility transition
        score = self.calculate_volatility_transition_score(current_volatility, avg_volatility, volatility_ratio)

        # Determine signal type based on current volatility regime and transition
        # Use volatility patterns to generate actionable trading signals
        if current_regime == "expansion":
            # High volatility expansion - potential for trend continuation or reversal
            # If volatility is expanding significantly, it may indicate strong market movement
            if volatility_ratio > self.volatility_expansion_threshold * 1.2:  # Even higher expansion
                # Extreme volatility - potential for reversal, SELL in uptrend, BUY in downtrend
                # For now, we'll use SELL as expansion often indicates potential reversal from highs
                signal_type = SignalType.SELL
                confidence = min(1.0, abs(score) * 0.9)  # High confidence for extreme expansion
            else:
                # Moderate expansion - potential for continuation
                signal_type = SignalType.BUY  # Expansion can indicate bullish sentiment
                confidence = min(0.7, abs(score) * 0.7)  # Moderate confidence
        elif current_regime == "compression":
            # Low volatility compression - potential breakout setup
            # Compression often precedes significant price movements
            signal_type = SignalType.BUY  # Breakout potential is generally positive
            confidence = min(0.8, abs(score) * 0.8)  # High confidence for compression breakout potential
        else:  # normal regime
            # In normal volatility, look for subtle changes
            if score > 0.1:
                signal_type = SignalType.BUY  # Positive volatility trend
                confidence = min(0.6, (score + 0.3) * 0.7)  # Moderate confidence
            elif score < -0.1:
                signal_type = SignalType.SELL  # Negative volatility trend
                confidence = min(0.6, (abs(score) + 0.3) * 0.7)  # Moderate confidence
            else:
                signal_type = SignalType.HOLD
                confidence = 0.3
                score = 0.0

        # Convert confidence to Percentage object for domain compatibility
        confidence_percentage = Percentage(Decimal(str(confidence)))

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence_percentage,
            score=score,
            strategy_name=self.name,  # Changed from 'strategy' to 'strategy_name' for domain compatibility
            timestamp=datetime.now(),
            source_engine=self.name,  # Add source engine for tracking
            metadata={
                'regime': current_regime,
                'regime_changed': self.regime_change_detected,
                'volatility_ratio': volatility_ratio,
                'current_volatility': current_volatility,
                'average_volatility': avg_volatility,
                'explanation': f"Volatility {current_regime} detected with ratio {volatility_ratio:.3f}, regime changed: {self.regime_change_detected}"
            }
        )

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"VolatilityWatcher {self.name} generated signal: {signal_type} with score {score:.3f}, regime: {current_regime}, vol_ratio: {volatility_ratio:.3f}")

        return signal

    def calculate_atr(self) -> float:
        """Calculate Average True Range"""
        if len(self.price_history) < 2:
            return 0.0

        # Simple ATR calculation (last few values)
        true_ranges = []
        for i in range(1, min(len(self.price_history), self.period + 1)):
            high = self.price_history[-i]
            low = self.price_history[-i-1]
            prev_close = self.price_history[-i-1] if i+1 < len(self.price_history) else self.price_history[-i-1]

            tr = max(
                abs(high - low),
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)

        if not true_ranges:
            return 0.0

        return sum(true_ranges) / len(true_ranges)

    def get_current_volatility_regime(self, current_vol: float, avg_vol: float, ratio: float) -> str:
        """Get current volatility regime - clearly distinguish expansion vs compression"""
        if ratio > self.volatility_expansion_threshold:
            return "expansion"  # High volatility expansion
        elif ratio < self.volatility_compression_threshold:
            return "compression"  # Low volatility compression
        else:
            return "normal"  # Stable volatility

    def is_regime_transition(self, current_regime: str, ratio: float) -> bool:
        """Check if there's a significant transition happening"""
        # Additional check for transitions that might not be captured by regime change
        # For example, when moving from compression to expansion gradually
        if len(self.atr_history) >= 3:
            recent_changes = [self.atr_history[i] - self.atr_history[i-1] for i in range(-3, -1)]
            if len(recent_changes) == 2:
                # Check if volatility is rapidly changing
                if abs(recent_changes[1] - recent_changes[0]) > 0.001:  # Adjust threshold as needed
                    return True
        return False

    def calculate_volatility_transition_score(self, current_vol: float, avg_vol: float, ratio: float) -> float:
        """Calculate score based on volatility transition (expansion/compression)"""
        if avg_vol == 0:
            return 0.0

        # Calculate normalized volatility change
        vol_change = (current_vol - avg_vol) / avg_vol

        # Use hyperbolic tangent to clamp between -1 and 1
        # This creates a smooth, bounded score that increases with volatility change
        transition_score = np.tanh(vol_change * 5)  # Multiplier adjusts sensitivity

        return transition_score

    def get_volatility_regime(self) -> str:
        """Get current volatility regime for external reference"""
        if not self.atr_history:
            return "unknown"

        current_vol = self.atr_history[-1]
        avg_vol = np.mean(self.atr_history[-self.lookback:]) if len(self.atr_history) >= self.lookback else np.mean(self.atr_history)

        if avg_vol == 0:
            return "unknown"

        ratio = current_vol / avg_vol if avg_vol != 0 else 1

        if ratio > self.volatility_expansion_threshold:
            return "expansion"
        elif ratio < self.volatility_compression_threshold:
            return "compression"
        else:
            return "normal"