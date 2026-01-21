"""
Market regime detection system to classify current market conditions
and adjust trading strategies accordingly.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class RegimeType(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CHOPPY = "choppy"
    BREAKOUT = "breakout"

class RegimeDetector:
    """Detects current market regime based on price/volume data."""
    
    def __init__(self, lookback_period: int = 50, volatility_window: int = 20):
        self.lookback_period = lookback_period
        self.volatility_window = volatility_window
        
    def detect_regime(self, prices: List[float], volumes: List[float] = None) -> Dict:
        """Detect the current market regime."""
        if len(prices) < self.lookback_period:
            return {"regime": RegimeType.RANGING.value, "confidence": 0.5, "details": {}}
            
        # Calculate various indicators
        returns = np.diff(prices) / prices[:-1]
        volatility = self._calculate_volatility(returns)
        trend_strength = self._calculate_trend_strength(prices)
        momentum = self._calculate_momentum(prices)
        mean_reversion = self._calculate_mean_reversion(prices)
        
        # Detect regime based on multiple indicators
        regime, confidence, details = self._classify_regime(
            returns, volatility, trend_strength, momentum, mean_reversion
        )
        
        return {
            "regime": regime.value,
            "confidence": confidence,
            "details": details
        }
        
    def _calculate_volatility(self, returns: np.ndarray) -> float:
        """Calculate rolling volatility."""
        if len(returns) < self.volatility_window:
            return np.std(returns)
        return np.std(returns[-self.volatility_window:])
        
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """Calculate trend strength using linear regression."""
        x = np.arange(len(prices))
        slope, _, r_value, _, _ = stats.linregress(x, prices)
        trend_strength = abs(slope) / np.mean(prices)  # Normalize by price level
        return trend_strength * r_value  # Multiply by correlation
        
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate momentum indicator."""
        if len(prices) < 10:
            return 0.0
        recent_avg = np.mean(prices[-5:])
        longer_avg = np.mean(prices[-20:])
        return (recent_avg - longer_avg) / np.mean(prices)
        
    def _calculate_mean_reversion(self, prices: List[float]) -> float:
        """Calculate mean reversion tendency."""
        if len(prices) < 20:
            return 0.0
            
        ma = np.mean(prices[-20:])
        current_price = prices[-1]
        z_score = (current_price - ma) / np.std(prices[-20:])
        
        # How far from mean, indicating potential reversion
        return abs(z_score) * np.sign(current_price - ma)
        
    def _classify_regime(self, returns: np.ndarray, volatility: float, 
                        trend_strength: float, momentum: float, 
                        mean_reversion: float) -> Tuple[RegimeType, float, Dict]:
        """Classify the market regime based on indicators."""
        
        # Calculate regime probabilities
        trending_up_prob = max(0, min(1, trend_strength * 10)) if trend_strength > 0 else 0
        trending_down_prob = max(0, min(1, -trend_strength * 10)) if trend_strength < 0 else 0
        
        # Volatility-based regimes
        high_vol_prob = min(1, volatility * 100)  # Assuming typical vol is around 0.01
        low_vol_prob = min(1, 0.02 / (volatility + 0.0001))  # Inverse relationship
        
        # Ranging detection - low trend strength but some movement
        ranging_prob = max(0, min(1, (0.01 - abs(trend_strength)) * 100)) * high_vol_prob
        
        # Choppiness detection - frequent direction changes
        direction_changes = sum(np.diff(np.sign(returns)) != 0)
        choppiness_ratio = direction_changes / len(returns) if len(returns) > 0 else 0
        choppy_prob = min(1, choppiness_ratio * 5)
        
        # Determine dominant regime
        probs = {
            RegimeType.TRENDING_UP: trending_up_prob,
            RegimeType.TRENDING_DOWN: trending_down_prob,
            RegimeType.RANGING: ranging_prob,
            RegimeType.HIGH_VOLATILITY: high_vol_prob,
            RegimeType.LOW_VOLATILITY: low_vol_prob,
            RegimeType.CHOPPY: choppy_prob
        }
        
        # Find regime with highest probability
        dominant_regime = max(probs, key=probs.get)
        confidence = probs[dominant_regime]
        
        details = {
            "trend_strength": trend_strength,
            "volatility": volatility,
            "momentum": momentum,
            "mean_reversion": mean_reversion,
            "choppiness_ratio": choppiness_ratio,
            "probabilities": {k.value: v for k, v in probs.items()}
        }
        
        return dominant_regime, confidence, details

# Global regime detector instance
regime_detector = RegimeDetector()