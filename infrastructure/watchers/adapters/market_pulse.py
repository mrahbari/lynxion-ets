from .base_watcher import BaseWatcher
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
import os
from decimal import Decimal


class MarketPulseWatcher(BaseWatcher):
    """Market PulseWatcher - analyzes market sentiment and momentum"""

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

        # Define thresholds for signal generation - lowered to allow more trading opportunities
        self.signal_threshold = 0.05  # Lowered threshold to allow more signals (was 0.15)

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

    def _analyze_impl(self, symbol: Symbol) -> Signal:
        """Analyze market pulse and return a signal"""
        if not self.enabled:
            return None

        if len(self.price_history) < self.lookback:
            return None

        # Calculate clearly separated sub-scores
        self.momentum_subscore = self.calculate_momentum_subscore()
        self.trend_subscore = self.calculate_trend_subscore()
        self.volume_subscore = self.calculate_volume_subscore()

        # Combine factors to get final score (monotonic and bounded)
        score = self.combine_subscores(self.momentum_subscore, self.trend_subscore, self.volume_subscore)

        # Apply NO SIGNAL zone to avoid constant firing
        if abs(score) < self.signal_threshold:
            signal_type = SignalType.HOLD
            confidence = 0.1  # Low confidence for no-signal state
        elif score > 0:
            signal_type = SignalType.BUY
            confidence = min(1.0, abs(score))  # Confidence based on signal strength
        else:
            signal_type = SignalType.SELL
            confidence = min(1.0, abs(score))  # Confidence based on signal strength

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
                'subscores': {
                    'momentum': self.momentum_subscore,
                    'trend': self.trend_subscore,
                    'volume': self.volume_subscore
                },
                'explanation': f"Momentum: {self.momentum_subscore:.3f}, Trend: {self.trend_subscore:.3f}, Volume: {self.volume_subscore:.3f}, Combined: {score:.3f}"
            }
        )

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"MarketPulseWatcher {self.name} generated signal: {signal_type} with score {score:.3f}, explanation: {signal.metadata['explanation']}")

        return signal

    def calculate_momentum_subscore(self) -> float:
        """Calculate momentum sub-score based on price changes - clearly explainable"""
        if len(self.price_history) < 2:
            return 0.0

        # Use a more stable momentum calculation
        lookback_period = min(5, len(self.price_history) - 1)
        if lookback_period < 1:
            return 0.0

        current_price = self.price_history[-1]
        comparison_price = self.price_history[-lookback_period - 1]

        if comparison_price == 0:
            return 0.0

        momentum = (current_price - comparison_price) / comparison_price
        # Use tanh to create a smooth, bounded score between -1 and 1
        return np.tanh(momentum * 10)  # Multiplier adjusts sensitivity

    def calculate_trend_subscore(self) -> float:
        """Calculate trend sub-score using linear regression - clearly explainable"""
        if len(self.price_history) < self.lookback:
            return 0.0

        prices = np.array(self.price_history[-self.lookback:])
        x = np.arange(len(prices))

        # Calculate linear regression slope with robust calculation
        n = len(x)
        slope = (n * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                (n * np.sum(x * x) - (np.sum(x)) ** 2) if n * np.sum(x * x) - (np.sum(x)) ** 2 != 0 else 0

        # Normalize slope to be between -1 and 1 using tanh for smooth bounded output
        return np.tanh(slope * 1000)  # Adjust multiplier based on typical price scale

    def calculate_volume_subscore(self) -> float:
        """Calculate volume sub-score based on relative volume changes - clearly explainable"""
        if len(self.volume_history) < 2:
            return 0.0

        # Calculate average volume over the lookback period for reference
        lookback_period = min(self.lookback, len(self.volume_history))
        avg_volume = np.mean(self.volume_history[-lookback_period:])

        if avg_volume == 0:
            return 0.0

        current_volume = self.volume_history[-1]
        # Calculate relative volume expansion/compression
        volume_ratio = (current_volume - avg_volume) / avg_volume

        # Use tanh to create a smooth, bounded score between -1 and 1
        return np.tanh(volume_ratio * 2)  # Multiplier adjusts sensitivity

    def combine_subscores(self, momentum: float, trend: float, volume: float) -> float:
        """Combine subscores with fixed weights for deterministic behavior"""
        # Use fixed weights to ensure deterministic behavior
        # All weights sum to 1.0 to maintain bounded output
        combined_score = (momentum * 0.4) + (trend * 0.4) + (volume * 0.2)

        # Ensure final score is bounded between -1 and 1
        return max(-1.0, min(1.0, combined_score))

    def get_subscore_breakdown(self) -> dict:
        """Get the current breakdown of subscores for explainability"""
        return {
            'momentum': self.momentum_subscore,
            'trend': self.trend_subscore,
            'volume': self.volume_subscore,
            'combined': self.combine_subscores(self.momentum_subscore, self.trend_subscore, self.volume_subscore),
            'explanation': f"Momentum + volume expansion exceeded baseline by {self.combine_subscores(self.momentum_subscore, self.trend_subscore, self.volume_subscore):.3f}"
        }