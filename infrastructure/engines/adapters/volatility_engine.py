from ..base_engine import BaseEngine
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List


class VolatilityEngine(BaseEngine):
    """Volatility Engine - evaluates signals based on market volatility"""
    
    def __init__(self, name: str, lookback: int = 20, high_vol_threshold: float = 0.02, low_vol_threshold: float = 0.005):
        super().__init__(name)
        self.lookback = lookback
        self.high_vol_threshold = high_vol_threshold  # High volatility threshold (2%)
        self.low_vol_threshold = low_vol_threshold    # Low volatility threshold (0.5%)
        self.price_history: List[float] = []
        self.volatility_history: List[float] = []
        self.current_volatility = 0
        self.avg_volatility = 0
        
    def update_data(self, data: Dict):
        """Update with new market data"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback * 3:
                self.price_history.pop(0)
                
            # Calculate volatility if we have enough data
            if len(self.price_history) >= 2:
                returns = np.diff(self.price_history[-self.lookback-1:]) / np.array(self.price_history[-self.lookback-1:-1])
                if len(returns) > 1:
                    vol = np.std(returns)
                    self.volatility_history.append(vol)
                    if len(self.volatility_history) > self.lookback * 3:
                        self.volatility_history.pop(0)
                        
                    self.current_volatility = vol
                    self.avg_volatility = np.mean(self.volatility_history) if self.volatility_history else 0
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through volatility analysis"""
        if not self.volatility_history:
            # No volatility data - return original signal with slightly reduced confidence
            new_confidence = signal.confidence * 0.9
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=new_confidence,
                score=signal.score * 0.9,
                strategy=f"{signal.strategy}_vol_filtered",
                timestamp=datetime.now(),
                metadata=signal.metadata
            )
            
        # Determine volatility regime
        is_high_vol = self.current_volatility > self.high_vol_threshold
        is_low_vol = self.current_volatility < self.low_vol_threshold
        is_normal_vol = not is_high_vol and not is_low_vol
        
        # Adjust signal based on volatility regime
        if is_high_vol:
            # High volatility may mean uncertain signals, reduce confidence
            new_confidence = max(0.2, signal.confidence * 0.6)  # Reduce confidence in high vol
            new_score = signal.score * 0.7
        elif is_low_vol:
            # Low volatility may mean signals are more reliable, slightly increase confidence
            new_confidence = min(1.0, signal.confidence * 1.1)  # Slightly increase confidence
            new_score = signal.score * 1.1
        else:
            # Normal volatility - keep confidence relatively unchanged
            new_confidence = signal.confidence
            new_score = signal.score
            
        # For reversal signals (contrarian), volatility adjustment might be different
        # If signal is contrarian (against trend), high volatility might validate it
        if signal.metadata and signal.metadata.get('contrarian', False):
            if is_high_vol:
                # High volatility might validate contrarian signals
                new_confidence = min(1.0, new_confidence * 1.2)
                
        # Generate enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy=f"{signal.strategy}_vol_filtered",
            timestamp=datetime.now(),
            metadata=signal.metadata or {}
        )
        
        # Add volatility-specific metadata
        enhanced_signal.metadata.update({
            'original_confidence': signal.confidence,
            'current_volatility': self.current_volatility,
            'avg_volatility': self.avg_volatility,
            'volatility_regime': self.get_volatility_regime(),
            'volatility_ratio': self.current_volatility / self.avg_volatility if self.avg_volatility > 0 else 1.0
        })
        
        logger.debug(f"VolatilityEngine {self.name} processed signal: original={signal.signal_type}, "
                    f"vol_regime={self.get_volatility_regime()}, "
                    f"new_conf={new_confidence:.3f}")
        
        # Add to history
        self.add_signal_to_history(enhanced_signal)
        
        return enhanced_signal
        
    def get_volatility_regime(self) -> str:
        """Get current volatility regime"""
        if self.current_volatility > self.high_vol_threshold:
            return "high"
        elif self.current_volatility < self.low_vol_threshold:
            return "low"
        else:
            return "normal"
            
    def calculate_volatility_score(self) -> float:
        """Calculate a score based on volatility conditions (-1 to 1)"""
        if not self.volatility_history or self.avg_volatility == 0:
            return 0.0
            
        # Calculate how different current volatility is from average
        vol_ratio = self.current_volatility / self.avg_volatility
        if self.avg_volatility == 0:
            return 0.0
            
        # Use log to normalize large differences
        vol_score = np.log(vol_ratio)
        
        # Clamp to reasonable range
        return max(-1.0, min(1.0, vol_score))