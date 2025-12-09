from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
from domain.value_objects import Symbol
import numpy as np


class TrendMTFWatcher(BaseWatcher):
    """Multi-Timeframe Trend Watcher - analyzes trends across multiple timeframes"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, short_period: int = 5, medium_period: int = 15, long_period: int = 30):
        super().__init__(name, symbol, broker_service, target_broker)
        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period

        # Stores for different timeframes
        self.short_trend = 0
        self.medium_trend = 0
        self.long_trend = 0
        self.price_history = []

        # Trend thresholds
        self.trend_threshold = 0.005  # 0.5% threshold for trend significance
        
    def update_data(self, data: dict):
        """Update with new market data"""
        if 'close' in data:
            self.price_history.append(data['close'])
            if len(self.price_history) > self.long_period * 3:  # Keep more than the longest period
                self.price_history.pop(0)
                
        # Update trends if we have enough data
        if len(self.price_history) >= self.long_period:
            self.update_trends()
            
    def update_trends(self):
        """Update trend values for different timeframes"""
        if len(self.price_history) < self.long_period:
            return
            
        # Calculate short-term trend (5-period moving average relationship)
        if len(self.price_history) >= self.short_period:
            short_ma = np.mean(self.price_history[-self.short_period:])
            current_price = self.price_history[-1]
            self.short_trend = (current_price - short_ma) / short_ma
            
        # Calculate medium-term trend (15-period moving average relationship)
        if len(self.price_history) >= self.medium_period:
            medium_ma = np.mean(self.price_history[-self.medium_period:])
            current_price = self.price_history[-1]
            self.medium_trend = (current_price - medium_ma) / medium_ma
            
        # Calculate long-term trend (30-period moving average relationship)
        if len(self.price_history) >= self.long_period:
            long_ma = np.mean(self.price_history[-self.long_period:])
            current_price = self.price_history[-1]
            self.long_trend = (current_price - long_ma) / long_ma
            
    def analyze(self, symbol: Symbol) -> Signal:
        """Analyze multi-timeframe trends and return a signal"""
        if len(self.price_history) < self.long_period:
            return None

        # Calculate overall trend score
        trend_score = self.calculate_trend_score()

        # Determine signal based on multi-timeframe alignment
        signal_type = self.determine_signal_type(trend_score)
        confidence = self.calculate_confidence()

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=trend_score,
            strategy=self.name,
            timestamp=datetime.now()
        )

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"TrendMTFWatcher {self.name} generated signal: {signal_type} with score {trend_score:.3f}, conf: {confidence:.3f}")

        return signal
        
    def calculate_trend_score(self) -> float:
        """Calculate trend score based on multi-timeframe alignment"""
        # Weight the different timeframes
        score = (self.long_trend * 0.5) + (self.medium_trend * 0.3) + (self.short_trend * 0.2)
        
        # Use tanh to clamp between -1 and 1
        return np.tanh(score * 5)  # Multiplier adjusts sensitivity
        
    def determine_signal_type(self, trend_score: float) -> SignalType:
        """Determine signal type based on trend alignment"""
        # Check if all timeframes are aligned in the same direction
        all_bullish = (self.long_trend > self.trend_threshold and 
                      self.medium_trend > self.trend_threshold and 
                      self.short_trend > self.trend_threshold)
        
        all_bearish = (self.long_trend < -self.trend_threshold and 
                      self.medium_trend < -self.trend_threshold and 
                      self.short_trend < -self.trend_threshold)
        
        # Check for divergences
        short_vs_long_divergence = ((self.short_trend > self.trend_threshold and self.long_trend < -self.trend_threshold) or
                                   (self.short_trend < -self.trend_threshold and self.long_trend > self.trend_threshold))
                                   
        if all_bullish:
            return SignalType.BUY
        elif all_bearish:
            return SignalType.SELL
        elif short_vs_long_divergence:
            # Divergence often signals reversal, opposite to short-term direction
            return SignalType.SELL if self.short_trend > 0 else SignalType.BUY
        else:
            # Mixed signals or weak trends
            return SignalType.HOLD
            
    def calculate_confidence(self) -> float:
        """Calculate confidence based on trend alignment"""
        # Confidence is higher when all timeframes align
        alignment_score = 0
        
        # Check alignment between timeframes
        if (np.sign(self.long_trend) == np.sign(self.medium_trend) and 
            np.sign(self.medium_trend) == np.sign(self.short_trend)):
            # All aligned - high confidence
            alignment_score = 0.8
        elif (np.sign(self.long_trend) == np.sign(self.medium_trend) or 
              np.sign(self.medium_trend) == np.sign(self.short_trend) or 
              np.sign(self.long_trend) == np.sign(self.short_trend)):
            # At least two aligned - medium confidence
            alignment_score = 0.5
        else:
            # No alignment - low confidence
            alignment_score = 0.2
            
        # Boost confidence if trends are strong
        avg_strength = (abs(self.long_trend) + abs(self.medium_trend) + abs(self.short_trend)) / 3
        strength_boost = min(0.2, avg_strength)  # Cap the boost
        
        confidence = min(1.0, alignment_score + strength_boost)
        return confidence
        
    def get_trend_alignment(self) -> dict:
        """Get the current alignment of trends"""
        return {
            'long': 'bullish' if self.long_trend > 0 else 'bearish',
            'medium': 'bullish' if self.medium_trend > 0 else 'bearish',
            'short': 'bullish' if self.short_trend > 0 else 'bearish',
            'long_strength': abs(self.long_trend),
            'medium_strength': abs(self.medium_trend),
            'short_strength': abs(self.short_trend)
        }