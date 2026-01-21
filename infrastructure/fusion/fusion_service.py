"""
Enhanced Fusion service for aggregating interpreted signals into fused signals.
Now includes hierarchical decision making with role-based watcher classification.
Following the correct architecture: Watcher → Engine → Fusion → Strategy → Broker
"""
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


class FusionService:
    """Service to aggregate interpreted signals into fused signals with hierarchical decision making"""

    def __init__(self):
        self.logger = None  # Will be set by the calling component if needed
        self.hierarchical_service = hierarchical_fusion_service
        self.watcher_classifier = WatcherClassifier()
        self.confidence_thresholds = ConfidenceThresholds()

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
        consensus_weight = float(os.getenv('CORRELATION_CONSENSUS_WEIGHT', '0.6'))
        confidence_weight = float(os.getenv('CORRELATION_CONFIDENCE_WEIGHT', '0.4'))
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