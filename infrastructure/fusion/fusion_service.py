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
        """Enhanced fusion method with weighted signal combination and correlation analysis"""
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

        # Aggregate multiple signals using enhanced method with correlation analysis
        try:
            # Calculate aggregated values
            symbol = interpreted_signals[0].symbol  # All signals should be for the same symbol
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            timestamp = datetime.now()

            # Calculate weighted average direction based on confidence and strength with correlation analysis
            total_weight = 0.0
            weighted_direction = 0.0
            weighted_strength = 0.0

            # Log individual signals before fusion
            if self.logger:
                self.logger.info(f"Enhanced Fusion: Processing {len(interpreted_signals)} signals for {symbol_str}:")
                for i, signal in enumerate(interpreted_signals):
                    self.logger.info(f"  Signal {i+1}: Type={signal.signal_type.value}, "
                                   f"Direction={signal.direction:.3f}, "
                                   f"Strength={signal.strength:.3f}, "
                                   f"Confidence={float(signal.confidence.value):.3f}, "
                                   f"Source={getattr(signal, 'source_watcher', 'unknown')}")

            # Perform correlation analysis between signals
            correlation_factor = self._calculate_signal_correlation(interpreted_signals)

            # Apply weights based on confidence, strength, and correlation
            for signal in interpreted_signals:
                # Calculate base weight from confidence and strength
                base_weight = float(signal.confidence.value) * signal.strength

                # Apply correlation factor to adjust weight
                # Signals that correlate well with others get higher weight
                adjusted_weight = base_weight * correlation_factor
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

            # Calculate overall confidence considering correlation
            confidences = [float(s.confidence.value) for s in interpreted_signals]
            avg_confidence = statistics.mean(confidences)

            # Adjust confidence based on correlation - higher correlation increases confidence
            adjusted_confidence = min(1.0, avg_confidence * correlation_factor)

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
                confidence=Percentage(Decimal(str(adjusted_confidence))),
                timestamp=timestamp,
                metadata={
                    'original_signals_count': len(interpreted_signals),
                    'regime_determination': 'calculated',
                    'fusion_method': 'enhanced_weighted_average',
                    'correlation_factor': correlation_factor,
                    'signal_diversity': len(unique_types)
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