from ..base_engine import BaseEngine
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List


class TrendEngine(BaseEngine):
    """Trend Engine - evaluates trend strength and direction"""
    
    def __init__(self, name: str, lookback: int = 20, trend_threshold: float = 0.01):
        super().__init__(name)
        self.lookback = lookback
        self.trend_threshold = trend_threshold
        self.price_history: List[float] = []
        self.trend_direction = 0  # -1 for down, 0 for neutral, 1 for up
        
    def update_data(self, data: Dict):
        """Update with new market data"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback * 3:
                self.price_history.pop(0)
                
            # Update trend if we have enough data
            if len(self.price_history) >= self.lookback:
                self.update_trend()
                
    def update_trend(self):
        """Update the current trend direction"""
        if len(self.price_history) < 5:
            return
            
        # Calculate simple trend using linear regression
        prices = np.array(self.price_history[-self.lookback:])
        x = np.arange(len(prices))
        
        # Calculate slope
        slope = (len(x) * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)
                
        # Calculate average price for normalization
        avg_price = np.mean(prices)
        
        if avg_price == 0:
            self.trend_direction = 0
            return
            
        # Normalize slope by average price to get trend strength
        normalized_slope = slope / avg_price
        
        # Determine trend direction
        if normalized_slope > self.trend_threshold:
            self.trend_direction = 1
        elif normalized_slope < -self.trend_threshold:
            self.trend_direction = -1
        else:
            self.trend_direction = 0
            
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through trend analysis"""
        if len(self.price_history) < 5 or self.trend_direction == 0:
            # Not enough data or no clear trend - return original signal with adjusted confidence
            new_confidence = signal.confidence * 0.8  # Slightly reduce confidence when no clear trend
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=new_confidence,
                score=signal.score * 0.8,
                strategy=f"{signal.strategy}_trend_filtered",
                timestamp=datetime.now(),
                metadata=signal.metadata
            )
        
        # Check if the incoming signal aligns with the current trend
        signal_aligns_with_trend = (
            (self.trend_direction == 1 and signal.signal_type == SignalType.BUY) or
            (self.trend_direction == -1 and signal.signal_type == SignalType.SELL)
        )
        
        if signal_aligns_with_trend:
            # Signal aligns with trend - increase confidence
            new_confidence = min(1.0, signal.confidence * 1.2)
            new_score = signal.score * 1.2
        else:
            # Signal goes against trend - decrease confidence
            new_confidence = max(0.1, signal.confidence * 0.7)
            new_score = signal.score * 0.6
            
        # Generate enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy=f"{signal.strategy}_trend_filtered",
            timestamp=datetime.now(),
            metadata=signal.metadata or {}
        )
        
        # Add trend-specific metadata
        enhanced_signal.metadata.update({
            'original_confidence': signal.confidence,
            'trend_direction': self.trend_direction,
            'trend_aligned': signal_aligns_with_trend,
            'trend_strength': self.get_trend_strength()
        })
        
        logger.debug(f"TrendEngine {self.name} processed signal: original={signal.signal_type}, "
                    f"trend_dir={self.trend_direction}, aligned={signal_aligns_with_trend}, "
                    f"new_conf={new_confidence:.3f}")
        
        # Add to history
        self.add_signal_to_history(enhanced_signal)
        
        return enhanced_signal
        
    def get_trend_strength(self) -> float:
        """Get the strength of the current trend"""
        if len(self.price_history) < self.lookback:
            return 0.0
            
        prices = np.array(self.price_history[-self.lookback:])
        x = np.arange(len(prices))
        
        # Calculate slope and R-squared for strength measure
        slope = (len(x) * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)
                
        avg_price = np.mean(prices)
        if avg_price == 0:
            return 0.0
            
        # Normalize slope
        normalized_slope = abs(slope / avg_price)
        
        # Return trend strength (clipped to reasonable range)
        return min(1.0, normalized_slope * 100)  # Adjust multiplier as needed
        
    def get_trend_regime(self) -> str:
        """Get current trend regime"""
        if self.trend_direction == 1:
            return "bullish"
        elif self.trend_direction == -1:
            return "bearish"
        else:
            return "sideways"