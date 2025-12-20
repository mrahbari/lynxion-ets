from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from domain.value_objects import Symbol
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, Optional
import os


class FundingRateWatcher(BaseWatcher):
    """Funding Rate Watcher - analyzes funding rate trends for perpetual futures"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 24):
        super().__init__(name, symbol, broker_service, target_broker)

        # Configuration from environment with defaults
        self.enabled = os.getenv('FUNDING_RATE_WATCHER_ENABLED', 'true').lower() == 'true'

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

        # Funding rate data
        self.funding_rates = []
        self.funding_rate_timestamps = []

        # Funding rate metrics - separate extreme funding from acceleration
        self.current_funding_rate = 0
        self.avg_funding_rate = 0
        self.funding_rate_change = 0  # Change in funding rate (acceleration)
        self.funding_rate_acceleration = 0  # Change in change (acceleration of acceleration)
        self.funding_rate_volatility = 0

        # Thresholds (in percentage) - more conservative
        self.extreme_long_threshold = 0.015  # Higher threshold to reduce noise (1.5%)
        self.extreme_short_threshold = -0.015  # Higher threshold to reduce noise (-1.5%)
        self.acceleration_threshold = 0.001  # For detecting acceleration in funding rate changes

        # Cooldown mechanism
        self.signal_cooldown = 0
        self.max_cooldown = 12  # Long cooldown period to avoid frequent signals

    def update_data(self, data: Dict):
        """Update with new funding rate data"""
        if not self.enabled:
            return

        if 'funding_rate' in data:
            # Add new funding rate
            rate = float(data['funding_rate'])
            timestamp = data.get('timestamp', datetime.now())

            self.funding_rates.append(rate)
            self.funding_rate_timestamps.append(timestamp)

            # Keep only the lookback amount of data
            if len(self.funding_rates) > self.lookback * 2:  # Keep extra for calculations
                self.funding_rates.pop(0)
                self.funding_rate_timestamps.pop(0)

            # Update current funding rate
            self.current_funding_rate = rate

            # Calculate metrics if we have enough data
            if len(self.funding_rates) >= 3:  # Need 3+ points to calculate acceleration
                self.avg_funding_rate = np.mean(self.funding_rates)
                # Calculate change in funding rate (velocity)
                self.funding_rate_change = rate - self.funding_rates[-2] if len(self.funding_rates) >= 2 else 0
                # Calculate change in the change (acceleration)
                if len(self.funding_rates) >= 3:
                    prev_change = self.funding_rates[-2] - self.funding_rates[-3]
                    self.funding_rate_acceleration = self.funding_rate_change - prev_change
                self.funding_rate_volatility = np.std(self.funding_rates) if len(self.funding_rates) > 1 else 0

    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze funding rate trends and return a signal"""
        if not self.enabled:
            return None

        if len(self.funding_rates) < 5:  # Require more data for reliable signals
            return None

        # Apply cooldown
        if self.signal_cooldown > 0:
            self.signal_cooldown -= 1
            # Return HOLD during cooldown
            return Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                confidence=0.1,
                score=0.0,
                strategy=self.name,
                timestamp=datetime.now(),
                metadata={
                    'explanation': 'Funding rate watcher in cooldown period',
                    'funding_rate': self.current_funding_rate
                }
            )

        # Separate detection of extreme funding levels from acceleration
        extreme_funding_detected = self.detect_extreme_funding()
        acceleration_detected = self.detect_funding_acceleration()

        # Only generate signals when there's a meaningful change or extreme condition
        signal_type = SignalType.HOLD
        confidence = 0.3  # Default low confidence for HOLD
        score = 0.0

        # Check for extreme funding with potential reversal
        if extreme_funding_detected and acceleration_detected:
            # Both extreme level and acceleration detected - high confidence reversal
            if self.current_funding_rate > self.extreme_long_threshold:
                # Extremely high funding rate with acceleration - strong SELL signal
                signal_type = SignalType.SELL
                confidence = 0.9
            elif self.current_funding_rate < self.extreme_short_threshold:
                # Extremely low funding rate with acceleration - strong BUY signal
                signal_type = SignalType.BUY
                confidence = 0.9
        elif extreme_funding_detected:
            # Only extreme level detected - moderate confidence reversal
            if self.current_funding_rate > self.extreme_long_threshold:
                signal_type = SignalType.SELL
                confidence = 0.7
            elif self.current_funding_rate < self.extreme_short_threshold:
                signal_type = SignalType.BUY
                confidence = 0.7
        elif acceleration_detected:
            # Only acceleration detected - contrarian signal based on acceleration direction
            if self.funding_rate_acceleration > 0 and self.current_funding_rate > 0:
                # Funding rate accelerating higher - potential SELL
                signal_type = SignalType.SELL
                confidence = 0.6
            elif self.funding_rate_acceleration < 0 and self.current_funding_rate < 0:
                # Funding rate accelerating lower - potential BUY
                signal_type = SignalType.BUY
                confidence = 0.6

        # Calculate score based on both level and acceleration
        level_score = np.tanh(self.current_funding_rate * 100)  # Score based on level
        acceleration_score = np.tanh(self.funding_rate_acceleration * 1000)  # Score based on acceleration

        # Combine scores based on signal type
        if signal_type == SignalType.BUY:
            score = abs(acceleration_score) if acceleration_detected else abs(level_score)
        elif signal_type == SignalType.SELL:
            score = -abs(acceleration_score) if acceleration_detected else -abs(level_score)
        else:
            score = 0.0

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy=self.name,
            timestamp=datetime.now(),
            metadata={
                'explanation': f"Funding extreme: {extreme_funding_detected}, acceleration: {acceleration_detected}",
                'current_funding_rate': self.current_funding_rate,
                'funding_rate_change': self.funding_rate_change,
                'funding_rate_acceleration': self.funding_rate_acceleration,
                'extreme_funding_detected': extreme_funding_detected,
                'acceleration_detected': acceleration_detected
            }
        )

        # Update last signal if it's different enough and activate cooldown
        if self.should_emit_signal(signal):
            self.last_signal = signal
            self.signal_cooldown = self.max_cooldown  # Activate long cooldown
            logger.debug(f"FundingRateWatcher {self.name} generated signal: {signal_type} with funding_rate {self.current_funding_rate:.5f}, conf: {confidence:.3f}")

        return signal

    def detect_extreme_funding(self) -> bool:
        """Separately detect extreme funding conditions"""
        if len(self.funding_rates) < 2:
            return False

        # Check if current funding rate is at extreme levels
        return (self.current_funding_rate > self.extreme_long_threshold or
                self.current_funding_rate < self.extreme_short_threshold)

    def detect_funding_acceleration(self) -> bool:
        """Separately detect acceleration in funding rate changes"""
        if len(self.funding_rates) < 3:
            return False

        # Check if the change in funding rate is significant (acceleration)
        return abs(self.funding_rate_acceleration) > self.acceleration_threshold

    def calculate_funding_rate_score(self) -> float:
        """Calculate a normalized score based on funding rate (-1 to 1)"""
        if len(self.funding_rates) < 2:
            return 0.0

        # Calculate z-score of current funding rate relative to historical
        if self.funding_rate_volatility == 0:
            # If no volatility, return 0 if near average, 1 if much higher, -1 if much lower
            if self.current_funding_rate > self.avg_funding_rate:
                return 0.5
            elif self.current_funding_rate < self.avg_funding_rate:
                return -0.5
            else:
                return 0.0

        z_score = (self.current_funding_rate - self.avg_funding_rate) / self.funding_rate_volatility

        # Clamp z-score to reasonable range to prevent extreme values
        z_score = max(-3, min(3, z_score))

        # Use tanh to map to -1 to 1 range while preserving direction
        return np.tanh(z_score / 2)  # Divide by 2 to make it less sensitive

    def get_funding_regime(self) -> str:
        """Get current funding rate regime"""
        if not self.funding_rates:
            return "unknown"

        if self.current_funding_rate > self.extreme_long_threshold:
            return "extremely_long"
        elif self.current_funding_rate > 0:
            return "moderately_long"
        elif self.current_funding_rate < self.extreme_short_threshold:
            return "extremely_short"
        elif self.current_funding_rate < 0:
            return "moderately_short"
        else:
            return "neutral"

    def get_funding_metrics(self) -> Dict:
        """Get current funding rate metrics"""
        return {
            'current_funding_rate': self.current_funding_rate,
            'average_funding_rate': self.avg_funding_rate,
            'funding_rate_change': self.funding_rate_change,
            'funding_rate_acceleration': self.funding_rate_acceleration,
            'funding_rate_volatility': self.funding_rate_volatility,
            'regime': self.get_funding_regime(),
            'data_points': len(self.funding_rates),
            'extreme_funding_detected': self.detect_extreme_funding(),
            'acceleration_detected': self.detect_funding_acceleration(),
            'cooldown_remaining': self.signal_cooldown
        }