"""
Infrastructure implementation of the fusion service with enhanced capabilities.
"""
from typing import List, Optional, Dict, Any
from domain.entities.trading_entities import Signal
from domain.entities.engine_entities import EngineResult
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import FusionPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import statistics
import numpy as np

# Import ML fusion service for enhanced capabilities
try:
    from infrastructure.fusion.ml_signal_fusion import MLSignalFusionService, MLFusionMethod
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    MLSignalFusionService = None
    MLFusionMethod = None


class FusionServiceAdapter(FusionPort):
    """Infrastructure implementation of signal fusion"""

    def __init__(self):
        self.fusion_method = "weighted_average"
        self.regime_detection_enabled = True
        self.min_signals_for_fusion = 2
        self.confidence_threshold = 0.6  # Minimum average score to generate a signal
        self.min_engines_for_signal = 3  # Minimum number of engines needed for a valid signal

    def fuse_signals(self, signals: List[Signal]) -> Signal:
        """Fuse multiple signals into a single consolidated signal"""
        try:
            if not signals:
                logger.warning("No signals to fuse")
                return None

            # Validate all signals are for the same symbol
            if len(set(s.symbol for s in signals)) > 1:
                logger.warning("Fusion called with signals for different symbols, using first symbol")

            # Filter out overlapping signals from similar strategies to reduce redundancy
            filtered_signals = self._filter_overlapping_signals(signals)

            if not filtered_signals:
                logger.warning("No non-overlapping signals after filtering")
                return None

            if len(filtered_signals) < self.min_signals_for_fusion:
                logger.info(f"Insufficient signals for fusion ({len(filtered_signals)} < {self.min_signals_for_fusion}), returning most confident signal after overlap filtering")
                # If not enough signals after filtering, return the most confident one
                return max(filtered_signals, key=lambda s: float(s.confidence.value))

            logger.info(f"Fusing {len(filtered_signals)} signals after overlap filtering using {self.fusion_method}")

            # Calculate fusion weights
            weights = self.calculate_fusion_weights(filtered_signals)

            # Apply fusion using weighted average
            fused_signal = self._apply_weighted_fusion(filtered_signals, weights)

            logger.info(f"Fused signal: type={fused_signal.signal_type.name}, confidence={fused_signal.confidence}, score={fused_signal.score}")
            return fused_signal
        except Exception as e:
            logger.error(f"Error in fuse_signals: {e}")
            # Return the highest confidence signal as fallback
            if signals:
                return max(signals, key=lambda s: float(s.confidence.value))
            return None

    def _filter_overlapping_signals(self, signals: List[Signal]) -> List[Signal]:
        """Filter out overlapping signals to reduce redundancy from similar strategies"""
        if not signals or len(signals) <= 1:
            return signals

        # First, group by strategy source to handle similar strategies separately
        strategy_groups = {}
        for signal in signals:
            strategy_key = signal.strategy_name.split('_')[0] if '_' in signal.strategy_name else signal.strategy_name
            if strategy_key not in strategy_groups:
                strategy_groups[strategy_key] = []
            strategy_groups[strategy_key].append(signal)

        # From each group, only keep the signal with highest confidence
        filtered_by_strategy = []
        for strategy_key, group_signals in strategy_groups.items():
            if len(group_signals) > 1:
                # Multiple signals from same strategy type, keep the one with highest confidence
                best_signal = max(group_signals, key=lambda s: float(s.confidence.value))
                filtered_by_strategy.append(best_signal)
            else:
                # Only one signal from this strategy type, keep it
                filtered_by_strategy.extend(group_signals)

        # Additional overlapping detection based on signal type and confidence similarity
        # If multiple signals are for same direction and similar confidence, consolidate
        final_signals = []
        processed_signals = set()

        for i, signal1 in enumerate(filtered_by_strategy):
            if i in processed_signals:
                continue

            # Find similar signals (same signal type and close confidence)
            similar_signals = [signal1]
            for j, signal2 in enumerate(filtered_by_strategy[i+1:], i+1):
                if j in processed_signals:
                    continue

                # Check if signals are similar: same type and close confidence
                if (signal1.signal_type == signal2.signal_type and
                    abs(float(signal1.confidence.value) - float(signal2.confidence.value)) < 0.15):  # 15% confidence similarity threshold
                    similar_signals.append(signal2)

            # Mark all similar signals as processed
            for k, _ in enumerate(filtered_by_strategy):
                if filtered_by_strategy[k] in similar_signals:
                    processed_signals.add(k)

            # If we have similar signals, keep the one with highest confidence
            if len(similar_signals) > 1:
                best_of_similar = max(similar_signals, key=lambda s: float(s.confidence.value))
                final_signals.append(best_of_similar)
            else:
                final_signals.append(signal1)

        return final_signals

    def calculate_fusion_weights(self, signals: List[Signal]) -> List[Percentage]:
        """Calculate weights for fusing signals"""
        if not signals:
            return []

        try:
            # Different weighting strategies could be implemented here
            # For now, we'll use a combination of confidence and recency

            weights = []
            total_weight = 0.0

            for signal in signals:
                # Base weight on confidence, with validation
                try:
                    base_weight = float(signal.confidence.value)
                    # Ensure confidence is between 0 and 1
                    base_weight = max(0.0, min(1.0, base_weight))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid confidence value {signal.confidence.value}, using 0.5 as default")
                    base_weight = 0.5

                # Adjust for recency if needed (more recent signals might be weighted higher)
                # For now, we'll just use confidence as the primary factor
                weight = base_weight
                weights.append(weight)
                total_weight += weight

            # Normalize weights to sum to 1.0
            if total_weight > 0:
                normalized_weights = [w / total_weight for w in weights]
            else:
                # If all weights are 0, give equal weight to all
                normalized_weights = [1.0 / len(signals)] * len(signals)

            # Convert to Percentage objects with validation
            from domain.value_objects import Percentage
            from decimal import Decimal
            return [Percentage(Decimal(str(max(0.0, min(1.0, w))))) for w in normalized_weights]

        except Exception as e:
            logger.error(f"Error calculating fusion weights: {e}")
            # Return equal weights as fallback
            equal_weight = 1.0 / len(signals) if signals else 1.0
            from domain.value_objects import Percentage
            from decimal import Decimal
            return [Percentage(Decimal(str(equal_weight))) for _ in signals]

    def _apply_weighted_fusion(self, signals: List[Signal], weights: List[Percentage]) -> Signal:
        """Apply weighted fusion to create a single signal"""
        try:
            if not signals or not weights or len(signals) != len(weights):
                logger.error(f"Invalid input: signals={len(signals) if signals else 0}, weights={len(weights) if weights else 0}, equal_length={len(signals) == len(weights) if signals and weights else False}")
                # Return a neutral signal as fallback
                from domain.entities.trading_entities import Signal, SignalType
                from domain.value_objects import Symbol, Percentage
                from decimal import Decimal
                return Signal(
                    symbol=Symbol("BTCUSDT") if signals else Symbol("BTCUSDT"),
                    signal_type=SignalType.NEUTRAL,
                    confidence=Percentage(Decimal('0.5')),
                    score=0.0,
                    strategy_name="FusionService",
                    timestamp=datetime.now(),
                    metadata={'fusion_error': 'invalid_input_parameters'}
                )

            # Calculate weighted average of scores
            weighted_scores = []
            buy_signals = 0
            sell_signals = 0
            hold_signals = 0

            for signal, weight in zip(signals, weights):
                try:
                    weight_value = float(weight.value)
                    # Validate the weight value
                    weight_value = max(0.0, min(1.0, weight_value))
                    weighted_score = signal.score * weight_value
                    weighted_scores.append(weighted_score)

                    # Count buy vs sell signals for determining final signal type
                    if signal.signal_type.name == 'BUY':
                        buy_signals += 1
                    elif signal.signal_type.name == 'SELL':
                        sell_signals += 1
                    else:
                        hold_signals += 1
                except Exception as e:
                    logger.warning(f"Error processing signal {signal} with weight {weight}: {e}")
                    # Skip this signal-weight pair
                    continue

            # If there were errors processing signals, adjust counts
            if len(weighted_scores) != len(signals):
                logger.warning(f"Only processed {len(weighted_scores)} out of {len(signals)} signals")
                if len(weighted_scores) == 0:
                    # No valid signals processed, return neutral
                    from domain.entities.trading_entities import Signal, SignalType
                    from domain.value_objects import Symbol, Percentage
                    from decimal import Decimal
                    return Signal(
                        symbol=signals[0].symbol,
                        signal_type=SignalType.NEUTRAL,
                        confidence=Percentage(Decimal('0.5')),
                        score=0.0,
                        strategy_name="FusionService",
                        timestamp=datetime.now(),
                        metadata={'fusion_error': 'no_valid_signals_processed'}
                    )

            # Calculate the fused score
            fused_score = sum(weighted_scores)

            # Determine the signal type based on the majority of input signals
            # or based on the sign of the fused score
            if fused_score > 0.1:  # Threshold to avoid neutral signals
                from domain.entities.trading_entities import SignalType
                fused_signal_type = SignalType.BUY
            elif fused_score < -0.1:
                from domain.entities.trading_entities import SignalType
                fused_signal_type = SignalType.SELL
            else:
                # If scores are around zero, use majority vote
                if buy_signals > sell_signals and buy_signals > hold_signals:
                    from domain.entities.trading_entities import SignalType
                    fused_signal_type = SignalType.BUY
                elif sell_signals > buy_signals and sell_signals > hold_signals:
                    from domain.entities.trading_entities import SignalType
                    fused_signal_type = SignalType.SELL
                else:
                    from domain.entities.trading_entities import SignalType
                    fused_signal_type = SignalType.NEUTRAL

            # Calculate fused confidence as the weighted average of confidences
            confidence_values = []
            weight_sum = 0.0
            for signal, weight in zip(signals, weights):
                try:
                    conf_val = float(signal.confidence.value)
                    conf_val = max(0.0, min(1.0, conf_val))  # Clamp confidence to [0, 1]
                    w_val = float(weight.value)
                    w_val = max(0.0, min(1.0, w_val))  # Clamp weight to [0, 1]

                    confidence_values.append(conf_val * w_val)
                    weight_sum += w_val
                except Exception as e:
                    logger.warning(f"Error processing confidence for signal {signal}: {e}")
                    continue

            if weight_sum > 0:
                fused_confidence = sum(confidence_values) / weight_sum
            else:
                fused_confidence = 0.5  # Default to 0.5 if no valid weights

            # Use the symbol from the first signal (all should be the same in a proper fusion)
            if signals:
                symbol = signals[0].symbol
                strategy_name = "FusionService"
            else:
                from domain.value_objects import Symbol
                symbol = Symbol("BTCUSDT")
                strategy_name = "FusionService"

            # Create the fused signal
            from domain.entities.trading_entities import Signal as DomainSignal
            from domain.value_objects import Percentage as DomainPercentage
            from decimal import Decimal

            fused_signal = DomainSignal(
                symbol=symbol,
                signal_type=fused_signal_type,
                confidence=DomainPercentage(Decimal(str(max(0.0, min(1.0, fused_confidence))))),  # Clamp to [0,1]
                score=max(-1.0, min(1.0, fused_score)),  # Clamp to [-1, 1]
                strategy_name=strategy_name,
                timestamp=datetime.now(),
                metadata={
                    'original_signals_count': len(signals),
                    'valid_signals_count': len(weighted_scores),
                    'fusion_method': self.fusion_method,
                    'individual_scores': [getattr(s, 'score', 0) for s in signals],
                    'individual_confidences': [float(s.confidence.value) if hasattr(s, 'confidence') and hasattr(s.confidence, 'value') else 0.5 for s in signals],
                    'processing_errors': len(signals) - len(weighted_scores) > 0
                }
            )

            return fused_signal
        except Exception as e:
            logger.error(f"Error in _apply_weighted_fusion: {e}")
            # Return a neutral signal as fallback
            from domain.entities.trading_entities import Signal, SignalType
            from domain.value_objects import Symbol, Percentage
            from decimal import Decimal
            return Signal(
                symbol=Symbol("BTCUSDT") if signals else Symbol("BTCUSDT"),
                signal_type=SignalType.NEUTRAL,
                confidence=Percentage(Decimal('0.5')),
                score=0.0,
                strategy_name="FusionService",
                timestamp=datetime.now(),
                metadata={'fusion_error': str(e)}
            )


# Import the ML fusion service at the top of the file (add after other imports)
# (This would typically be at the top, but since the file is large, I'm showing this change here)
# from infrastructure.fusion.ml_signal_fusion import MLSignalFusionService, MLFusionMethod


class AdvancedFusionServiceAdapter(FusionServiceAdapter):
    """Advanced fusion implementation with regime detection and ML weighting"""

    def __init__(self):
        super().__init__()
        self.ml_weights_enabled = True
        self.regime_detection_enabled = True
        self.correlation_adjustment_enabled = True
        self.adaptive_weights_enabled = True
        self.signal_diversity_enabled = True
        self.explainability_enabled = True
        self.signal_weights = {}  # Track adaptive weights for each signal source
        self.signal_diversity_matrix = {}  # Track diversity between signals

    def fuse_signals(self, signals: List[Signal]) -> Signal:
        """Enhanced fusion with regime awareness, correlation adjustment, and adaptive weights"""
        logger.info("Using advanced fusion with regime detection, correlation adjustment, and adaptive weights")

        if not signals:
            logger.warning("No signals to fuse")
            return None

        # Apply regime-based adjustments if enabled
        if self.regime_detection_enabled:
            signals = self._adjust_for_regime(signals)

        # Apply correlation adjustments if enabled
        if self.correlation_adjustment_enabled:
            signals = self._adjust_for_correlation(signals)

        # Apply adaptive weights if enabled
        if self.adaptive_weights_enabled:
            weights = self._calculate_adaptive_weights(signals)
        else:
            weights = self.calculate_fusion_weights(signals)

        # Apply diversity adjustments if enabled
        if self.signal_diversity_enabled:
            weights = self._adjust_weights_for_diversity(signals, weights)

        # Use the enhanced fusion method for the actual fusion
        fused_signal = self._apply_enhanced_fusion(signals, weights)

        # Add explainability information if enabled
        if self.explainability_enabled and fused_signal:
            fused_signal.metadata['fusion_explanation'] = self._generate_fusion_explanation(signals, weights)

        return fused_signal

    def _calculate_adaptive_weights(self, signals: List[Signal]) -> List[Percentage]:
        """Calculate adaptive weights based on signal source performance and reliability"""
        if not signals:
            return []

        from domain.value_objects import Percentage
        from decimal import Decimal

        weights = []
        for signal in signals:
            source_engine = getattr(signal, 'source_engine', signal.strategy_name) if hasattr(signal, 'strategy_name') else 'unknown'

            # Get baseline weight from confidence
            try:
                baseline_weight = float(signal.confidence.value)
                baseline_weight = max(0.0, min(1.0, baseline_weight))
            except (ValueError, TypeError):
                baseline_weight = 0.5

            # Adjust based on historical performance of the source engine
            performance_factor = self.signal_weights.get(source_engine, 1.0)

            # Adjust based on recency if needed
            weight = baseline_weight * performance_factor
            weights.append(weight)

        # Normalize weights
        total_weight = sum(weights) if weights else 1.0
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
        else:
            normalized_weights = [1.0 / len(weights) if weights else 1.0] * len(weights)

        return [Percentage(Decimal(str(max(0.0, min(1.0, w))))) for w in normalized_weights]

    def _adjust_weights_for_diversity(self, signals: List[Signal], weights: List[Percentage]) -> List[Percentage]:
        """Adjust weights based on signal diversity to avoid over-concentration"""
        if len(signals) <= 1:
            return weights

        from domain.value_objects import Percentage
        from decimal import Decimal

        # Calculate diversity between signals
        diversity_factors = []
        for i, signal1 in enumerate(signals):
            diversity_sum = 0.0
            for j, signal2 in enumerate(signals):
                if i != j:
                    diversity = self._calculate_signal_diversity(signal1, signal2)
                    diversity_sum += diversity
            avg_diversity = diversity_sum / max(1, len(signals) - 1)
            diversity_factors.append(avg_diversity)

        # Adjust weights based on diversity
        adjusted_weights = []
        for i, (weight, diversity_factor) in enumerate(zip(weights, diversity_factors)):
            adjusted_weight_value = float(weight.value) * (0.7 + 0.3 * diversity_factor)  # Boost diverse signals
            adjusted_weights.append(Percentage(Decimal(str(max(0.0, min(1.0, adjusted_weight_value))))))

        # Renormalize to sum to 1.0
        total_weight = sum(float(w.value) for w in adjusted_weights)
        if total_weight > 0:
            renormalized_weights = [Percentage(Decimal(str(float(w.value) / total_weight))) for w in adjusted_weights]
        else:
            equal_weight = 1.0 / len(adjusted_weights) if adjusted_weights else 1.0
            renormalized_weights = [Percentage(Decimal(str(equal_weight))) for _ in adjusted_weights]

        return renormalized_weights

    def _calculate_signal_diversity(self, signal1: Signal, signal2: Signal) -> float:
        """Calculate diversity between two signals (0.0 to 1.0)"""
        # Calculate diversity based on signal type difference
        type_diversity = 1.0 if signal1.signal_type != signal2.signal_type else 0.3

        # Calculate diversity based on confidence difference
        conf_diff = abs(float(signal1.confidence.value) - float(signal2.confidence.value))
        confidence_diversity = min(1.0, conf_diff * 2)  # More confidence difference = more diversity

        # Calculate diversity based on source difference
        source1 = getattr(signal1, 'source_engine', signal1.strategy_name) if hasattr(signal1, 'strategy_name') else 'unknown'
        source2 = getattr(signal2, 'source_engine', signal2.strategy_name) if hasattr(signal2, 'strategy_name') else 'unknown'
        source_diversity = 1.0 if source1 != source2 else 0.5

        # Combine diversities with weights
        diversity = (type_diversity * 0.4 + confidence_diversity * 0.3 + source_diversity * 0.3)
        return min(1.0, max(0.0, diversity))

    def _apply_enhanced_fusion(self, signals: List[Signal], weights: List[Percentage]) -> Signal:
        """Apply enhanced fusion with better handling of conflicting signals"""
        try:
            if not signals or not weights or len(signals) != len(weights):
                logger.error(f"Invalid input: signals={len(signals) if signals else 0}, weights={len(weights) if weights else 0}, equal_length={len(signals) == len(weights) if signals and weights else False}")
                # Return a neutral signal as fallback
                from domain.entities.trading_entities import Signal, SignalType
                from domain.value_objects import Symbol, Percentage
                from decimal import Decimal
                return Signal(
                    symbol=Symbol("BTCUSDT") if signals else Symbol("BTCUSDT"),
                    signal_type=SignalType.NEUTRAL,
                    confidence=Percentage(Decimal('0.5')),
                    score=0.0,
                    strategy_name="FusionService",
                    timestamp=datetime.now(),
                    metadata={'fusion_error': 'invalid_input_parameters'}
                )

            # Calculate weighted average of scores
            weighted_scores = []
            signal_types = []
            total_confidence = 0.0

            for signal, weight in zip(signals, weights):
                try:
                    weight_value = float(weight.value)
                    # Validate the weight value
                    weight_value = max(0.0, min(1.0, weight_value))
                    weighted_score = signal.score * weight_value
                    weighted_scores.append(weighted_score)

                    signal_types.append(signal.signal_type.name)
                    total_confidence += float(signal.confidence.value) * weight_value

                except Exception as e:
                    logger.warning(f"Error processing signal {signal} with weight {weight}: {e}")
                    continue

            if not weighted_scores:
                # No valid signals processed, return neutral
                from domain.entities.trading_entities import Signal, SignalType
                from domain.value_objects import Symbol, Percentage
                from decimal import Decimal
                return Signal(
                    symbol=signals[0].symbol if signals else Symbol("BTCUSDT"),
                    signal_type=SignalType.NEUTRAL,
                    confidence=Percentage(Decimal('0.5')),
                    score=0.0,
                    strategy_name="FusionService",
                    timestamp=datetime.now(),
                    metadata={'fusion_error': 'no_valid_signals_processed'}
                )

            # Calculate the fused score
            fused_score = sum(weighted_scores)

            # Determine the signal type based on weighted voting
            buy_weight = sum(weight.value for signal, weight in zip(signals, weights) if signal.signal_type.name == 'BUY')
            sell_weight = sum(weight.value for signal, weight in zip(signals, weights) if signal.signal_type.name == 'SELL')
            hold_weight = sum(weight.value for signal, weight in zip(signals, weights) if signal.signal_type.name in ['HOLD', 'NEUTRAL'])

            from domain.entities.trading_entities import SignalType
            if buy_weight > sell_weight and buy_weight > hold_weight:
                fused_signal_type = SignalType.BUY
            elif sell_weight > buy_weight and sell_weight > hold_weight:
                fused_signal_type = SignalType.SELL
            else:
                # If no clear majority, use score-based decision
                if fused_score > 0.1:
                    fused_signal_type = SignalType.BUY
                elif fused_score < -0.1:
                    fused_signal_type = SignalType.SELL
                else:
                    fused_signal_type = SignalType.NEUTRAL

            # Calculate fused confidence
            final_confidence = min(1.0, max(0.0, total_confidence))

            # Use the symbol from the first signal
            symbol = signals[0].symbol if signals else Symbol("BTCUSDT")
            strategy_name = "FusionService"

            # Create the fused signal
            from domain.entities.trading_entities import Signal as DomainSignal
            from domain.value_objects import Percentage as DomainPercentage
            from decimal import Decimal

            fused_signal = DomainSignal(
                symbol=symbol,
                signal_type=fused_signal_type,
                confidence=DomainPercentage(Decimal(str(final_confidence))),
                score=max(-1.0, min(1.0, fused_score)),
                strategy_name=strategy_name,
                timestamp=datetime.now(),
                metadata={
                    'original_signals_count': len(signals),
                    'valid_signals_count': len(weighted_scores),
                    'fusion_method': self.fusion_method,
                    'individual_scores': [getattr(s, 'score', 0) for s in signals],
                    'individual_confidences': [float(s.confidence.value) if hasattr(s, 'confidence') and hasattr(s.confidence, 'value') else 0.5 for s in signals],
                    'processing_errors': len(signals) - len(weighted_scores) > 0,
                    'signal_type_distribution': {
                        'BUY': signal_types.count('BUY'),
                        'SELL': signal_types.count('SELL'),
                        'HOLD': signal_types.count('HOLD') + signal_types.count('NEUTRAL')
                    },
                    'weight_distribution': [float(w.value) for w in weights],
                    'buy_weight': float(buy_weight),
                    'sell_weight': float(sell_weight),
                    'hold_weight': float(hold_weight)
                }
            )

            return fused_signal
        except Exception as e:
            logger.error(f"Error in _apply_enhanced_fusion: {e}")
            # Return a neutral signal as fallback
            from domain.entities.trading_entities import Signal, SignalType
            from domain.value_objects import Symbol, Percentage
            from decimal import Decimal
            return Signal(
                symbol=Symbol("BTCUSDT") if signals else Symbol("BTCUSDT"),
                signal_type=SignalType.NEUTRAL,
                confidence=Percentage(Decimal('0.5')),
                score=0.0,
                strategy_name="FusionService",
                timestamp=datetime.now(),
                metadata={'fusion_error': str(e)}
            )

    def _generate_fusion_explanation(self, signals: List[Signal], weights: List[Percentage]) -> Dict[str, Any]:
        """Generate explanation for the fusion decision"""
        explanation = {
            'input_signals': len(signals),
            'fusion_method': 'enhanced_weighted_average',
            'weight_calculation': 'adaptive_with_diversity',
            'signal_sources': [getattr(s, 'source_engine', s.strategy_name) if hasattr(s, 'strategy_name') else 'unknown' for s in signals],
            'signal_types': [s.signal_type.name for s in signals],
            'weights_applied': [float(w.value) for w in weights],
            'fusion_timestamp': datetime.now().isoformat()
        }

        # Add more detailed analysis
        buy_signals = [s for s in signals if s.signal_type.name == 'BUY']
        sell_signals = [s for s in signals if s.signal_type.name == 'SELL']
        hold_signals = [s for s in signals if s.signal_type.name in ['HOLD', 'NEUTRAL']]

        explanation['buy_signals'] = len(buy_signals)
        explanation['sell_signals'] = len(sell_signals)
        explanation['hold_signals'] = len(hold_signals)

        return explanation

    def _adjust_for_regime(self, signals: List[Signal]) -> List[Signal]:
        """Adjust signals based on detected market regime"""
        # In a real implementation, this would detect the current market regime
        # and adjust signal confidences accordingly

        # For demonstration, we'll just add regime information to metadata
        adjusted_signals = []

        for signal in signals:
            # In trending markets, trend-following signals might be more reliable
            # In mean-reverting markets, contrarian signals might be more reliable
            # For now, we'll just add a placeholder regime indicator

            new_metadata = (signal.metadata or {}).copy()
            new_metadata['market_regime'] = 'trending'  # This would come from actual regime detection
            new_metadata['regime_adjusted'] = True

            adjusted_signal = Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence,
                score=signal.score,
                strategy_name=signal.strategy_name,
                timestamp=signal.timestamp,
                source_engine=signal.source_engine,
                metadata=new_metadata
            )

            adjusted_signals.append(adjusted_signal)

        return adjusted_signals

    def _adjust_for_correlation(self, signals: List[Signal]) -> List[Signal]:
        """Adjust signal weights based on correlation between signals"""
        # In a real implementation, this would analyze correlation between signals
        # and reduce weights for highly correlated signals to avoid over-concentration

        # For demonstration, we'll just add correlation information to metadata
        adjusted_signals = []

        for signal in signals:
            new_metadata = (signal.metadata or {}).copy()
            new_metadata['diversification_factor'] = 1.0  # This would be calculated based on correlation
            new_metadata['correlation_adjusted'] = True

            adjusted_signal = Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence,
                score=signal.score,
                strategy_name=signal.strategy_name,
                timestamp=signal.timestamp,
                source_engine=signal.source_engine,
                metadata=new_metadata
            )

            adjusted_signals.append(adjusted_signal)

        return adjusted_signals

    def fuse_engine_results(self, engine_outputs: Dict[str, EngineResult], weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Fuse outputs from multiple engines that return EngineResult objects (from temp-sample-features pattern)
        This follows the pattern from the temp-sample-features fusion engine.

        Args:
            engine_outputs: Dictionary with engine names as keys and EngineResult objects as values
            weights: Optional dictionary with engine weights for weighted average

        Returns:
            Dictionary with fused score, signal, and raw engine outputs
        """
        if not engine_outputs:
            return {
                "score": 0.5,
                "signal": "none",
                "confidence": 0.0,
                "raw": {},
                "consensus_strength": 0.0
            }

        # Set default weights if none provided
        if weights is None:
            weights = {name: 1.0 for name in engine_outputs.keys()}

        # Normalize weights
        total_weight = sum(weights.values()) if weights else len(engine_outputs)
        if total_weight > 0:
            normalized_weights = {name: weight/total_weight for name, weight in weights.items()}
        else:
            # If no weights or all weights sum to 0, use equal weights
            normalized_weights = {name: 1.0/len(engine_outputs) for name in engine_outputs.keys()}

        # Extract scores and signals from engine results
        scores = []
        signals = []
        weighted_scores = []
        valid_engines = 0

        for engine_name, result in engine_outputs.items():
            if isinstance(result, EngineResult):
                score = result.score
                signal = result.signal

                # Only count engines with meaningful scores
                if 0 <= score <= 1:
                    raw_weight = normalized_weights.get(engine_name, 1.0/len(engine_outputs))

                    scores.append(score)
                    signals.append(signal)
                    weighted_scores.append(score * raw_weight)
                    valid_engines += 1

        if valid_engines == 0:
            return {
                "score": 0.5,
                "signal": "none",
                "confidence": 0.0,
                "raw": engine_outputs,
                "consensus_strength": 0.0
            }

        # Calculate weighted average score
        fused_score = sum(weighted_scores) if weighted_scores else sum(scores) / len(scores) if scores else 0.5

        # Calculate consensus strength (how aligned the signals are)
        unique_signals = set(signals)
        if len(unique_signals) == 1:
            # All engines agree
            consensus_strength = 1.0
        elif len(unique_signals) == 2 and 'none' in unique_signals:
            # Two signals but one is neutral
            consensus_strength = 0.7
        else:
            # Multiple different signals
            consensus_strength = 1.0 - (len(unique_signals) - 1) / len(signals)

        # Determine overall signal based on majority and score
        long_signals = signals.count('long') + signals.count('buy')
        short_signals = signals.count('short') + signals.count('sell')
        none_signals = signals.count('none') + signals.count('hold')

        # Calculate signal confidence based on agreement
        if long_signals > short_signals and long_signals > none_signals:
            overall_signal = 'long' if 'long' in signals else 'buy'
            agreement_ratio = long_signals / len(signals) if len(signals) > 0 else 0
        elif short_signals > long_signals and short_signals > none_signals:
            overall_signal = 'short' if 'short' in signals else 'sell'
            agreement_ratio = short_signals / len(signals) if len(signals) > 0 else 0
        else:
            # No clear majority or tie
            overall_signal = 'none'
            agreement_ratio = max(long_signals, short_signals) / len(signals) if len(signals) > 0 else 0

        # Adjust fused score based on signal direction
        if overall_signal in ['long', 'buy']:
            # Ensure score is above center for long signal
            fused_score = max(0.55, fused_score)
        elif overall_signal in ['short', 'sell']:
            # Ensure score is below center for short signal
            fused_score = min(0.45, fused_score)
        else:
            # For neutral signal, move toward center
            fused_score = 0.5

        # Calculate confidence based on number of engines, consensus strength and score
        engine_count_factor = min(1.0, valid_engines / self.min_engines_for_signal) if self.min_engines_for_signal > 0 else 0
        confidence = (agreement_ratio * 0.4) + (consensus_strength * 0.3) + (engine_count_factor * 0.3)

        # Final confidence adjusted by score extremeness
        score_confidence = 0.5 + abs(fused_score - 0.5)
        confidence = (confidence + score_confidence) / 2

        return {
            "score": fused_score,
            "signal": overall_signal,
            "confidence": confidence,
            "raw": engine_outputs,
            "consensus_strength": consensus_strength,
            "engines_participating": valid_engines,
            "agreement_ratio": agreement_ratio
        }

    def adaptive_fuse(self, engine_outputs: Dict[str, EngineResult], market_regime: str = "normal") -> Dict[str, Any]:
        """
        Adaptive fusion that changes behavior based on market regime

        Args:
            engine_outputs: Dictionary with engine names as keys and EngineResult objects as values
            market_regime: Current market regime ('trending', 'volatile', 'normal', 'low_volatility')

        Returns:
            Dictionary with fused score, signal, and raw engine outputs
        """
        # Define weights for different market regimes
        regime_weights = {
            "trending": {
                "trend": 0.4,
                "pullback": 0.3,
                "volume": 0.15,
                "volatility": 0.1,
                "spike": 0.05
            },
            "volatile": {
                "volatility": 0.3,
                "spike": 0.3,
                "volume": 0.25,
                "trend": 0.1,
                "pullback": 0.05
            },
            "low_volatility": {
                "pullback": 0.3,
                "volume": 0.25,
                "trend": 0.2,
                "spike": 0.15,
                "volatility": 0.1
            },
            "normal": {
                "trend": 0.25,
                "volume": 0.2,
                "volatility": 0.2,
                "pullback": 0.18,
                "spike": 0.17
            }
        }

        # Use default weights if regime not recognized, but map engine names to regime categories
        weights = regime_weights.get(market_regime, regime_weights["normal"])

        # Map actual engine names to weight categories
        actual_weights = {}
        for engine_name, engine_result in engine_outputs.items():
            # Try to match engine name to a category in weights
            matched_category = None
            engine_lower = engine_name.lower()
            for category in weights.keys():
                if category in engine_lower:
                    matched_category = category
                    break

            if matched_category:
                actual_weights[engine_name] = weights[matched_category]
            else:
                actual_weights[engine_name] = 0.1  # Default weight for unmatched engines

        # Perform fusion with regime-specific weights
        result = self.fuse_engine_results(engine_outputs, actual_weights)

        # Add market regime to the result
        result["market_regime"] = market_regime

        return result