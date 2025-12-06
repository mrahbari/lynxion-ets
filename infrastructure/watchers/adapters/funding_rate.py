from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from domain.value_objects import Symbol
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, Optional


class FundingRateWatcher(BaseWatcher):
    """Funding Rate Watcher - analyzes funding rate trends for perpetual futures"""
    
    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 24):
        super().__init__(name, symbol, broker_service, target_broker)
        self.lookback = lookback
        
        # Funding rate data
        self.funding_rates = []
        self.funding_rate_timestamps = []
        
        # Funding rate metrics
        self.current_funding_rate = 0
        self.avg_funding_rate = 0
        self.funding_rate_change = 0
        self.funding_rate_volatility = 0
        
        # Thresholds (in percentage)
        self.extreme_long_threshold = 0.01  # 1% funding rate (very long)
        self.extreme_short_threshold = -0.01  # -1% funding rate (very short)
        self.reversion_threshold = 0.005  # 0.5% for reversion signals
        
    def update_data(self, data: Dict):
        """Update with new funding rate data"""
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
            if len(self.funding_rates) >= 2:
                self.avg_funding_rate = np.mean(self.funding_rates)
                self.funding_rate_change = rate - self.funding_rates[-2] if len(self.funding_rates) >= 2 else 0
                self.funding_rate_volatility = np.std(self.funding_rates) if len(self.funding_rates) > 1 else 0
                
    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze funding rate trends and return a signal"""
        if len(self.funding_rates) < 3:
            return None
            
        # Determine the signal based on funding rate levels and changes
        signal_type = SignalType.HOLD
        confidence = 0.3  # Default confidence
        
        # Check for extreme funding rates (potential reversal signals)
        if self.current_funding_rate > self.extreme_long_threshold:
            # High funding rate - likely over-leveraged longs, potential reversal down
            signal_type = SignalType.SELL
            confidence = min(1.0, 0.5 + (self.current_funding_rate - self.extreme_long_threshold) * 50)
        elif self.current_funding_rate < self.extreme_short_threshold:
            # Low funding rate - likely over-leveraged shorts, potential reversal up
            signal_type = SignalType.BUY
            confidence = min(1.0, 0.5 + (self.extreme_short_threshold - self.current_funding_rate) * 50)
        elif abs(self.funding_rate_change) > self.reversion_threshold:
            # Significant change in funding rate - potential acceleration or deceleration
            if self.funding_rate_change > 0 and self.current_funding_rate > 0:
                # Funding rate turning more positive rapidly - could mean more longs entering
                # This may continue the trend or signal caution
                signal_type = SignalType.SELL  # Potential reversal if too high
                confidence = min(0.7, 0.3 + abs(self.funding_rate_change) * 10)
            elif self.funding_rate_change < 0 and self.current_funding_rate < 0:
                # Funding rate turning more negative rapidly - could mean more shorts entering
                signal_type = SignalType.BUY  # Potential reversal if too low
                confidence = min(0.7, 0.3 + abs(self.funding_rate_change) * 10)
                
        # Calculate score based on funding rate level and recent changes
        # Convert funding rate to -1 to 1 scale for the score
        score = np.tanh(self.current_funding_rate * 100)  # Adjust multiplier as needed
        
        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=-score if signal_type == SignalType.SELL else score if signal_type == SignalType.BUY else -abs(score),
            strategy=self.name,
            timestamp=datetime.now()
        )
        
        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"FundingRateWatcher {self.name} generated signal: {signal_type} with funding_rate {self.current_funding_rate:.5f}, conf: {confidence:.3f}")
            
        return signal
        
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
            'funding_rate_volatility': self.funding_rate_volatility,
            'regime': self.get_funding_regime(),
            'data_points': len(self.funding_rates),
            'next_funding_time': None  # Would be added if available in data
        }