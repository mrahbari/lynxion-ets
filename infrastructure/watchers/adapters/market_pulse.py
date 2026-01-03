from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
import os
from decimal import Decimal


class MarketPulseWatcher(BaseWatcher):
    """Market PulseWatcher - analyzes market sentiment and momentum, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 20):
        super().__init__(name, symbol, broker_service, target_broker)

        # Configuration from environment with defaults
        self.enabled = os.getenv('MARKET_PULSE_WATCHER_ENABLED', 'true').lower() == 'true'

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
        self.price_history = []
        self.volume_history = []

        # Initialize sub-components
        self.momentum_subscore = 0.0
        self.trend_subscore = 0.0
        self.volume_subscore = 0.0

    def update_data(self, data: dict):
        """Update with new market data"""
        if not self.enabled:
            return

        if 'close' in data:
            self.price_history.append(data['close'])
            if len(self.price_history) > self.lookback * 3:  # Keep more data for stability
                self.price_history.pop(0)

        if 'volume' in data:
            self.volume_history.append(data['volume'])
            if len(self.volume_history) > self.lookback * 3:
                self.volume_history.pop(0)

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze market pulse and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if len(self.price_history) < self.lookback:
            return None

        # Calculate clearly separated sub-scores
        self.momentum_subscore = self.calculate_momentum_subscore()
        self.trend_subscore = self.calculate_trend_subscore()
        self.volume_subscore = self.calculate_volume_subscore()

        # Combine factors to get final observation value (monotonic and bounded)
        observation_value = self.combine_subscores(self.momentum_subscore, self.trend_subscore, self.volume_subscore)

        # Determine observation type based on the value
        # Calculate confidence based on the strength of the signal
        signal_strength = abs(observation_value)

        if abs(observation_value) < 0.05:  # Threshold for low activity
            observation_type = 'market_pulse_neutral'
            # For neutral state, confidence is based on how close to zero we are
            # (more certainty about neutrality when signal is very weak)
            confidence = min(0.6, (1.0 - signal_strength))
        elif observation_value > 0:
            observation_type = 'market_pulse_positive'  # Positive momentum/sentiment
            # Confidence increases with signal strength
            confidence = min(0.95, max(0.3, signal_strength))
        else:
            observation_type = 'market_pulse_negative'  # Negative momentum/sentiment
            # Confidence increases with signal strength
            confidence = min(0.95, max(0.3, signal_strength))

        # Convert confidence to Percentage object for domain compatibility
        confidence_percentage = Percentage(Decimal(str(confidence)))

        # Create and return a MarketObservation instead of a Signal
        observation = MarketObservation(
            symbol=symbol,
            observation_type=observation_type,
            observation_value=observation_value,
            confidence=confidence_percentage,
            timestamp=datetime.now(),
            metadata={
                'subscores': {
                    'momentum': self.momentum_subscore,
                    'trend': self.trend_subscore,
                    'volume': self.volume_subscore
                },
                'observation_source': self.name,
                'lookback_period': self.lookback,
                'price_history_length': len(self.price_history),
                'volume_history_length': len(self.volume_history)
            }
        )

        return observation

    def calculate_momentum_subscore(self) -> float:
        """Calculate momentum subscore based on price changes"""
        if len(self.price_history) < 2:
            return 0.0

        # Calculate recent momentum (short-term)
        recent_change = (self.price_history[-1] - self.price_history[-2]) / self.price_history[-2]
        return recent_change  # Return as is, will be normalized later

    def calculate_trend_subscore(self) -> float:
        """Calculate trend subscore based on longer-term price movement"""
        if len(self.price_history) < self.lookback:
            return 0.0

        # Calculate trend using linear regression
        prices = np.array(self.price_history[-self.lookback:])
        x = np.arange(len(prices))

        if len(x) > 1:
            slope = (len(x) * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                    (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)

            # Normalize by average price
            avg_price = np.mean(prices)
            if avg_price != 0:
                return slope / avg_price

        return 0.0

    def calculate_volume_subscore(self) -> float:
        """Calculate volume subscore based on volume changes"""
        if len(self.volume_history) < 2:
            return 0.0

        # Calculate recent volume momentum
        recent_vol_change = (self.volume_history[-1] - self.volume_history[-2]) / self.volume_history[-2]
        return recent_vol_change  # Return as is, will be normalized later

    def combine_subscores(self, momentum: float, trend: float, volume: float) -> float:
        """Combine subscores into a single observation value"""
        # Normalize each subscore to [-1, 1] range if needed
        # Weight each component (adjust weights as needed)
        combined = (momentum * 0.4 + trend * 0.4 + volume * 0.2)
        
        # Clamp to reasonable range
        return max(-1.0, min(1.0, combined))