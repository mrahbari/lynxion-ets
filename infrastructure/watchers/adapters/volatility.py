from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
from domain.value_objects import Symbol
import numpy as np


class VolatilityWatcher(BaseWatcher):
    """Volatility Watcher - analyzes market volatility patterns"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 20, period: int = 14):
        super().__init__(name, symbol, broker_service, target_broker)
        self.lookback = lookback
        self.period = period
        self.price_history = []
        self.atr_history = []
        self.volatility_threshold_high = 0.02  # High volatility threshold (2%)
        self.volatility_threshold_low = 0.005  # Low volatility threshold (0.5%)
        
    def update_data(self, data: dict):
        """Update with new market data"""
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
                
    def analyze(self, symbol: Symbol) -> Signal:
        """Analyze volatility and return a signal"""
        if len(self.price_history) < self.lookback or len(self.atr_history) < 2:
            return None

        current_volatility = self.atr_history[-1] if self.atr_history else 0
        avg_volatility = np.mean(self.atr_history[-self.lookback:])

        if avg_volatility == 0:
            return None

        # Calculate volatility ratio
        volatility_ratio = current_volatility / avg_volatility if avg_volatility != 0 else 1

        # Determine if volatility is above or below normal
        is_high_vol = current_volatility > self.volatility_threshold_high
        is_low_vol = current_volatility < self.volatility_threshold_low

        # Calculate score based on volatility changes
        score = self.calculate_volatility_score(current_volatility, avg_volatility)

        # Determine signal type based on volatility conditions
        if is_high_vol and volatility_ratio > 1.5:
            # High volatility expansion - could signal trend continuation or reversal
            signal_type = SignalType.HOLD  # High volatility often means uncertain conditions
            confidence = min(1.0, volatility_ratio * 0.3)
        elif is_low_vol and volatility_ratio < 0.5:
            # Low volatility contraction - often precedes breakouts
            # Could signal either direction, so hold
            signal_type = SignalType.HOLD
            confidence = min(1.0, (1 - volatility_ratio) * 0.4)
        else:
            # Normal volatility conditions
            signal_type = SignalType.HOLD
            confidence = 0.3  # Low confidence in volatility-based signals alone

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
            logger.debug(f"VolatilityWatcher {self.name} generated signal: {signal_type} with score {score:.3f}, vol_ratio: {volatility_ratio:.3f}")

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
        
    def calculate_volatility_score(self, current_vol: float, avg_vol: float) -> float:
        """Calculate volatility score between -1 and 1"""
        if avg_vol == 0:
            return 0.0
            
        # Calculate normalized volatility change
        vol_change = (current_vol - avg_vol) / avg_vol
        
        # Use hyperbolic tangent to clamp between -1 and 1
        return np.tanh(vol_change * 5)  # Multiplier adjusts sensitivity
        
    def get_volatility_regime(self) -> str:
        """Get current volatility regime"""
        if not self.atr_history:
            return "unknown"
            
        current_vol = self.atr_history[-1]
        
        if current_vol > self.volatility_threshold_high:
            return "high"
        elif current_vol < self.volatility_threshold_low:
            return "low"
        else:
            return "normal"