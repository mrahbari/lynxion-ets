"""
Enhanced Fusion service for aggregating interpreted signals into fused signals.
Now includes hierarchical decision making with role-based watcher classification.
Following the correct architecture: Watcher → Engine → Fusion → Strategy → Broker
"""
import os
from typing import List, Optional, Dict, Any
from domain.entities.signal_entities import InterpretedSignal, FusedSignal, MarketObservation
from domain.value_objects import Symbol, Percentage
from datetime import datetime
from decimal import Decimal
import statistics

from .hierarchical.hierarchical_fusion_service import hierarchical_fusion_service, HierarchicalFusionService
from .hierarchical.watcher_classifier import WatcherClassifier
from .hierarchical.confidence_thresholds import ConfidenceThresholds
from infrastructure.logging.forensic_logger import forensic_logger
import numpy as np
from scipy import stats
from application.configs.configs import Configs


class PerformanceAdaptiveFusionService:
    """
    Redesigned Fusion Service with performance-adaptive and correlation-penalizing mechanisms.

    Mathematical Formula:
    Weight_i = (Performance_Score_i * Stability_Factor_i * Regime_Adjustment_i) /
               (1 + Correlation_Penalty_i) * Timeframe_Adjustment_i

    Where:
    - Performance_Score_i = f(historical_accuracy, recent_performance, consistency)
    - Correlation_Penalty_i = sum(correlation_with_other_signals * penalty_factor)
    - Stability_Factor_i = measure of signal consistency over time
    - Regime_Adjustment_i = adjustment based on regime compatibility
    - Timeframe_Adjustment_i = adjustment based on timeframe alignment
    """

    def __init__(self,
                 correlation_penalty_factor: float = 0.3,
                 performance_decay_factor: float = 0.95,
                 stability_importance: float = 0.2,
                 regime_importance: float = 0.2,
                 timeframe_importance: float = 0.1):

        self.correlation_penalty_factor = correlation_penalty_factor
        self.performance_decay_factor = performance_decay_factor
        self.stability_importance = stability_importance
        self.regime_importance = regime_importance
        self.timeframe_importance = timeframe_importance

    def calculate_weights(self,
                        signals: List[Dict[str, Any]],
                        correlation_matrix: Optional[np.ndarray] = None,
                        regime_context: str = "normal",
                        timeframe: str = "H1") -> Dict[str, float]:
        """
        Calculate adaptive weights for fusion with correlation penalties.
        """
        signal_names = [signal.get('name', f'signal_{i}') for i, signal in enumerate(signals)]

        # Calculate individual performance scores
        performance_scores = self._calculate_performance_scores(signals)

        # Calculate stability factors
        stability_factors = self._calculate_stability_factors(signals)

        # Calculate regime adjustments
        regime_adjustments = self._calculate_regime_adjustments(signals, regime_context)

        # Calculate timeframe adjustments
        timeframe_adjustments = self._calculate_timeframe_adjustments(signals, timeframe)

        # Calculate correlation penalties
        correlation_penalties = self._calculate_correlation_penalties(
            signal_names, correlation_matrix
        )

        # Calculate final weights
        weights = {}
        for i, name in enumerate(signal_names):
            # Combine all factors
            combined_score = (
                performance_scores.get(name, 0.5) *
                (1 + stability_factors.get(name, 0.0) * self.stability_importance) *
                (1 + regime_adjustments.get(name, 0.0) * self.regime_importance) *
                (1 + timeframe_adjustments.get(name, 0.0) * self.timeframe_importance)
            )

            # Apply correlation penalty
            penalty = correlation_penalties.get(name, 0.0) * self.correlation_penalty_factor
            penalized_score = combined_score / (1 + penalty)

            weights[name] = max(0.0, penalized_score)  # Ensure non-negative weights

        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            normalized_weights = {name: weight / total_weight for name, weight in weights.items()}
        else:
            # If all weights are zero, assign equal weights
            normalized_weights = {name: 1.0 / len(signal_names) for name in signal_names}

        return normalized_weights

    def _calculate_performance_scores(self, signals: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate performance scores based on historical accuracy and recent performance.
        """
        scores = {}
        for signal in signals:
            name = signal.get('name', 'unknown')

            # Get historical performance metrics
            historical_accuracy = signal.get('historical_accuracy', 0.5)
            recent_performance = signal.get('recent_performance', 0.5)
            consistency_score = signal.get('consistency_score', 0.5)

            # Calculate weighted performance score
            performance_score = (
                0.4 * historical_accuracy +
                0.4 * recent_performance +
                0.2 * consistency_score
            )

            # Apply decay to older performance data
            age_factor = signal.get('performance_age_factor', 1.0)
            final_score = performance_score * (self.performance_decay_factor ** age_factor)

            scores[name] = max(0.0, min(1.0, final_score))

        return scores

    def _calculate_stability_factors(self, signals: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate stability factors based on signal consistency over time.
        """
        factors = {}
        for signal in signals:
            name = signal.get('name', 'unknown')

            # Get stability metrics
            variance = signal.get('variance', 0.1)  # Lower variance = more stable
            trend_consistency = signal.get('trend_consistency', 0.5)
            signal_noise_ratio = signal.get('signal_noise_ratio', 0.5)

            # Calculate stability score (inverse of variance, plus other factors)
            stability_score = (
                (1.0 - min(1.0, variance * 10)) * 0.5 +  # Inverse of variance (clamped)
                trend_consistency * 0.3 +
                signal_noise_ratio * 0.2
            )

            factors[name] = max(-1.0, min(1.0, stability_score))

        return factors

    def _calculate_regime_adjustments(self, signals: List[Dict[str, Any]], regime_context: str) -> Dict[str, float]:
        """
        Calculate regime adjustments based on signal compatibility with current regime.
        """
        adjustments = {}
        for signal in signals:
            name = signal.get('name', 'unknown')

            # Get regime compatibility scores
            regime_compatibilities = signal.get('regime_compatibilities', {})
            compatibility_score = regime_compatibilities.get(regime_context.lower(), 0.5)

            # Apply regime-specific adjustment
            if regime_context.lower() in ['trending_up', 'trending_down']:
                # Trend-following signals get boost in trending markets
                if 'trend' in name.lower() or 'momentum' in name.lower():
                    compatibility_score = min(1.0, compatibility_score * 1.2)
            elif regime_context.lower() in ['choppy', 'mean_reverting']:
                # Mean-reversion signals get boost in choppy markets
                if 'mean' in name.lower() or 'reversion' in name.lower() or 'rsi' in name.lower():
                    compatibility_score = min(1.0, compatibility_score * 1.2)

            adjustments[name] = max(-1.0, min(1.0, compatibility_score - 0.5))  # Center around 0

        return adjustments

    def _calculate_timeframe_adjustments(self, signals: List[Dict[str, Any]], timeframe: str) -> Dict[str, float]:
        """
        Calculate timeframe adjustments based on signal alignment with current timeframe.
        """
        adjustments = {}
        for signal in signals:
            name = signal.get('name', 'unknown')

            # Get timeframe compatibility
            signal_timeframes = signal.get('compatible_timeframes', [])
            timeframe_match = 1.0 if timeframe in signal_timeframes else 0.5

            # Apply adjustment based on timeframe alignment
            if timeframe_match > 0.5:
                # Signals compatible with current timeframe get positive adjustment
                adjustments[name] = min(0.5, timeframe_match - 0.5)
            else:
                # Signals not compatible get negative adjustment
                adjustments[name] = max(-0.5, timeframe_match - 0.5)

        return adjustments

    def _calculate_correlation_penalties(self,
                                       signal_names: List[str],
                                       correlation_matrix: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Calculate correlation penalties based on inter-signal correlations.
        """
        penalties = {}

        if correlation_matrix is not None and len(signal_names) > 1:
            # Calculate average correlation for each signal with others
            n = len(signal_names)
            for i, name in enumerate(signal_names):
                if i < correlation_matrix.shape[0]:
                    # Sum correlations with all other signals (excluding self-correlation)
                    correlations = []
                    for j in range(n):
                        if i != j and j < correlation_matrix.shape[1]:
                            correlations.append(abs(correlation_matrix[i, j]))

                    if correlations:
                        avg_correlation = np.mean(correlations)
                        penalties[name] = max(0.0, min(2.0, avg_correlation))  # Clamp penalty
                    else:
                        penalties[name] = 0.0
                else:
                    penalties[name] = 0.0
        else:
            # If no correlation matrix provided, use default penalties based on signal similarity
            for name in signal_names:
                # For now, assign minimal penalties if no correlation data
                penalties[name] = 0.0

        return penalties

    def update_weights_over_time(self,
                               current_weights: Dict[str, float],
                               performance_updates: Dict[str, float],
                               new_correlations: Optional[Dict[str, Dict[str, float]]] = None) -> Dict[str, float]:
        """
        Update weights based on new performance data and correlations.
        """
        updated_weights = current_weights.copy()

        # Adjust weights based on performance updates
        for name, perf_update in performance_updates.items():
            if name in updated_weights:
                # Apply performance-based adjustment
                adjustment = perf_update * 0.1  # Small adjustment based on performance
                updated_weights[name] = max(0.0, min(1.0, updated_weights[name] + adjustment))

        # Recalculate correlation penalties if new correlation data provided
        if new_correlations:
            # Calculate new penalties based on updated correlations
            for name in updated_weights.keys():
                if name in new_correlations:
                    # Sum correlations with other signals
                    total_corr = sum(new_correlations[name].values())
                    penalty = total_corr * self.correlation_penalty_factor
                    # Apply penalty to weight
                    updated_weights[name] = updated_weights[name] / (1 + penalty)

        # Renormalize weights to sum to 1
        total_weight = sum(updated_weights.values())
        if total_weight > 0:
            normalized_weights = {name: weight / total_weight for name, weight in updated_weights.items()}
        else:
            # If all weights become zero, assign equal weights
            n_signals = len(updated_weights)
            normalized_weights = {name: 1.0 / n_signals for name in updated_weights.keys()}

        return normalized_weights

    def suppress_noise(self, weights: Dict[str, float], signals: List[Dict[str, Any]],
                      noise_threshold: float = 0.3) -> Dict[str, float]:
        """
        Suppress weights for noisy signals based on noise metrics.
        """
        suppressed_weights = weights.copy()

        for i, signal in enumerate(signals):
            name = signal.get('name', f'signal_{i}')

            # Check if signal is too noisy
            noise_level = signal.get('noise_level', 0.0)
            if noise_level > noise_threshold:
                # Reduce weight for noisy signals
                suppression_factor = max(0.1, 1.0 - (noise_level - noise_threshold))
                suppressed_weights[name] = weights[name] * suppression_factor

        # Renormalize after suppression
        total_weight = sum(suppressed_weights.values())
        if total_weight > 0:
            normalized_weights = {name: weight / total_weight for name, weight in suppressed_weights.items()}
        else:
            # If all weights are suppressed, assign equal weights
            n_signals = len(suppressed_weights)
            normalized_weights = {name: 1.0 / n_signals for name in suppressed_weights.keys()}

        return normalized_weights


class FusionService:
    """Service to aggregate interpreted signals into fused signals with hierarchical decision making"""

    def __init__(self):
        self.logger = None  # Will be set by the calling component if needed
        self.hierarchical_service = hierarchical_fusion_service
        self.watcher_classifier = WatcherClassifier()
        self.confidence_thresholds = ConfidenceThresholds()

        # Add the redesigned fusion service
        self.performance_adaptive_fusion = PerformanceAdaptiveFusionService()

    def fuse_signals(self, interpreted_signals: List[InterpretedSignal]) -> Optional[FusedSignal]:
        """Aggregate multiple interpreted signals into a single fused signal"""
        if not interpreted_signals:
            if self.logger:
                self.logger.info("No interpreted signals to fuse")
            return None

        # Check if we have observation-based signals that can use hierarchical fusion
        if hasattr(interpreted_signals[0], 'source_watcher') and interpreted_signals[0].source_watcher:
            # Convert interpreted signals back to observation format for hierarchical processing
            observations_with_watchers = []
            for signal in interpreted_signals:
                # Create a mock observation from the interpreted signal for hierarchical processing
                mock_observation = MarketObservation(
                    symbol=signal.symbol,
                    observation_type=f"{signal.signal_type.value.lower()}_signal",
                    observation_value=signal.direction,
                    confidence=signal.confidence,
                    timestamp=signal.timestamp,
                    metadata=signal.metadata or {}
                )
                
                observations_with_watchers.append({
                    'observation': mock_observation,
                    'watcher_name': getattr(signal, 'source_watcher', 'unknown')
                })
            
            # Use hierarchical fusion if available
            try:
                return self.hierarchical_service.fuse_signals_hierarchically(
                    observations_with_watchers, 
                    interpreted_signals[0].symbol
                )
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in hierarchical fusion: {e}, falling back to standard fusion")
        
        # Fallback to enhanced fusion for better correlation analysis
        return self._enhanced_fuse_signals(interpreted_signals)

    def _enhanced_fuse_signals(self, interpreted_signals: List[InterpretedSignal]) -> Optional[FusedSignal]:
        """Enhanced fusion method with performance-based, regime-conditional, correlation-adjusted, and stability-controlled weighting"""
        if not interpreted_signals:
            if self.logger:
                self.logger.info("No interpreted signals to fuse")
            return None

        if len(interpreted_signals) == 1:
            # If only one signal, convert it directly to a fused signal
            single_signal = interpreted_signals[0]
            # Determine regime context based on the single signal
            signal_types = {single_signal.signal_type}
            regime_context = self._determine_regime_context(signal_types, single_signal.strength)

            if self.logger:
                symbol = single_signal.symbol.value if hasattr(single_signal.symbol, 'value') else str(single_signal.symbol)
                self.logger.info(f"Fusion: Single signal for {symbol} - Type: {single_signal.signal_type.value}, "
                               f"Direction: {single_signal.direction:.3f}, Confidence: {float(single_signal.confidence.value):.3f}")

            return FusedSignal(
                symbol=single_signal.symbol,
                dominant_bias=single_signal.signal_type,
                direction=single_signal.direction,
                dominance_score=float(single_signal.confidence.value) * single_signal.strength,
                regime_context=regime_context,
                confidence=single_signal.confidence,
                timestamp=single_signal.timestamp,
                metadata=single_signal.metadata or {}
            )

        # Aggregate multiple signals using enhanced method with advanced weighting
        try:
            # Calculate aggregated values
            symbol = interpreted_signals[0].symbol  # All signals should be for the same symbol
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            timestamp = datetime.now()

            # Determine regime context based on signal diversity
            signal_types = [s.signal_type for s in interpreted_signals]
            unique_types = set(s.value for s in signal_types)
            regime_context = self._determine_regime_context(unique_types, 0.0)  # We'll calculate avg_strength later

            # Calculate performance-based weights
            performance_weights = self._calculate_performance_based_weights(interpreted_signals, regime_context)

            # Calculate correlation factor between signals
            correlation_factor = self._calculate_signal_correlation(interpreted_signals)

            # Apply weights to calculate weighted averages
            total_weight = 0.0
            weighted_direction = 0.0
            weighted_strength = 0.0

            # Log individual signals before fusion
            if self.logger:
                self.logger.info(f"Enhanced Fusion: Processing {len(interpreted_signals)} signals for {symbol_str}:")
                for i, signal in enumerate(interpreted_signals):
                    perf_weight = performance_weights[i]
                    self.logger.info(f"  Signal {i+1}: Type={signal.signal_type.value}, "
                                   f"Direction={signal.direction:.3f}, "
                                   f"Strength={signal.strength:.3f}, "
                                   f"Confidence={float(signal.confidence.value):.3f}, "
                                   f"Performance Weight={perf_weight:.3f}, "
                                   f"Source={getattr(signal, 'source_watcher', 'unknown')}")

            # Apply the calculated weights to aggregate signals
            for i, signal in enumerate(interpreted_signals):
                # Use the performance-based weight for this signal
                weight = performance_weights[i]

                # Apply correlation adjustment to the weight
                adjusted_weight = weight * correlation_factor

                weighted_direction += signal.direction * adjusted_weight
                weighted_strength += signal.strength * adjusted_weight
                total_weight += adjusted_weight

            if total_weight > 0:
                avg_direction = weighted_direction / total_weight
                avg_strength = weighted_strength / total_weight
            else:
                avg_direction = 0.0
                avg_strength = 0.0

            # Determine dominant bias based on average direction
            from domain.entities.signal_entities import SignalType
            if avg_direction > 0.01:  # Lowered threshold from 0.1 to 0.01 to avoid neutral signals
                dominant_bias = SignalType.BUY
            elif avg_direction < -0.01:  # Lowered threshold from -0.1 to -0.01
                dominant_bias = SignalType.SELL
            else:
                dominant_bias = SignalType.NEUTRAL

            # Calculate overall confidence considering all factors
            confidences = [float(s.confidence.value) for s in interpreted_signals]
            avg_confidence = statistics.mean(confidences)

            # Adjust confidence based on correlation and performance weighting
            adjusted_confidence = min(1.0, avg_confidence * correlation_factor)

            # Update regime context with calculated strength
            regime_context = self._determine_regime_context(unique_types, avg_strength)

            # Create fused signal
            fused_signal = FusedSignal(
                symbol=symbol,
                dominant_bias=dominant_bias,
                direction=avg_direction,
                dominance_score=avg_strength,
                regime_context=regime_context,
                confidence=Percentage(Decimal(str(adjusted_confidence))),
                timestamp=timestamp,
                metadata={
                    'original_signals_count': len(interpreted_signals),
                    'regime_determination': 'calculated',
                    'fusion_method': 'enhanced_performance_based_weighting',
                    'correlation_factor': correlation_factor,
                    'signal_diversity': len(unique_types),
                    'performance_weights_applied': True,
                    'regime_conditional_weights': True,
                    'stability_controlled': True
                }
            )

            if self.logger:
                self.logger.info(f"Enhanced Fusion complete for {symbol_str}: "
                               f"Count={len(interpreted_signals)}, "
                               f"Dominant Bias={dominant_bias.value}, "
                               f"Direction={avg_direction:.3f}, "
                               f"Strength={avg_strength:.3f}, "
                               f"Confidence={adjusted_confidence:.3f}, "
                               f"Correlation Factor={correlation_factor:.3f}, "
                               f"Regime={regime_context}")

            # Log the fusion result to forensic log with enhanced details
            # Extract contributors from the interpreted signals
            contributors = {}
            rejected_engines = []

            for i, signal in enumerate(interpreted_signals):
                source = getattr(signal, 'source_engine', 'Unknown')
                contributors[source] = performance_weights[i]  # Use performance-based weight

                # Identify if any signals were rejected (low performance weight or other factors)
                if performance_weights[i] < 0.05:  # Very low performance weight indicates rejection
                    rejected_engines.append({
                        'engine': source,
                        'confidence': float(signal.confidence.value),
                        'strength': signal.strength,
                        'direction': signal.direction,
                        'performance_weight': performance_weights[i]
                    })

            # Prepare decision reason
            decision_reason = f"Aggregated {len(interpreted_signals)} signals with {regime_context} regime context using performance-based weighting. "
            if len(interpreted_signals) > 1:
                decision_reason += f"Dominant bias from {len(contributors)} engines with performance and regime adjustments."
            else:
                decision_reason += "Single signal processed."

            forensic_logger.log_fusion_result(
                symbol=symbol_str,
                exchange=getattr(symbol, 'exchange', 'BINANCE'),  # Use exchange from symbol if available
                regime=regime_context,
                fused_direction=dominant_bias.value,
                confidence=adjusted_confidence,
                contributors=contributors,
                decision_reason=decision_reason,
                rejected_engines=rejected_engines,
                timestamp=timestamp
            )

            return fused_signal

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error fusing signals: {e}")
            return None

    def _calculate_signal_correlation(self, interpreted_signals: List[InterpretedSignal]) -> float:
        """Calculate correlation factor between signals to weight their importance"""
        if len(interpreted_signals) < 2:
            return 1.0  # No correlation to calculate with single signal

        # Calculate correlation based on direction agreement
        directions = [signal.direction for signal in interpreted_signals]
        confidences = [float(signal.confidence.value) for signal in interpreted_signals]

        # Calculate how many signals agree on direction (same sign)
        positive_signals = sum(1 for d in directions if d > 0)
        negative_signals = sum(1 for d in directions if d < 0)

        # Calculate direction consensus (higher consensus = higher correlation factor)
        max_agreement = max(positive_signals, negative_signals)
        consensus_ratio = max_agreement / len(directions)

        # Calculate average confidence of agreeing signals
        agreeing_confidences = []
        for i, direction in enumerate(directions):
            if (direction > 0 and positive_signals >= negative_signals) or \
               (direction < 0 and negative_signals >= positive_signals):
                agreeing_confidences.append(confidences[i])

        avg_agreeing_confidence = statistics.mean(agreeing_confidences) if agreeing_confidences else 0.5

        # Combine consensus ratio and confidence to get correlation factor
        # Higher consensus and higher confidence of agreeing signals = higher correlation
        import os
        consensus_weight = Configs.fusion.correlation_consensus_weight if Configs.fusion and hasattr(Configs.fusion, 'correlation_consensus_weight') else 0.6
        confidence_weight = Configs.fusion.correlation_confidence_weight if Configs.fusion and hasattr(Configs.fusion, 'correlation_confidence_weight') else 0.4
        correlation_factor = consensus_weight * consensus_ratio + confidence_weight * avg_agreeing_confidence

        # Ensure correlation factor is between 0.5 and 1.5 to avoid extreme adjustments
        correlation_factor = max(0.5, min(1.5, correlation_factor))

        return correlation_factor

    def _calculate_performance_based_weights(self, interpreted_signals: List[InterpretedSignal],
                                           regime_context: str) -> List[float]:
        """Calculate performance-based weights for signals based on historical performance"""
        weights = []

        for signal in interpreted_signals:
            # Base weight from confidence and strength
            base_weight = float(signal.confidence.value) * signal.strength

            # Adjust weight based on regime compatibility
            regime_factor = self._get_regime_compatibility_factor(signal, regime_context)

            # Adjust weight based on signal stability (consistency over time)
            stability_factor = self._get_signal_stability_factor(signal)

            # Calculate final weight
            final_weight = base_weight * regime_factor * stability_factor
            weights.append(final_weight)

        # Normalize weights so they sum to 1
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
        else:
            # If all weights are zero, assign equal weights
            normalized_weights = [1.0 / len(weights)] * len(weights)

        return normalized_weights

    def _get_regime_compatibility_factor(self, signal: InterpretedSignal, regime_context: str) -> float:
        """Get regime compatibility factor for a signal"""
        # Different signals may perform differently in different regimes
        # This is a simplified version - in a real system, this would be based on historical performance
        if regime_context == "trending":
            # Trend-following signals perform better in trending markets
            if "trend" in getattr(signal, 'source_watcher', '').lower() or \
               "momentum" in getattr(signal, 'source_watcher', '').lower():
                return 1.2  # Boost trend-following signals in trending regime
            else:
                return 0.8  # Reduce weight for counter-trend signals in trending regime
        elif regime_context == "mean_reverting":
            # Mean reversion signals perform better in mean reverting markets
            if "mean" in getattr(signal, 'source_watcher', '').lower() or \
               "rsi" in getattr(signal, 'source_watcher', '').lower() or \
               "bollinger" in getattr(signal, 'source_watcher', '').lower():
                return 1.2  # Boost mean reversion signals in mean reverting regime
            else:
                return 0.8  # Reduce weight for trend-following signals in mean reverting regime
        elif regime_context == "volatile":
            # In volatile markets, all signals might be less reliable
            return 0.9
        else:
            # Default factor for other regimes
            return 1.0

    def _get_signal_stability_factor(self, signal: InterpretedSignal) -> float:
        """Get stability factor based on signal consistency"""
        # This is a simplified version - in a real system, this would track historical consistency
        # For now, we'll use confidence as a proxy for stability
        confidence = float(signal.confidence.value)

        # Higher confidence suggests more stable signal
        if confidence > 0.8:
            return 1.1  # Very confident signals get slight boost
        elif confidence > 0.6:
            return 1.0  # Moderate confidence gets normal weight
        elif confidence > 0.4:
            return 0.9  # Low confidence gets slight reduction
        else:
            return 0.7  # Very low confidence gets significant reduction

    def _standard_fuse_signals(self, interpreted_signals: List[InterpretedSignal]) -> Optional[FusedSignal]:
        """Original fusion method for backward compatibility"""
        if not interpreted_signals:
            if self.logger:
                self.logger.info("No interpreted signals to fuse")
            return None

        if len(interpreted_signals) == 1:
            # If only one signal, convert it directly to a fused signal
            single_signal = interpreted_signals[0]
            # Determine regime context based on the single signal
            signal_types = {single_signal.signal_type}
            regime_context = self._determine_regime_context(signal_types, single_signal.strength)

            if self.logger:
                symbol = single_signal.symbol.value if hasattr(single_signal.symbol, 'value') else str(single_signal.symbol)
                self.logger.info(f"Fusion: Single signal for {symbol} - Type: {single_signal.signal_type.value}, "
                               f"Direction: {single_signal.direction:.3f}, Confidence: {float(single_signal.confidence.value):.3f}")

            return FusedSignal(
                symbol=single_signal.symbol,
                dominant_bias=single_signal.signal_type,
                direction=single_signal.direction,
                dominance_score=float(single_signal.confidence.value) * single_signal.strength,
                regime_context=regime_context,
                confidence=single_signal.confidence,
                timestamp=single_signal.timestamp,
                metadata=single_signal.metadata or {}
            )

        # Aggregate multiple signals using the original method
        try:
            # Calculate aggregated values
            symbol = interpreted_signals[0].symbol  # All signals should be for the same symbol
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            timestamp = datetime.now()

            # Calculate weighted average direction based on confidence and strength
            total_weight = 0.0
            weighted_direction = 0.0
            weighted_strength = 0.0

            # Log individual signals before fusion
            if self.logger:
                self.logger.info(f"Fusion: Processing {len(interpreted_signals)} signals for {symbol_str}:")
                for i, signal in enumerate(interpreted_signals):
                    self.logger.info(f"  Signal {i+1}: Type={signal.signal_type.value}, "
                                   f"Direction={signal.direction:.3f}, "
                                   f"Strength={signal.strength:.3f}, "
                                   f"Confidence={float(signal.confidence.value):.3f}, "
                                   f"Source={getattr(signal, 'source_watcher', 'unknown')}")

            for signal in interpreted_signals:
                weight = float(signal.confidence.value) * signal.strength
                weighted_direction += signal.direction * weight
                weighted_strength += signal.strength * weight
                total_weight += weight

            if total_weight > 0:
                avg_direction = weighted_direction / total_weight
                avg_strength = weighted_strength / total_weight
            else:
                avg_direction = 0.0
                avg_strength = 0.0

            # Determine dominant bias based on average direction
            from domain.entities.signal_entities import SignalType
            if avg_direction > 0.01:  # Lowered threshold from 0.1 to 0.01 to avoid neutral signals
                dominant_bias = SignalType.BUY
            elif avg_direction < -0.01:  # Lowered threshold from -0.1 to -0.01
                dominant_bias = SignalType.SELL
            else:
                dominant_bias = SignalType.NEUTRAL

            # Calculate overall confidence as average of individual confidences
            confidences = [float(s.confidence.value) for s in interpreted_signals]
            avg_confidence = statistics.mean(confidences)

            # Determine regime context based on signal diversity
            signal_types = [s.signal_type for s in interpreted_signals]
            unique_types = set(s.value for s in signal_types)
            regime_context = self._determine_regime_context(unique_types, avg_strength)

            # Create fused signal
            fused_signal = FusedSignal(
                symbol=symbol,
                dominant_bias=dominant_bias,
                direction=avg_direction,
                dominance_score=avg_strength,
                regime_context=regime_context,
                confidence=Percentage(Decimal(str(avg_confidence))),
                timestamp=timestamp,
                metadata={
                    'original_signals_count': len(interpreted_signals),
                    'regime_determination': 'calculated',
                    'fusion_method': 'weighted_average'
                }
            )

            if self.logger:
                self.logger.info(f"Fusion complete for {symbol_str}: "
                               f"Count={len(interpreted_signals)}, "
                               f"Dominant Bias={dominant_bias.value}, "
                               f"Direction={avg_direction:.3f}, "
                               f"Strength={avg_strength:.3f}, "
                               f"Confidence={avg_confidence:.3f}, "
                               f"Regime={regime_context}")

            return fused_signal

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error fusing signals: {e}")
            return None

    def _determine_regime_context(self, unique_signal_types: set, avg_strength: float) -> str:
        """Determine market regime context based on signal characteristics"""
        if len(unique_signal_types) == 1:
            # Consensus among signals
            signal = list(unique_signal_types)[0]
            signal_str = signal.value if hasattr(signal, 'value') else str(signal)
            if signal_str in ['BUY', 'SELL']:
                # For single signal type, determine regime based on additional signal characteristics
                # that would suggest different market conditions
                if avg_strength > 0.5:
                    # Strong signals could be trending or volatile depending on other factors
                    # In a real system, we'd incorporate more market data like volatility, volume, etc.
                    # For now, we'll make it dependent on the strength and diversity of signals
                    return "trending"
                else:
                    return "weak_trend"
            else:
                return "stable"
        elif len(unique_signal_types) > 2:
            # Divergence among signals - likely volatile market
            return "volatile" if avg_strength > 0.3 else "uncertain"
        else:
            # Mixed signals - could be transitional or mean-reverting
            # In a real system, we'd analyze more factors like price oscillation, RSI, etc.
            # to determine if it's mean-reverting vs transitional
            return "mean_reverting"  # Changed to mean_reverting for mixed signals

    def fuse_observations_hierarchically(self, observations_with_watchers: List[Dict[str, Any]], symbol: Symbol) -> Optional[FusedSignal]:
        """New method to fuse observations using hierarchical approach"""
        return self.hierarchical_service.fuse_signals_hierarchically(observations_with_watchers, symbol)


# Global fusion service instance
fusion_service = FusionService()