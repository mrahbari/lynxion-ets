"""
Market regime detection system to classify current market conditions
and adjust trading strategies accordingly.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
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
    MEAN_REVERTING = "mean_reverting"
    MOMENTUM = "momentum"

class ConfidenceBasedRegimeClassifier:
    """
    Redesigned Regime Classification with confidence scoring and veto mechanisms.

    Mathematical Formula:
    Regime_Probability_i = f(trend_strength, volatility, momentum, mean_reversion,
                            choppiness, volume_profile) * Regime_Bias_i

    Where:
    - Confidence_Score = max(Regime_Probabilities) / sum(Regime_Probabilities)
    - Maturity = f(time_since_regime_start, consistency)
    - Stability = f(regime_probability_variance, transition_frequency)
    - Veto = confidence < veto_threshold OR stability < min_stability
    """

    def __init__(self,
                 lookback_period: int = 50,
                 volatility_window: int = 20,
                 confidence_threshold: float = 0.6,
                 stability_threshold: float = 0.3,
                 maturity_threshold: float = 0.5,
                 transition_smoothing_window: int = 3):

        self.lookback_period = lookback_period
        self.volatility_window = volatility_window
        self.confidence_threshold = confidence_threshold
        self.stability_threshold = stability_threshold
        self.maturity_threshold = maturity_threshold
        self.transition_smoothing_window = transition_smoothing_window

        self.last_regime = None
        self.last_confidence = 0.0
        self.regime_transition_buffer = []  # Buffer to smooth transitions
        self.confusion_matrix = {}  # Track classification accuracy

    def classify_regime(self,
                       prices: List[float],
                       volumes: List[float] = None,
                       external_signals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify the current market regime with confidence scoring and veto mechanisms.
        """
        if len(prices) < self.lookback_period:
            return {
                "regime": RegimeType.RANGING.value,
                "confidence": 0.3,  # Low confidence for insufficient data
                "confidence_score": 0.3,
                "maturity": 0.0,
                "stability": 0.0,
                "veto": True,  # Veto regime when confidence is low
                "details": {"reason": "insufficient_data"},
                "transition_probability": 0.1,
                "confusion_matrix_feedback": {}
            }

        # Calculate various indicators
        returns = np.diff(prices) / prices[:-1]
        volatility = self._calculate_volatility(returns)
        trend_strength = self._calculate_trend_strength(prices)
        momentum = self._calculate_momentum(prices)
        mean_reversion = self._calculate_mean_reversion(prices)
        trend_consistency = self._calculate_trend_consistency(prices)
        volatility_regime = self._calculate_volatility_regime(returns)
        choppiness = self._calculate_choppiness(prices)
        volume_profile = self._calculate_volume_profile(volumes) if volumes else {}

        # Detect regime based on multiple indicators
        regime, confidence, details = self._classify_regime(
            returns, volatility, trend_strength, momentum, mean_reversion,
            trend_consistency, volatility_regime, choppiness, volume_profile,
            external_signals
        )

        # Calculate regime maturity and stability
        maturity = self._calculate_regime_maturity(regime)
        stability = self._calculate_regime_stability(regime, confidence)

        # Calculate transition probability
        transition_probability = self._calculate_transition_probability(regime)

        # Apply confusion matrix feedback
        confusion_feedback = self._apply_confusion_matrix_feedback(regime, prices)

        # Determine if regime should be vetoed due to low confidence or instability
        veto = (confidence < self.confidence_threshold or
                stability < self.stability_threshold)

        # Update transition buffer for smoothing
        self._update_transition_buffer(regime, confidence)

        # Apply smoothing to reduce noise in regime transitions
        smoothed_regime = self._apply_regime_smoothing(regime)

        result = {
            "regime": smoothed_regime.value,
            "confidence": confidence,
            "confidence_score": confidence,
            "maturity": maturity,
            "stability": stability,
            "veto": veto,
            "details": details,
            "transition_probability": transition_probability,
            "confusion_matrix_feedback": confusion_feedback
        }

        # Update last known regime for decay calculations
        self.last_regime = smoothed_regime
        self.last_confidence = confidence

        return result

    def _calculate_volatility(self, returns: np.ndarray) -> float:
        """Calculate rolling volatility."""
        if len(returns) < self.volatility_window:
            return float(np.std(returns))
        return float(np.std(returns[-self.volatility_window:]))

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

        return float(consistency)

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
        return float((recent_avg - longer_avg) / np.mean(prices)) if np.mean(prices) > 0 else 0.0

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
        return float(abs(z_score) * np.sign(current_price - ma))

    def _calculate_choppiness(self, prices: List[float]) -> float:
        """Calculate choppiness index to detect ranging markets."""
        if len(prices) < 14:
            return 0.5  # Neutral choppiness

        # Calculate Choppiness Index (CI)
        high_14 = max(prices[-14:])
        low_14 = min(prices[-14:])
        sum_atr_14 = sum([abs(prices[i] - prices[i-1]) for i in range(len(prices)-14, len(prices))])

        if sum_atr_14 == 0:
            return 0.5

        ci = 100 * np.log10(sum_atr_14 / (high_14 - low_14)) / np.log10(14)
        # CI ranges from 0 to 100, higher values indicate choppier markets
        return float(min(1.0, max(0.0, ci / 100)))

    def _calculate_volume_profile(self, volumes: List[float]) -> Dict[str, float]:
        """Calculate volume profile indicators."""
        if not volumes or len(volumes) < 10:
            return {"volume_trend": 0.0, "volume_spike": 0.0}

        recent_vol_avg = np.mean(volumes[-5:])
        longer_vol_avg = np.mean(volumes[-20:])

        volume_trend = (recent_vol_avg - longer_vol_avg) / longer_vol_avg if longer_vol_avg > 0 else 0.0
        volume_spike = max(0.0, (max(volumes[-5:]) - longer_vol_avg) / longer_vol_avg if longer_vol_avg > 0 else 0.0)

        return {
            "volume_trend": float(volume_trend),
            "volume_spike": float(volume_spike)
        }

    def _classify_regime(self,
                        returns: np.ndarray,
                        volatility: float,
                        trend_strength: float,
                        momentum: float,
                        mean_reversion: float,
                        trend_consistency: float,
                        volatility_regime: str,
                        choppiness: float,
                        volume_profile: Dict[str, float],
                        external_signals: Optional[Dict[str, Any]] = None) -> Tuple[RegimeType, float, Dict]:
        """Classify the market regime based on indicators with confusion matrix considerations."""

        # Calculate regime probabilities
        trending_up_prob = max(0, min(1, trend_strength * 10)) if trend_strength > 0 else 0
        trending_down_prob = max(0, min(1, -trend_strength * 10)) if trend_strength < 0 else 0

        # Momentum-based probability (when momentum is strong)
        momentum_prob = max(0, min(1, abs(momentum) * 5))

        # Mean reversion probability (when price is far from mean)
        mean_rev_prob = max(0, min(1, abs(mean_reversion) * 0.5))

        # Volatility-based regimes
        high_vol_prob = min(1, volatility * 100)  # Assuming typical vol is around 0.01
        low_vol_prob = min(1, 0.02 / (volatility + 0.0001))  # Inverse relationship

        # Ranging/choppy detection
        ranging_prob = choppiness  # Higher choppiness indicates ranging market

        # Trend consistency affects the reliability of trend signals
        trending_up_prob *= trend_consistency
        trending_down_prob *= trend_consistency

        # Incorporate volume signals
        volume_trend = volume_profile.get("volume_trend", 0.0)
        volume_spike = volume_profile.get("volume_spike", 0.0)

        # Adjust probabilities based on volume
        if volume_trend > 0.1:  # Increasing volume
            trending_up_prob *= 1.1 if momentum > 0 else 1.0
            trending_down_prob *= 1.1 if momentum < 0 else 1.0
        elif volume_trend < -0.1:  # Decreasing volume
            trending_up_prob *= 0.9
            trending_down_prob *= 0.9

        # Consider breakout conditions (high volatility + high volume spike)
        breakout_prob = min(1.0, (high_vol_prob + volume_spike) / 2.0) * 0.8

        # Determine dominant regime
        probs = {
            RegimeType.TRENDING_UP: trending_up_prob,
            RegimeType.TRENDING_DOWN: trending_down_prob,
            RegimeType.HIGH_VOLATILITY: high_vol_prob,
            RegimeType.LOW_VOLATILITY: low_vol_prob,
            RegimeType.CHOPPY: ranging_prob,
            RegimeType.MEAN_REVERTING: mean_rev_prob,
            RegimeType.MOMENTUM: momentum_prob * 0.8,  # Slightly reduce momentum to avoid over-allocation
            RegimeType.BREAKOUT: breakout_prob
        }

        # Find regime with highest probability
        dominant_regime = max(probs, key=probs.get)
        confidence = probs[dominant_regime]

        # Apply external signals if provided
        if external_signals:
            for ext_regime, ext_confidence in external_signals.items():
                try:
                    ext_regime_enum = RegimeType(ext_regime)
                    if ext_regime_enum in probs:
                        # Blend external signal with internal calculation
                        probs[ext_regime_enum] = (probs[ext_regime_enum] + ext_confidence) / 2.0
                except ValueError:
                    continue  # Invalid regime name in external signals

        # Recalculate dominant regime after incorporating external signals
        dominant_regime = max(probs, key=probs.get)
        confidence = probs[dominant_regime]

        details = {
            "trend_strength": trend_strength,
            "trend_consistency": trend_consistency,
            "volatility": volatility,
            "momentum": momentum,
            "mean_reversion": mean_reversion,
            "choppiness": choppiness,
            "volatility_regime": volatility_regime,
            "volume_profile": volume_profile,
            "probabilities": {k.value: v for k, v in probs.items()},
            "classification_method": "multi_indicator_probability_with_external_signals"
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

        return float(stability)

    def _calculate_transition_probability(self, current_regime: RegimeType) -> float:
        """Calculate the probability of regime transition."""
        # Higher probability if regime has been stable for a long time
        # or if market conditions are changing rapidly
        if self.last_regime != current_regime:
            # Just changed, so transition probability is lower
            return 0.1
        else:
            # Same regime, probability depends on how long it's lasted
            # and how consistent it's been
            maturity = self._get_current_maturity()
            # Longer maturity increases transition probability
            return min(0.8, maturity * 0.5)

    def _apply_confusion_matrix_feedback(self, predicted_regime: RegimeType, prices: List[float]) -> Dict[str, float]:
        """Apply confusion matrix feedback to improve future predictions."""
        # Placeholder for confusion matrix feedback
        # In a real system, this would compare predictions to actual outcomes
        feedback = {
            "predicted_regime": predicted_regime.value,
            "feedback_applied": False,
            "accuracy_estimate": 0.0
        }

        # This would be updated when actual regime changes are observed
        return feedback

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

    def update_confusion_matrix(self, predicted_regime: RegimeType, actual_regime: RegimeType):
        """Update confusion matrix with actual outcome."""
        if predicted_regime.value not in self.confusion_matrix:
            self.confusion_matrix[predicted_regime.value] = {}

        if actual_regime.value not in self.confusion_matrix[predicted_regime.value]:
            self.confusion_matrix[predicted_regime.value][actual_regime.value] = 0

        self.confusion_matrix[predicted_regime.value][actual_regime.value] += 1

    def get_regime_accuracy(self) -> Dict[str, float]:
        """Get accuracy metrics from confusion matrix."""
        if not self.confusion_matrix:
            return {}

        accuracies = {}
        for pred_regime, actual_dict in self.confusion_matrix.items():
            total_predictions = sum(actual_dict.values())
            if total_predictions > 0:
                correct_predictions = actual_dict.get(pred_regime, 0)
                accuracies[pred_regime] = correct_predictions / total_predictions

        return accuracies


class RegimeVetoMechanism:
    """
    Veto mechanism to override regime classification when confidence is too low
    or other conditions warrant caution.
    """

    def __init__(self,
                 confidence_threshold: float = 0.5,
                 stability_threshold: float = 0.4,
                 transition_volatility_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.stability_threshold = stability_threshold
        self.transition_volatility_threshold = transition_volatility_threshold

    def should_veto(self, regime_classification: Dict[str, Any]) -> bool:
        """
        Determine if the regime classification should be vetoed.
        """
        # Veto if confidence is too low
        if regime_classification['confidence'] < self.confidence_threshold:
            return True

        # Veto if stability is too low
        if regime_classification['stability'] < self.stability_threshold:
            return True

        # Veto if transition probability is too high (indicating high uncertainty)
        if regime_classification['transition_probability'] > self.transition_volatility_threshold:
            return True

        # No veto conditions met
        return False

    def get_safe_regime(self) -> RegimeType:
        """
        Get a safe regime to fall back to when veto is triggered.
        """
        # In uncertain times, default to a conservative regime
        return RegimeType.LOW_VOLATILITY  # Conservative default


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

# Global regime detector instance
regime_detector = RegimeDetector()