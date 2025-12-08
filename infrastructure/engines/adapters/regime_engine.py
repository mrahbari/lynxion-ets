from ..base_engine import BaseEngine
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List


class RegimeEngine(BaseEngine):
    """Regime Engine - detects market regime changes and adjusts signals accordingly"""
    
    def __init__(self, name: str, lookback: int = 30):
        super().__init__(name)
        self.lookback = lookback
        
        # Market data history
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        
        # Regime detection metrics
        self.volatility_regime = "normal"
        self.trend_regime = "sideways"
        self.liquidity_regime = "normal"
        self.momentum_regime = "neutral"
        
        # Volatility measures
        self.current_volatility = 0
        self.avg_volatility = 0
        self.volatility_regimes = []
        
        # Trend measures
        self.current_trend_strength = 0
        self.trend_regimes = []
        
        # Thresholds
        self.high_vol_threshold = 0.025  # High volatility (>2.5% daily)
        self.low_vol_threshold = 0.008   # Low volatility (<0.8% daily)
        self.trend_strength_threshold = 0.003  # Trend strength threshold
        
    def update_data(self, data: Dict):
        """Update with new market data"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback * 4:
                self.price_history.pop(0)
                
        if 'volume' in data:
            self.volume_history.append(float(data['volume']))
            if len(self.volume_history) > self.lookback * 4:
                self.volume_history.pop(0)
                
        # Update regime metrics if we have enough data
        if len(self.price_history) >= 10:
            self.update_regime_metrics()
    
    def update_regime_metrics(self):
        """Update all regime metrics"""
        # Update volatility regime
        if len(self.price_history) >= 10:
            returns = np.diff(self.price_history[-self.lookback-1:]) / np.array(self.price_history[-self.lookback:-1])
            if len(returns) > 1:
                self.current_volatility = np.std(returns)
                
                if self.current_volatility > self.high_vol_threshold:
                    self.volatility_regime = "high"
                elif self.current_volatility < self.low_vol_threshold:
                    self.volatility_regime = "low"
                else:
                    self.volatility_regime = "normal"
                    
                self.avg_volatility = np.mean([np.std(np.diff(self.price_history[i-self.lookback:i]) / np.array(self.price_history[i-self.lookback-1:i-1])) 
                                              for i in range(max(10, len(self.price_history)-5), len(self.price_history)) 
                                              if i > 1]) if len(self.price_history) > 10 else self.current_volatility
                                              
        # Update trend regime
        if len(self.price_history) >= 5:
            prices = np.array(self.price_history[-self.lookback:])
            x = np.arange(len(prices))
            
            if len(x) > 1:
                slope = (len(x) * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                        (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)
                        
                avg_price = np.mean(prices) if len(prices) > 0 else 1
                if avg_price != 0:
                    self.current_trend_strength = slope / avg_price
                else:
                    self.current_trend_strength = 0
                    
                if self.current_trend_strength > self.trend_strength_threshold:
                    self.trend_regime = "bullish"
                elif self.current_trend_strength < -self.trend_strength_threshold:
                    self.trend_regime = "bearish"
                else:
                    self.trend_regime = "sideways"
            else:
                self.current_trend_strength = 0
                
        # Update liquidity regime (based on volume changes)
        if len(self.volume_history) >= 5:
            current_avg_vol = np.mean(self.volume_history[-5:])
            longer_avg_vol = np.mean(self.volume_history[-self.lookback:]) if len(self.volume_history) >= self.lookback else current_avg_vol
            
            if longer_avg_vol > 0 and current_avg_vol / longer_avg_vol > 2.0:  # Volume spike
                self.liquidity_regime = "high"
            elif longer_avg_vol > 0 and current_avg_vol / longer_avg_vol < 0.5:  # Low volume
                self.liquidity_regime = "low"
            else:
                self.liquidity_regime = "normal"
                
        # Update momentum regime
        if len(self.price_history) >= 3:
            recent_returns = np.diff(self.price_history[-3:])
            if len(recent_returns) > 0:
                avg_recent_return = np.mean(recent_returns)
                if avg_recent_return > 0.005:
                    self.momentum_regime = "positive"
                elif avg_recent_return < -0.005:
                    self.momentum_regime = "negative"
                else:
                    self.momentum_regime = "neutral"
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through regime analysis"""
        if len(self.price_history) < 10:
            # Not enough data for regime analysis - return original signal with reduced confidence
            new_confidence = signal.confidence * 0.7
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=new_confidence,
                score=signal.score * 0.7,
                strategy=f"{signal.strategy}_regime_filtered",
                timestamp=datetime.now(),
                metadata=signal.metadata
            )
            
        # Determine if the regime supports the signal
        regime_support_score = self.calculate_regime_support(signal)
        
        # Adjust signal based on regime
        base_confidence = signal.confidence
        base_score = signal.score
        
        # Adjust confidence based on regime alignment
        new_confidence = base_confidence * (0.8 + 0.4 * regime_support_score)  # Range from 0.8* to 1.2*
        new_score = base_score * (0.7 + 0.6 * regime_support_score)  # Range from 0.7* to 1.3*
        
        # Further adjustments based on specific regime conditions
        if self.volatility_regime == "high":
            # In high volatility, signals need to be more robust
            if signal.signal_type == SignalType.HOLD:
                # High volatility favors holding positions
                new_confidence = min(1.0, new_confidence * 1.1)
            else:
                # Other signals in high volatility need higher threshold
                new_confidence = new_confidence * 0.95
        elif self.volatility_regime == "low":
            # In low volatility, small moves are significant
            if signal.signal_type != SignalType.HOLD:
                # Non-hold signals in low volatility could be more significant
                new_confidence = min(1.0, new_confidence * 1.05)
                
        if self.trend_regime == "sideways" and signal.signal_type != SignalType.HOLD:
            # In sideways markets, trend-following signals might be less reliable
            new_confidence = new_confidence * 0.9
        elif self.trend_regime != "sideways":
            # In trending markets, trend-aligned signals might be more reliable
            trend_aligned = (self.trend_regime == "bullish" and signal.signal_type == SignalType.BUY) or \
                           (self.trend_regime == "bearish" and signal.signal_type == SignalType.SELL)
            if trend_aligned:
                new_confidence = min(1.0, new_confidence * 1.1)
                
        # Generate enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=max(0.05, min(1.0, new_confidence)),  # Clamp between 0.05 and 1.0
            score=new_score,
            strategy=f"{signal.strategy}_regime_filtered",
            timestamp=datetime.now(),
            metadata=signal.metadata or {}
        )
        
        # Add regime-specific metadata
        enhanced_signal.metadata.update({
            'original_confidence': signal.confidence,
            'regime_support_score': regime_support_score,
            'volatility_regime': self.volatility_regime,
            'trend_regime': self.trend_regime,
            'liquidity_regime': self.liquidity_regime,
            'momentum_regime': self.momentum_regime,
            'current_volatility': self.current_volatility,
            'current_trend_strength': self.current_trend_strength
        })
        
        logger.debug(f"RegimeEngine {self.name} processed signal: original={signal.signal_type}, "
                    f"regime_support={regime_support_score:.3f}, vol_regime={self.volatility_regime}, "
                    f"trend_regime={self.trend_regime}, new_conf={new_confidence:.3f}")
        
        # Add to history
        self.add_signal_to_history(enhanced_signal)
        
        return enhanced_signal
        
    def calculate_regime_support(self, signal: Signal) -> float:
        """Calculate how much the current regime supports the signal (-1 to 1)"""
        support_score = 0.0
        
        # Check volatility support
        if signal.signal_type == SignalType.HOLD:
            if self.volatility_regime == "high":
                support_score += 0.3  # High volatility supports holding
            else:
                support_score -= 0.1  # Low/mid volatility makes hold less necessary
        else:
            # For BUY/SELL signals
            if self.volatility_regime == "low":
                # In low volatility, signals might represent more significant shifts
                support_score += 0.2
            elif self.volatility_regime == "high":
                # In high volatility, more caution needed
                support_score -= 0.2
                
        # Check trend support
        if self.trend_regime != "sideways":
            trend_support = (
                (self.trend_regime == "bullish" and signal.signal_type == SignalType.BUY) or
                (self.trend_regime == "bearish" and signal.signal_type == SignalType.SELL)
            )
            if trend_support:
                support_score += 0.2
            else:
                support_score -= 0.2
                
        # Check momentum support
        if self.momentum_regime != "neutral":
            momentum_support = (
                (self.momentum_regime == "positive" and signal.signal_type == SignalType.BUY) or
                (self.momentum_regime == "negative" and signal.signal_type == SignalType.SELL)
            )
            if momentum_support:
                support_score += 0.1
            else:
                support_score -= 0.1
                
        # Clamp to -1 to 1 range
        return max(-1.0, min(1.0, support_score))
        
    def get_current_regime(self) -> Dict:
        """Get the current market regime"""
        return {
            'volatility_regime': self.volatility_regime,
            'trend_regime': self.trend_regime,
            'liquidity_regime': self.liquidity_regime,
            'momentum_regime': self.momentum_regime,
            'composite_regime': self.get_composite_regime(),
            'current_volatility': self.current_volatility,
            'avg_volatility': self.avg_volatility,
            'current_trend_strength': self.current_trend_strength
        }
        
    def get_composite_regime(self) -> str:
        """Get a composite regime classification"""
        if self.volatility_regime == "high" and self.trend_regime == "sideways":
            return "high_vol_chop"
        elif self.volatility_regime == "high" and self.trend_regime != "sideways":
            return "high_vol_trend"
        elif self.volatility_regime == "low" and self.trend_regime == "sideways":
            return "low_vol_chop"
        elif self.volatility_regime == "low" and self.trend_regime != "sideways":
            return "low_vol_trend"
        elif self.trend_regime != "sideways" and self.momentum_regime != "neutral":
            return "trending_momentum"
        else:
            return "normal"