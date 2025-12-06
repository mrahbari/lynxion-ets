"""
Infrastructure implementation of the fusion service with enhanced capabilities.
"""
from typing import List, Optional, Dict, Any
from domain.entities.trading_entities import Signal
from domain.entities.engine_entities import EngineResult
from domain.value_objects import Symbol, Percentage
from domain.ports.strategy_ports import FusionPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import statistics
import numpy as np


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
        if not signals:
            logger.warning("No signals to fuse")
            return None

        if len(signals) < self.min_signals_for_fusion:
            logger.info(f"Insufficient signals for fusion ({len(signals)} < {self.min_signals_for_fusion}), returning first signal")
            # If not enough signals, return the most confident one
            return max(signals, key=lambda s: float(s.confidence.value))

        logger.info(f"Fusing {len(signals)} signals using {self.fusion_method}")

        # Calculate fusion weights
        weights = self.calculate_fusion_weights(signals)

        # Apply fusion using weighted average
        fused_signal = self._apply_weighted_fusion(signals, weights)

        logger.info(f"Fused signal: type={fused_signal.signal_type.name}, confidence={fused_signal.confidence}, score={fused_signal.score}")
        return fused_signal

    def calculate_fusion_weights(self, signals: List[Signal]) -> List[Percentage]:
        """Calculate weights for fusing signals"""
        if not signals:
            return []

        # Different weighting strategies could be implemented here
        # For now, we'll use a combination of confidence and recency

        weights = []
        total_weight = 0.0

        for signal in signals:
            # Base weight on confidence
            base_weight = float(signal.confidence.value)

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

        # Convert to Percentage objects
        from domain.value_objects import Percentage
        from decimal import Decimal
        return [Percentage(Decimal(str(w))) for w in normalized_weights]

    def _apply_weighted_fusion(self, signals: List[Signal], weights: List[Percentage]) -> Signal:
        """Apply weighted fusion to create a single signal"""
        if not signals or not weights or len(signals) != len(weights):
            raise ValueError("Signals and weights must be non-empty and of equal length")

        # Calculate weighted average of scores
        weighted_scores = []
        total_signal_confidence = 0.0
        buy_signals = 0
        sell_signals = 0

        for signal, weight in zip(signals, weights):
            weighted_score = signal.score * float(weight.value)
            weighted_scores.append(weighted_score)

            # Count buy vs sell signals for determining final signal type
            if signal.signal_type.name == 'BUY':
                buy_signals += 1
            elif signal.signal_type.name == 'SELL':
                sell_signals += 1

        # Calculate the fused score
        fused_score = sum(weighted_scores)

        # Determine the signal type based on the majority of input signals
        # or based on the sign of the fused score
        if fused_score > 0.1:  # Threshold to avoid neutral signals
            fused_signal_type = signals[0].signal_type.__class__.BUY  # type: ignore
        elif fused_score < -0.1:
            fused_signal_type = signals[0].signal_type.__class__.SELL  # type: ignore
        else:
            # If scores are around zero, use majority vote
            if buy_signals > sell_signals:
                fused_signal_type = signals[0].signal_type.__class__.BUY  # type: ignore
            elif sell_signals > buy_signals:
                fused_signal_type = signals[0].signal_type.__class__.SELL  # type: ignore
            else:
                fused_signal_type = signals[0].signal_type.__class__.NEUTRAL  # type: ignore

        # Calculate fused confidence as the weighted average of confidences
        confidence_values = [float(signal.confidence.value) for signal in signals]
        weighted_confidences = [conf * float(weight.value) for conf, weight in zip(confidence_values, weights)]
        fused_confidence = sum(weighted_confidences)

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
                'fusion_method': self.fusion_method,
                'individual_scores': [s.score for s in signals],
                'individual_confidences': [float(s.confidence.value) for s in signals]
            }
        )

        return fused_signal


class AdvancedFusionServiceAdapter(FusionServiceAdapter):
    """Advanced fusion implementation with regime detection and ML weighting"""

    def __init__(self):
        super().__init__()
        self.ml_weights_enabled = True
        self.regime_detection_enabled = True
        self.correlation_adjustment_enabled = True

    def fuse_signals(self, signals: List[Signal]) -> Signal:
        """Enhanced fusion with regime awareness and correlation adjustment"""
        logger.info("Using advanced fusion with regime detection")

        # Apply regime-based adjustments if enabled
        if self.regime_detection_enabled:
            signals = self._adjust_for_regime(signals)

        # Apply correlation adjustments if enabled
        if self.correlation_adjustment_enabled:
            signals = self._adjust_for_correlation(signals)

        # Use the parent fusion method for the actual fusion
        return super().fuse_signals(signals)

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