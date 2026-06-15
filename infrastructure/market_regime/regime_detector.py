"""
Market regime detection system to classify current market conditions
and adjust trading strategies accordingly.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')
from infrastructure.market_regime._regime_classifiers import RegimeType, ConfidenceBasedRegimeClassifier, RegimeVetoMechanism

class RegimeDetector:
    """Detects current market regime based on price/volume data with confidence scoring and decay logic."""

    def __init__(self, lookback_period: int = 50, volatility_window: int = 20,
                 confidence_threshold: float = 0.6, decay_factor: float = 0.95):
        self.lookback_period = lookback_period
        self.volatility_window = volatility_window
        self.confidence_threshold = confidence_threshold  # Threshold below which regime is considered unreliable
        self.decay_factor = decay_factor  # Factor for regime decay over time
        self.last_regime = None
        self.last_confidence = 0.0
        self.regime_transition_buffer = []  # Buffer to smooth transitions
        self.transition_smoothing_window = 3  # Number of periods to consider for smoothing

        # Add the redesigned regime classifier
        self.confidence_based_classifier = ConfidenceBasedRegimeClassifier(
            lookback_period=lookback_period,
            volatility_window=volatility_window,
            confidence_threshold=confidence_threshold,
            transition_smoothing_window=self.transition_smoothing_window
        )
        self.veto_mechanism = RegimeVetoMechanism()

    def detect_regime(self, prices: List[float], volumes: List[float] = None) -> Dict:
        """Detect the current market regime with confidence scoring."""
        if len(prices) < self.lookback_period:
            return {
                "regime": RegimeType.RANGING.value,
                "confidence": 0.3,  # Low confidence for insufficient data
                "confidence_score": 0.3,
                "maturity": 0.0,
                "stability": 0.0,
                "veto": True,  # Veto regime when confidence is low
                "details": {"reason": "insufficient_data"}
            }

        # Calculate various indicators
        returns = np.diff(prices) / prices[:-1]
        volatility = self._calculate_volatility(returns)
        trend_strength = self._calculate_trend_strength(prices)
        momentum = self._calculate_momentum(prices)
        mean_reversion = self._calculate_mean_reversion(prices)
        trend_consistency = self._calculate_trend_consistency(prices)
        volatility_regime = self._calculate_volatility_regime(returns)

        # Detect regime based on multiple indicators
        regime, confidence, details = self._classify_regime(
            returns, volatility, trend_strength, momentum, mean_reversion,
            trend_consistency, volatility_regime
        )

        # Calculate regime maturity and stability
        maturity = self._calculate_regime_maturity(regime)
        stability = self._calculate_regime_stability(regime, confidence)

        # Apply decay to confidence if regime has been consistent for too long
        decayed_confidence = self._apply_regime_decay(confidence, regime)

        # Determine if regime should be vetoed due to low confidence
        veto = decayed_confidence < self.confidence_threshold

        # Update transition buffer for smoothing
        self._update_transition_buffer(regime, decayed_confidence)

        # Apply smoothing to reduce noise in regime transitions
        smoothed_regime = self._apply_regime_smoothing(regime)

        result = {
            "regime": smoothed_regime.value,
            "confidence": decayed_confidence,
            "confidence_score": decayed_confidence,  # Alias for compatibility
            "maturity": maturity,
            "stability": stability,
            "veto": veto,
            "details": details
        }

        # Update last known regime for decay calculations
        self.last_regime = smoothed_regime
        self.last_confidence = decayed_confidence

        return result

    def _calculate_volatility(self, returns: np.ndarray) -> float:
        """Calculate rolling volatility."""
        if len(returns) < self.volatility_window:
            return np.std(returns)
        return np.std(returns[-self.volatility_window:])

    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """Calculate trend strength using linear regression."""
        x = np.arange(len(prices))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, prices)
        trend_strength = abs(slope) / np.mean(prices) if np.mean(prices) > 0 else 0.0  # Normalize by price level
        return trend_strength * r_value  # Multiply by correlation

    def _calculate_trend_consistency(self, prices: List[float]) -> float:
        """Calculate how consistent the trend is over time."""
        if len(prices) < 10:
            return 0.0

        # Calculate trend for multiple sub-periods
        sub_periods = 3
        period_length = len(prices) // sub_periods
        trends = []

        for i in range(sub_periods):
            start_idx = i * period_length
            end_idx = min((i + 1) * period_length, len(prices))
            if end_idx > start_idx:
                sub_prices = prices[start_idx:end_idx]
                x = np.arange(len(sub_prices))
                slope, _, r_value, _, _ = stats.linregress(x, sub_prices)
                trends.append(slope * r_value)

        if len(trends) < 2:
            return 0.0

        # Calculate consistency as the standard deviation of trends (lower is more consistent)
        trend_std = np.std(trends)
        consistency = 1.0 / (1.0 + trend_std)  # Inverse relationship

        return consistency

    def _calculate_volatility_regime(self, returns: np.ndarray) -> str:
        """Classify volatility regime."""
        if len(returns) < 20:
            return "normal"

        current_vol = np.std(returns[-10:])  # Recent volatility
        historical_vol = np.std(returns[-50:])  # Historical volatility

        if current_vol > historical_vol * 1.5:
            return "high"
        elif current_vol < historical_vol * 0.7:
            return "low"
        else:
            return "normal"

    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate momentum indicator."""
        if len(prices) < 10:
            return 0.0
        recent_avg = np.mean(prices[-5:])
        longer_avg = np.mean(prices[-20:])
        return (recent_avg - longer_avg) / np.mean(prices) if np.mean(prices) > 0 else 0.0

    def _calculate_mean_reversion(self, prices: List[float]) -> float:
        """Calculate mean reversion tendency."""
        if len(prices) < 20:
            return 0.0

        ma = np.mean(prices[-20:])
        current_price = prices[-1]
        std_dev = np.std(prices[-20:])

        if std_dev == 0:
            return 0.0

        z_score = (current_price - ma) / std_dev

        # How far from mean, indicating potential reversion
        return abs(z_score) * np.sign(current_price - ma)

    def _classify_regime(self, returns: np.ndarray, volatility: float,
                        trend_strength: float, momentum: float,
                        mean_reversion: float, trend_consistency: float,
                        volatility_regime: str) -> Tuple[RegimeType, float, Dict]:
        """Classify the market regime based on indicators with confusion matrix considerations."""

        # Calculate regime probabilities
        trending_up_prob = max(0, min(1, trend_strength * 10)) if trend_strength > 0 else 0
        trending_down_prob = max(0, min(1, -trend_strength * 10)) if trend_strength < 0 else 0

        # Momentum-based probability (when momentum is strong)
        momentum_prob = max(0, min(1, abs(momentum) * 5))
        momentum_regime = RegimeType.MOMENTUM if momentum > 0 else RegimeType.TRENDING_DOWN
        if momentum < 0:
            momentum_regime = RegimeType.MOMENTUM  # Both up and down momentum are momentum regime

        # Mean reversion probability (when price is far from mean)
        mean_rev_prob = max(0, min(1, abs(mean_reversion) * 0.5))
        mean_rev_regime = RegimeType.MEAN_REVERTING

        # Volatility-based regimes
        high_vol_prob = min(1, volatility * 100)  # Assuming typical vol is around 0.01
        low_vol_prob = min(1, 0.02 / (volatility + 0.0001))  # Inverse relationship

        # Ranging detection - low trend strength but some movement
        ranging_prob = max(0, min(1, (0.01 - abs(trend_strength)) * 100)) * high_vol_prob

        # Choppiness detection - frequent direction changes
        direction_changes = sum(np.diff(np.sign(returns)) != 0)
        choppiness_ratio = direction_changes / len(returns) if len(returns) > 0 else 0
        choppy_prob = min(1, choppiness_ratio * 5)

        # Trend consistency affects the reliability of trend signals
        trending_up_prob *= trend_consistency
        trending_down_prob *= trend_consistency

        # Determine dominant regime
        probs = {
            RegimeType.TRENDING_UP: trending_up_prob,
            RegimeType.TRENDING_DOWN: trending_down_prob,
            RegimeType.RANGING: ranging_prob,
            RegimeType.HIGH_VOLATILITY: high_vol_prob,
            RegimeType.LOW_VOLATILITY: low_vol_prob,
            RegimeType.CHOPPY: choppy_prob,
            RegimeType.MEAN_REVERTING: mean_rev_prob,
            RegimeType.MOMENTUM: momentum_prob * 0.8  # Slightly reduce momentum to avoid over-allocation
        }

        # Find regime with highest probability
        dominant_regime = max(probs, key=probs.get)
        confidence = probs[dominant_regime]

        details = {
            "trend_strength": trend_strength,
            "trend_consistency": trend_consistency,
            "volatility": volatility,
            "momentum": momentum,
            "mean_reversion": mean_reversion,
            "choppiness_ratio": choppiness_ratio,
            "volatility_regime": volatility_regime,
            "probabilities": {k.value: v for k, v in probs.items()},
            "classification_method": "multi_indicator_probability"
        }

        return dominant_regime, confidence, details

    def _calculate_regime_maturity(self, current_regime: RegimeType) -> float:
        """Calculate how mature the current regime is."""
        # In a real implementation, this would track how long the regime has persisted
        # For now, we'll simulate maturity based on consistency
        if self.last_regime == current_regime:
            # If regime continues, increase maturity up to 1.0
            return min(1.0, self._get_current_maturity() + 0.1)
        else:
            # If regime changes, reset maturity
            return 0.1

    def _get_current_maturity(self) -> float:
        """Helper to get current maturity (placeholder implementation)."""
        # In a real system, this would be tracked over time
        return 0.3

    def _calculate_regime_stability(self, current_regime: RegimeType, current_confidence: float) -> float:
        """Calculate regime stability."""
        # Stability is based on confidence and consistency of the regime
        stability = current_confidence

        # If the regime has been consistent recently, increase stability
        if self.last_regime == current_regime and self.last_confidence > 0.7:
            stability = min(1.0, stability * 1.2)

        return stability

    def _apply_regime_decay(self, confidence: float, regime: RegimeType) -> float:
        """Apply decay to regime confidence over time."""
        # If the same regime has persisted for too long, reduce confidence
        # This helps detect when a regime might be ending
        if self.last_regime == regime:
            # Apply decay factor to gradually reduce confidence
            return confidence * self.decay_factor
        else:
            # If regime changed, return original confidence
            return confidence

    def _update_transition_buffer(self, regime: RegimeType, confidence: float):
        """Update the regime transition buffer for smoothing."""
        self.regime_transition_buffer.append((regime, confidence))

        # Keep only the last N transitions
        if len(self.regime_transition_buffer) > self.transition_smoothing_window:
            self.regime_transition_buffer.pop(0)

    def _apply_regime_smoothing(self, current_regime: RegimeType) -> RegimeType:
        """Apply smoothing to reduce noise in regime transitions."""
        if len(self.regime_transition_buffer) < 2:
            return current_regime

        # Count the most frequent regime in the buffer
        regime_counts = {}
        for regime, _ in self.regime_transition_buffer:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

        # If the current regime is the most frequent in the buffer, keep it
        # Otherwise, consider the most frequent regime
        most_frequent_regime = max(regime_counts, key=regime_counts.get)

        # Only change if the most frequent regime appears more than once
        if regime_counts[most_frequent_regime] > 1:
            return most_frequent_regime
        else:
            return current_regime

# Module-level singleton retired (E2.T6). The canonical instance is now created
# in bootstrap/container.py (container-scoped). This lazy accessor preserves
# backward compatibility for ``from ... import regime_detector`` without
# instantiating at import time. New code should resolve from the container.
_regime_detector_singleton = None


def __getattr__(name):
    global _regime_detector_singleton
    if name == "regime_detector":
        if _regime_detector_singleton is None:
            _regime_detector_singleton = RegimeDetector()
        return _regime_detector_singleton
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")