from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
from domain.value_objects import Symbol
import numpy as np


class MarketPulseWatcher(BaseWatcher):
    """Market PulseWatcher - analyzes market sentiment and momentum"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 20):
        super().__init__(name, symbol, broker_service, target_broker)
        self.lookback = lookback
        self.price_history = []
        self.volume_history = []
        self.trend_strength_threshold = 0.1
        self.momentum_threshold = 0.05
        
    def update_data(self, data: dict):
        """Update with new market data"""
        if 'close' in data:
            self.price_history.append(data['close'])
            if len(self.price_history) > self.lookback * 2:
                self.price_history.pop(0)
                
        if 'volume' in data:
            self.volume_history.append(data['volume'])
            if len(self.volume_history) > self.lookback * 2:
                self.volume_history.pop(0)
                
    def analyze(self, symbol: Symbol) -> Signal:
        """Analyze market pulse and return a signal"""
        if len(self.price_history) < self.lookback:
            return None

        # Calculate momentum
        momentum = self.calculate_momentum()

        # Calculate trend strength
        trend_strength = self.calculate_trend_strength()

        # Calculate volume factor
        volume_factor = self.calculate_volume_factor()

        # Combine factors to get score
        score = (momentum * 0.4) + (trend_strength * 0.4) + (volume_factor * 0.2)

        # Determine signal type based on score
        if score > self.trend_strength_threshold:
            signal_type = SignalType.BUY
            confidence = min(1.0, score)
        elif score < -self.trend_strength_threshold:
            signal_type = SignalType.SELL
            confidence = min(1.0, abs(score))
        else:
            signal_type = SignalType.HOLD
            confidence = 1.0 - abs(score)

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy=self.name,
            timestamp=datetime.now()
        )

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"MarketPulseWatcher {self.name} generated signal: {signal_type} with score {score:.3f}")

        return signal
        
    def calculate_momentum(self) -> float:
        """Calculate momentum based on price changes"""
        if len(self.price_history) < 2:
            return 0.0
            
        recent_prices = self.price_history[-5:]  # Last 5 prices
        older_prices = self.price_history[-10:-5]  # Previous 5 prices
        
        if len(older_prices) == 0:
            return 0.0
            
        recent_avg = sum(recent_prices) / len(recent_prices)
        older_avg = sum(older_prices) / len(older_prices)
        
        if older_avg == 0:
            return 0.0
            
        momentum = (recent_avg - older_avg) / older_avg
        return max(-1.0, min(1.0, momentum))  # Clamp between -1 and 1
        
    def calculate_trend_strength(self) -> float:
        """Calculate trend strength using linear regression"""
        if len(self.price_history) < self.lookback:
            return 0.0
            
        prices = np.array(self.price_history[-self.lookback:])
        x = np.arange(len(prices))
        
        # Calculate linear regression slope
        slope = (len(x) * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)
                
        # Normalize slope to be between -1 and 1
        normalized_slope = np.tanh(slope * 10)  # Adjust multiplier as needed
        return normalized_slope
        
    def calculate_volume_factor(self) -> float:
        """Calculate factor based on volume changes"""
        if len(self.volume_history) < 2:
            return 0.0
            
        # Calculate average volume over the lookback period
        avg_volume = np.mean(self.volume_history[-self.lookback:]) if len(self.volume_history) >= self.lookback else np.mean(self.volume_history)
        
        if avg_volume == 0:
            return 0.0
            
        current_volume = self.volume_history[-1]
        volume_ratio = (current_volume - avg_volume) / avg_volume
        
        # Return volume factor clamped between -0.5 and 0.5
        return max(-0.5, min(0.5, volume_ratio * 0.5))