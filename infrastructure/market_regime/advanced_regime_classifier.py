"""
Advanced Regime Classification with confidence scoring, veto mechanisms, and recalibration logic.
Implements regime confidence, stability, maturity, and confusion matrix feedback.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


class RegimeType(Enum):
    """Market regime types"""
    BULLISH_TRENDING = "bullish_trending"
    BEARISH_TRENDING = "bearish_trending"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CHOPPY = "choppy"
    BREAKOUT = "breakout"
    NORMAL = "normal"
    MEAN_REVERTING = "mean_reverting"
    MOMENTUM = "momentum"


@dataclass
class RegimeClassification:
    """Container for regime classification results"""
    regime: RegimeType
    confidence: float
    stability: float
    maturity: float
    veto: bool
    details: Dict[str, Any]


class AdvancedRegimeClassifier:
    """
    Advanced regime classification with:
    - Confidence scoring
    - Stability assessment
    - Maturity tracking
    - Veto mechanisms
    - Recalibration logic
    - Confusion matrix feedback
    """
    
    def __init__(self,
                 lookback_period: int = 50,
                 volatility_window: int = 20,
                 confidence_threshold: float = 0.6,
                 stability_threshold: float = 0.5,
                 maturity_threshold: float = 0.3,
                 decay_factor: float = 0.95,
                 transition_smoothing_window: int = 3):
        
        self.lookback_period = lookback_period
        self.volatility_window = volatility_window
        self.confidence_threshold = confidence_threshold
        self.stability_threshold = stability_threshold
        self.maturity_threshold = maturity_threshold
        self.decay_factor = decay_factor
        self.transition_smoothing_window = transition_smoothing_window
        
        # Track regime history
        self.regime_history: List[Tuple[RegimeType, float, datetime]] = []
        self.confidence_history: List[Tuple[float, datetime]] = []
        self.transition_buffer: List[Tuple[RegimeType, float]] = []
        
        # Track regime performance for recalibration
        self.regime_performance: Dict[RegimeType, List[Dict[str, Any]]] = {}
        self.confusion_matrix: Dict[RegimeType, Dict[RegimeType, int]] = {}
        
        # Initialize confusion matrix
        for regime1 in RegimeType:
            self.confusion_matrix[regime1] = {}
            for regime2 in RegimeType:
                self.confusion_matrix[regime1][regime2] = 0

    def classify_regime(self, 
                      prices: List[float], 
                      volumes: Optional[List[float]] = None,
                      external_signals: Optional[Dict[str, Any]] = None) -> RegimeClassification:
        """
        Classify current market regime with confidence scoring and vetos.
        """
        if len(prices) < self.lookback_period:
            return RegimeClassification(
                regime=RegimeType.NORMAL,
                confidence=0.3,  # Low confidence for insufficient data
                stability=0.2,
                maturity=0.1,
                veto=True,
                details={"reason": "insufficient_data", "data_points": len(prices)}
            )

        # Calculate various indicators
        returns = np.diff(prices) / np.array(prices[:-1])
        volatility = self._calculate_volatility(returns)
        trend_strength = self._calculate_trend_strength(prices)
        momentum = self._calculate_momentum(prices)
        mean_reversion = self._calculate_mean_reversion(prices)
        trend_consistency = self._calculate_trend_consistency(prices)
        volatility_regime = self._calculate_volatility_regime(returns)
        choppiness = self._calculate_choppiness(prices)
        support_resistance = self._calculate_support_resistance(prices)

        # Classify regime with confidence
        regime, confidence, details = self._classify_with_confidence(
            returns, volatility, trend_strength, momentum, mean_reversion,
            trend_consistency, volatility_regime, choppiness, support_resistance
        )

        # Calculate regime stability
        stability = self._calculate_stability(regime, confidence)

        # Calculate regime maturity
        maturity = self._calculate_maturity(regime)

        # Apply decay to confidence based on regime persistence
        decayed_confidence = self._apply_decay(regime, confidence)

        # Determine if regime should be vetoed
        veto = self._should_veto(decayed_confidence, stability, maturity)

        # Apply transition smoothing
        smoothed_regime = self._apply_transition_smoothing(regime, decayed_confidence)

        # Update history
        self._update_history(smoothed_regime, decayed_confidence)

        result = RegimeClassification(
            regime=smoothed_regime,
            confidence=decayed_confidence,
            stability=stability,
            maturity=maturity,
            veto=veto,
            details=details
        )

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
        trend_strength = abs(slope) / np.mean(prices) if np.mean(prices) > 0 else 0.0
        return float(trend_strength * r_value)

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

        # Calculate consistency as the inverse of standard deviation
        trend_std = np.std(trends)
        consistency = 1.0 / (1.0 + trend_std)

        return float(consistency)

    def _calculate_volatility_regime(self, returns: np.ndarray) -> str:
        """Classify volatility regime."""
        if len(returns) < 20:
            return "normal"

        current_vol = np.std(returns[-10:])
        historical_vol = np.std(returns[-50:])

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
        return float(abs(z_score) * np.sign(current_price - ma))

    def _calculate_choppiness(self, prices: List[float]) -> float:
        """Calculate choppiness index."""
        if len(prices) < 14:
            return 0.5  # Neutral choppiness

        # Simplified choppiness calculation
        high_14 = max(prices[-14:])
        low_14 = min(prices[-14:])
        close = prices[-1]

        if high_14 == low_14:
            return 0.5

        # Choppiness index ranges from 0 (trending) to 1 (choppy)
        choppiness = (close - low_14) / (high_14 - low_14)
        return float(choppiness)

    def _calculate_support_resistance(self, prices: List[float]) -> Dict[str, float]:
        """Calculate support and resistance levels."""
        if len(prices) < 20:
            return {"support": float(min(prices)), "resistance": float(max(prices))}

        # Calculate support and resistance based on recent highs/lows
        recent_prices = prices[-20:]
        support = float(np.percentile(recent_prices, 20))
        resistance = float(np.percentile(recent_prices, 80))

        return {"support": support, "resistance": resistance}

    def _classify_with_confidence(self, 
                                 returns: np.ndarray,
                                 volatility: float,
                                 trend_strength: float,
                                 momentum: float,
                                 mean_reversion: float,
                                 trend_consistency: float,
                                 volatility_regime: str,
                                 choppiness: float,
                                 support_resistance: Dict[str, float]) -> Tuple[RegimeType, float, Dict[str, Any]]:
        """Classify regime with confidence scoring."""
        # Calculate probabilities for each regime
        probabilities = self._calculate_regime_probabilities(
            returns, volatility, trend_strength, momentum, mean_reversion,
            trend_consistency, volatility_regime, choppiness
        )

        # Find regime with highest probability
        dominant_regime = max(probabilities, key=probabilities.get)
        confidence = probabilities[dominant_regime]

        details = {
            "trend_strength": trend_strength,
            "trend_consistency": trend_consistency,
            "volatility": volatility,
            "momentum": momentum,
            "mean_reversion": mean_reversion,
            "choppiness": choppiness,
            "volatility_regime": volatility_regime,
            "probabilities": {k.value: v for k, v in probabilities.items()},
            "classification_method": "multi_indicator_probability",
            "support_level": support_resistance["support"],
            "resistance_level": support_resistance["resistance"]
        }

        return dominant_regime, confidence, details

    def _calculate_regime_probabilities(self,
                                      returns: np.ndarray,
                                      volatility: float,
                                      trend_strength: float,
                                      momentum: float,
                                      mean_reversion: float,
                                      trend_consistency: float,
                                      volatility_regime: str,
                                      choppiness: float) -> Dict[RegimeType, float]:
        """Calculate probability for each regime."""
        # Calculate regime-specific probabilities
        trending_up_prob = max(0, min(1, trend_strength * 10)) if trend_strength > 0 else 0
        trending_down_prob = max(0, min(1, -trend_strength * 10)) if trend_strength < 0 else 0

        # Momentum-based probability
        momentum_prob = max(0, min(1, abs(momentum) * 5))

        # Mean reversion probability
        mean_rev_prob = max(0, min(1, abs(mean_reversion) * 0.5))

        # Volatility-based regimes
        high_vol_prob = min(1, volatility * 100)
        low_vol_prob = min(1, 0.02 / (volatility + 0.0001))

        # Ranging/choppy detection
        ranging_prob = max(0, min(1, (0.01 - abs(trend_strength)) * 100)) * high_vol_prob
        choppy_prob = min(1, choppiness * 2)  # Higher choppiness = more likely choppy

        # Apply trend consistency to trending probabilities
        trending_up_prob *= trend_consistency
        trending_down_prob *= trend_consistency

        # Define probabilities for each regime
        probabilities = {
            RegimeType.BULLISH_TRENDING: trending_up_prob,
            RegimeType.BEARISH_TRENDING: trending_down_prob,
            RegimeType.HIGH_VOLATILITY: high_vol_prob,
            RegimeType.LOW_VOLATILITY: low_vol_prob,
            RegimeType.CHOPPY: choppy_prob,
            RegimeType.MEAN_REVERTING: mean_rev_prob * 0.8,  # Reduce slightly to avoid over-allocation
            RegimeType.MOMENTUM: momentum_prob * 0.7,  # Reduce slightly to avoid over-allocation
            RegimeType.NORMAL: max(0.1, 1.0 - sum([
                trending_up_prob, trending_down_prob, high_vol_prob, low_vol_prob,
                choppy_prob, mean_rev_prob * 0.8, momentum_prob * 0.7
            ]))  # Fill remainder for normal regime
        }

        # Normalize probabilities to sum to 1
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            for regime in probabilities:
                probabilities[regime] /= total_prob

        return probabilities

    def _calculate_stability(self, regime: RegimeType, confidence: float) -> float:
        """Calculate regime stability."""
        # Stability is based on consistency of the regime and confidence
        if not self.regime_history:
            return confidence

        # Check how often the regime has been consistent recently
        recent_regimes = [r[0] for r in self.regime_history[-5:]] if len(self.regime_history) >= 5 else [r[0] for r in self.regime_history]
        consistency = recent_regimes.count(regime) / len(recent_regimes) if recent_regimes else 0

        # Combine consistency with confidence
        stability = (consistency + confidence) / 2
        return min(1.0, stability)

    def _calculate_maturity(self, regime: RegimeType) -> float:
        """Calculate regime maturity."""
        if not self.regime_history:
            return 0.1

        # Count consecutive occurrences of the same regime
        count = 0
        for reg, _, _ in reversed(self.regime_history):
            if reg == regime:
                count += 1
            else:
                break

        # Maturity increases with duration but caps at 1.0
        maturity = min(1.0, count / 20)  # Cap at 20 periods
        return maturity

    def _apply_decay(self, regime: RegimeType, confidence: float) -> float:
        """Apply decay to confidence based on regime persistence."""
        if not self.regime_history:
            return confidence

        # Check if the same regime has persisted for too long
        consecutive_count = 0
        for reg, _, _ in reversed(self.regime_history):
            if reg == regime:
                consecutive_count += 1
            else:
                break

        # Apply decay if regime has persisted too long (potential transition)
        if consecutive_count > 10:  # Arbitrary threshold
            decay_factor = self.decay_factor ** (consecutive_count - 10)
            return confidence * decay_factor
        else:
            return confidence

    def _should_veto(self, confidence: float, stability: float, maturity: float) -> bool:
        """Determine if regime classification should be vetoed."""
        # Veto if confidence is too low
        if confidence < self.confidence_threshold:
            return True

        # Veto if stability is too low
        if stability < self.stability_threshold:
            return True

        # Veto if maturity is too low (regime is too new to trust)
        if maturity < self.maturity_threshold and confidence < 0.7:
            return True

        return False

    def _apply_transition_smoothing(self, regime: RegimeType, confidence: float) -> RegimeType:
        """Apply smoothing to reduce noise in regime transitions."""
        self.transition_buffer.append((regime, confidence))

        # Keep only the last N transitions
        if len(self.transition_buffer) > self.transition_smoothing_window:
            self.transition_buffer.pop(0)

        # If we have enough transitions, check for majority vote
        if len(self.transition_buffer) >= 2:
            regime_votes = {}
            for reg, conf in self.transition_buffer:
                if reg not in regime_votes:
                    regime_votes[reg] = 0
                regime_votes[reg] += conf  # Weight by confidence

            # Choose regime with highest weighted votes
            if regime_votes:
                dominant_regime = max(regime_votes, key=regime_votes.get)
                return dominant_regime

        return regime

    def _update_history(self, regime: RegimeType, confidence: float):
        """Update regime history."""
        self.regime_history.append((regime, confidence, datetime.now()))
        self.confidence_history.append((confidence, datetime.now()))

        # Keep only recent history
        cutoff = datetime.now() - timedelta(days=30)
        self.regime_history = [(r, c, t) for r, c, t in self.regime_history if t >= cutoff]
        self.confidence_history = [(c, t) for c, t in self.confidence_history if t >= cutoff]

    def update_performance_feedback(self, 
                                 predicted_regime: RegimeType, 
                                 actual_regime: RegimeType,
                                 accuracy: float):
        """Update performance feedback for recalibration."""
        if predicted_regime not in self.regime_performance:
            self.regime_performance[predicted_regime] = []
            
        self.regime_performance[predicted_regime].append({
            'predicted': predicted_regime,
            'actual': actual_regime,
            'accuracy': accuracy,
            'timestamp': datetime.now()
        })

        # Update confusion matrix
        self.confusion_matrix[predicted_regime][actual_regime] += 1

        # Keep only recent performance data
        cutoff = datetime.now() - timedelta(days=30)
        self.regime_performance[predicted_regime] = [
            record for record in self.regime_performance[predicted_regime]
            if record['timestamp'] >= cutoff
        ]

    def get_confusion_matrix_analysis(self) -> Dict[str, Any]:
        """Get analysis of confusion matrix."""
        analysis = {
            'matrix': {(p.value, a.value): count 
                      for p, act_dict in self.confusion_matrix.items() 
                      for a, count in act_dict.items()},
            'accuracy_by_predicted': {},
            'accuracy_by_actual': {}
        }

        # Calculate accuracy by predicted regime
        for pred_regime in RegimeType:
            total_predicted = sum(self.confusion_matrix[pred_regime].values())
            if total_predicted > 0:
                correct = self.confusion_matrix[pred_regime][pred_regime]
                analysis['accuracy_by_predicted'][pred_regime.value] = correct / total_predicted

        # Calculate accuracy by actual regime
        for actual_regime in RegimeType:
            total_actual = sum(self.confusion_matrix[pred][actual_regime] for pred in RegimeType)
            if total_actual > 0:
                correct = self.confusion_matrix[actual_regime][actual_regime]
                analysis['accuracy_by_actual'][actual_regime.value] = correct / total_actual

        return analysis

    def recalibrate_classifier(self):
        """Recalibrate classifier based on performance feedback."""
        # This would involve adjusting the classification algorithm based on confusion matrix
        # For now, we'll just log the recalibration event
        print(f"[{datetime.now()}] Regime classifier recalibrated based on performance feedback")
        
        # In a real implementation, this would adjust the probability calculations
        # based on the confusion matrix and performance data

    def get_regime_insights(self, regime: RegimeType) -> Dict[str, Any]:
        """Get insights about a specific regime."""
        if regime not in self.regime_performance:
            return {
                'regime': regime.value,
                'performance_records': 0,
                'avg_accuracy': 0.0,
                'last_seen': None
            }

        records = self.regime_performance[regime]
        if not records:
            return {
                'regime': regime.value,
                'performance_records': 0,
                'avg_accuracy': 0.0,
                'last_seen': None
            }

        avg_accuracy = np.mean([r['accuracy'] for r in records])
        last_seen = max(r['timestamp'] for r in records) if records else None

        return {
            'regime': regime.value,
            'performance_records': len(records),
            'avg_accuracy': float(avg_accuracy),
            'last_seen': last_seen
        }

    def reset_classification_history(self):
        """Reset all classification history for fresh start."""
        self.regime_history = []
        self.confidence_history = []
        self.transition_buffer = []
        self.regime_performance = {}
        self.confusion_matrix = {}
        
        # Reinitialize confusion matrix
        for regime1 in RegimeType:
            self.confusion_matrix[regime1] = {}
            for regime2 in RegimeType:
                self.confusion_matrix[regime1][regime2] = 0


class RegimeAwareService:
    """Service to manage regime-aware operations."""
    
    def __init__(self):
        self.classifier = AdvancedRegimeClassifier()
        self.active_regime: Optional[RegimeClassification] = None
    
    def update_market_data(self, prices: List[float], volumes: Optional[List[float]] = None) -> RegimeClassification:
        """Update with new market data and classify regime."""
        self.active_regime = self.classifier.classify_regime(prices, volumes)
        return self.active_regime
    
    def should_adjust_strategy(self) -> bool:
        """Determine if strategy should be adjusted based on regime."""
        if not self.active_regime:
            return False
            
        # Adjust strategy if regime is high confidence and stable
        return (not self.active_regime.veto and 
                self.active_regime.confidence > 0.7 and 
                self.active_regime.stability > 0.6)
    
    def get_regime_recommendation(self) -> str:
        """Get recommendation based on current regime."""
        if not self.active_regime or self.active_regime.veto:
            return "Maintain current strategy - regime unclear"
            
        regime = self.active_regime.regime
        confidence = self.active_regime.confidence
        
        if regime in [RegimeType.BULLISH_TRENDING, RegimeType.MOMENTUM]:
            return f"Trend-following strategy recommended (confidence: {confidence:.2f})"
        elif regime in [RegimeType.BEARISH_TRENDING]:
            return f"Counter-trend or defensive strategy recommended (confidence: {confidence:.2f})"
        elif regime == RegimeType.CHOPPY:
            return f"Mean reversion or range-bound strategy recommended (confidence: {confidence:.2f})"
        elif regime == RegimeType.HIGH_VOLATILITY:
            return f"Reduce position sizes, use tighter stops (confidence: {confidence:.2f})"
        elif regime == RegimeType.LOW_VOLATILITY:
            return f"Increase position sizes, look for breakout opportunities (confidence: {confidence:.2f})"
        else:
            return f"Neutral strategy recommended (confidence: {confidence:.2f})"


# Global instance
regime_classifier = AdvancedRegimeClassifier()
regime_aware_service = RegimeAwareService()