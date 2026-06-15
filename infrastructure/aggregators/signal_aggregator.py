"""
Signal Aggregator for collecting and comparing fused signals across all symbols.
This component collects signals from all symbols over a time period and selects
the best opportunities based on multiple factors.
"""
import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from domain.entities import FusedSignal, ExecutionIntent
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from infrastructure.messaging.event_system import event_router, EventType, SignalEvent
from infrastructure.strategies.strategy_manager import strategy_manager
from infrastructure.services.broker_execution_service import BrokerExecutionService


class SignalAggregator:
    """
    Aggregates fused signals from all symbols and selects the best opportunities
    based on comprehensive evaluation criteria.
    """

    def __init__(self, aggregation_window_seconds: int = 1, max_signals_to_evaluate: int = 1):  # Reduced aggregation window to 1 second
        self.aggregation_window_seconds = aggregation_window_seconds
        self.max_signals_to_evaluate = max_signals_to_evaluate
        self.logger = EnhancedLogger("SignalAggregator")

        # Storage for collected signals
        self.collected_signals: List[FusedSignal] = []
        self.signal_collection_lock = threading.Lock()

        # Time of last aggregation
        self.last_aggregation_time = datetime.now()

        # Execution service for placing orders
        self.execution_service = None

        # Start the aggregation thread
        self.is_running = False
        self.aggregation_thread = None

        # Subscribe to fused signals
        event_router.subscribe(EventType.FUSED_SIGNAL, self._collect_fused_signal)

    def set_execution_service(self, execution_service):
        """Set the execution service for placing orders."""
        self.execution_service = execution_service

    def _collect_fused_signal(self, event: SignalEvent):
        """Collect fused signals from the event system."""
        try:
            fused_signal = event.data
            with self.signal_collection_lock:
                # Add signal to collection
                self.collected_signals.append(fused_signal)

                # Log the collected signal
                self.logger.debug(f"📥 Collected fused signal for {fused_signal.symbol.value} "
                                f"with confidence {float(fused_signal.confidence.value):.2%} "
                                f"and dominance {fused_signal.dominance_score:.2f}")

                # Check if we should trigger aggregation now
                current_time = datetime.now()
                time_since_last = (current_time - self.last_aggregation_time).total_seconds()

                # Trigger aggregation if we have enough signals or enough time has passed
                # With max_signals_to_evaluate=1, this should trigger immediately after 1 signal
                should_trigger = (len(self.collected_signals) >= self.max_signals_to_evaluate or
                                 time_since_last >= self.aggregation_window_seconds)

                # Add debugging information
                self.logger.debug(f"SignalAggregator Trigger Check: {len(self.collected_signals)}/{self.max_signals_to_evaluate} signals, {time_since_last:.2f}/{self.aggregation_window_seconds}s elapsed, should_trigger={should_trigger}")

                if should_trigger:
                    self.logger.info(f"🔄 Triggering aggregation: {len(self.collected_signals)} signals collected, {time_since_last:.2f}s since last aggregation")
                    # Call aggregation in a separate thread to avoid blocking the event processing
                    aggregation_thread = threading.Thread(target=self._perform_aggregation, daemon=True)
                    aggregation_thread.start()
                else:
                    self.logger.debug(f"⏳ Not triggering aggregation yet: {len(self.collected_signals)}/{self.max_signals_to_evaluate} signals, {time_since_last:.2f}/{self.aggregation_window_seconds}s")

        except Exception as e:
            self.logger.error(f"Error collecting fused signal: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _perform_aggregation(self):
        """Perform aggregation and evaluation of collected signals."""
        self.logger.debug(f"🔍 Starting _perform_aggregation method...")

        with self.signal_collection_lock:
            # Get a copy of the signals to evaluate
            signals_to_evaluate = self.collected_signals.copy()
            self.logger.debug(f"🔍 Inside lock: signals_to_evaluate has {len(signals_to_evaluate)} signals, collected_signals has {len(self.collected_signals)} signals")

            self.collected_signals.clear()  # Clear the collection
            self.last_aggregation_time = datetime.now()

            self.logger.debug(f"🔍 After clearing: signals_to_evaluate has {len(signals_to_evaluate)} signals, collected_signals has {len(self.collected_signals)} signals")

        if not signals_to_evaluate:
            self.logger.debug("🔍 No signals to evaluate, returning early")
            return  # Nothing to evaluate

        self.logger.info(f"🔄 Aggregating and evaluating {len(signals_to_evaluate)} signals")

        # Evaluate all signals and rank them
        ranked_signals = self._rank_signals(signals_to_evaluate)

        # Select the best signals based on our criteria
        selected_signals = self._select_best_signals(ranked_signals)

        self.logger.info(f"✅ Selected {len(selected_signals)} signals for execution intent generation out of {len(signals_to_evaluate)} evaluated")

        # Generate execution intents for selected signals
        for fused_signal in selected_signals:
            self.logger.info(f"🎯 Attempting to generate execution intent for {fused_signal.symbol.value} with confidence {float(fused_signal.confidence.value):.2%}")
            self._generate_execution_intent(fused_signal)

        # Log that aggregation is complete
        self.logger.info(f"✅ Aggregation complete: Processed {len(selected_signals)} signals for execution intent generation")

    def _rank_signals(self, signals: List[FusedSignal]) -> List[Dict[str, Any]]:
        """Rank signals based on multiple criteria."""
        self.logger.debug(f"📊 Ranking {len(signals)} signals...")
        ranked_signals = []

        for signal in signals:
            try:
                # Calculate a composite score based on multiple factors
                confidence = float(signal.confidence.value) if hasattr(signal.confidence, 'value') else 0.5
                dominance = signal.dominance_score if signal.dominance_score else 0.5
                regime_factor = self._get_regime_factor(signal.regime_context)

                # Additional factors could include:
                # - Portfolio balance (avoid over-concentration in one symbol)
                # - Recent performance of this symbol
                # - Market conditions
                # - Risk-adjusted returns

                # Calculate composite score
                composite_score = (
                    0.4 * confidence +           # 40% weight to confidence
                    0.3 * dominance +            # 30% weight to dominance
                    0.2 * regime_factor +        # 20% weight to regime factor
                    0.1 * self._get_diversification_factor(signal.symbol)  # 10% to diversification
                )

                ranked_signals.append({
                    'signal': signal,
                    'score': composite_score,
                    'confidence': confidence,
                    'dominance': dominance,
                    'regime_factor': regime_factor
                })

            except Exception as e:
                self.logger.error(f"Error ranking signal for {signal.symbol.value}: {e}")
                continue

        # Sort by composite score (highest first)
        ranked_signals.sort(key=lambda x: x['score'], reverse=True)

        # Log the ranking
        self.logger.debug(f"📊 Signal ranking:")
        for i, ranked in enumerate(ranked_signals[:5]):  # Log top 5
            signal = ranked['signal']
            self.logger.debug(f"  {i+1}. {signal.symbol.value}: "
                            f"Score={ranked['score']:.3f}, "
                            f"Conf={ranked['confidence']:.2%}, "
                            f"Dominance={ranked['dominance']:.2f}")

        return ranked_signals

    def _get_regime_factor(self, regime_context: str) -> float:
        """Get a factor based on market regime context."""
        # Different regimes might have different effectiveness
        regime_weights = {
            'trending': 1.0,
            'volatile': 0.8,
            'sideways': 0.7,
            'normal': 0.9,
            'high_volatility': 0.85,
            'low_volatility': 0.75
        }
        return regime_weights.get(regime_context, 0.8)  # Default to 0.8

    def _get_diversification_factor(self, symbol: Symbol) -> float:
        """Get a factor based on portfolio diversification needs."""
        # This would ideally check current portfolio allocation
        # For now, we'll use a simple approach to encourage diversification
        # If this symbol has been traded frequently recently, reduce its score
        # In a real implementation, this would connect to portfolio tracking
        return 1.0  # Default to 1.0, could be adjusted based on portfolio data

    def _select_best_signals(self, ranked_signals: List[Dict[str, Any]]) -> List[FusedSignal]:
        """Select the best signals based on diversification and other criteria."""
        selected_signals = []

        # For now, select top N signals, ensuring diversification
        # In a more sophisticated implementation, we might:
        # - Limit exposure to any single symbol
        # - Consider correlation between selected symbols
        # - Apply risk management constraints

        max_selections = min(3, len(ranked_signals))  # Select top 3 at most

        # Track selected symbols to avoid over-concentration
        selected_symbols = set()

        for ranked in ranked_signals:
            signal = ranked['signal']
            symbol_str = signal.symbol.value

            # Skip if we already have a signal for this symbol
            # (to encourage diversification)
            if symbol_str in selected_symbols:
                continue

            selected_signals.append(signal)
            selected_symbols.add(symbol_str)

            if len(selected_signals) >= max_selections:
                break

        self.logger.info(f"✅ Selected {len(selected_signals)} signals for execution out of {len(ranked_signals)} evaluated")

        return selected_signals

    def _generate_execution_intent(self, fused_signal: FusedSignal):
        """Generate execution intent for a selected fused signal."""
        try:
            self.logger.debug(f"🎯 Attempting to generate execution intent for {fused_signal.symbol.value}")

            # Use the strategy manager to evaluate the fused signal
            execution_intent = strategy_manager.evaluate_fused_signal(fused_signal)

            if execution_intent:
                self.logger.info(f"🎯 Generated execution intent for {execution_intent.symbol.value} "
                               f"({execution_intent.side.name}) with confidence {float(execution_intent.intent_confidence.value):.2%}")

                # Log the decision to generate execution intent
                self.logger.log_decision_reason(
                    component="SignalAggregator",
                    symbol=execution_intent.symbol.value,
                    decision="Execution Intent Generated",
                    reason=f"Signal passed strategy evaluation with confidence {float(execution_intent.intent_confidence.value):.2%}",
                    confidence=float(execution_intent.intent_confidence.value),
                    details={
                        'strategy': execution_intent.strategy_name,
                        'side': execution_intent.side.name,
                        'regime_context': getattr(fused_signal, 'regime_context', 'unknown'),
                        'dominant_bias': fused_signal.dominant_bias.value,
                        'dominance_score': fused_signal.dominance_score
                    }
                )

                # Publish the execution intent to the event system
                event_router.publish_execution_intent(
                    execution_intent,
                    source="SignalAggregator",
                    correlation_id=f"agg_{fused_signal.symbol.value}_{datetime.now().timestamp()}"
                )

                self.logger.info(f"📤 Published execution intent for {execution_intent.symbol.value} "
                               f"({execution_intent.side.name}) to event system")
            else:
                self.logger.debug(f"⚠️ No execution intent generated for {fused_signal.symbol.value}")

                # Log why no execution intent was generated
                confidence = float(fused_signal.confidence.value)
                self.logger.log_decision_reason(
                    component="SignalAggregator",
                    symbol=fused_signal.symbol.value,
                    decision="Execution Intent Rejected",
                    reason=f"Signal did not meet strategy criteria with confidence {confidence:.2%}",
                    confidence=confidence,
                    details={
                        'regime_context': getattr(fused_signal, 'regime_context', 'unknown'),
                        'dominant_bias': fused_signal.dominant_bias.value,
                        'dominance_score': fused_signal.dominance_score
                    }
                )

        except Exception as e:
            self.logger.error(f"Error generating execution intent for {fused_signal.symbol.value}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def start_aggregation(self):
        """Start the aggregation process."""
        if not self.is_running:
            self.is_running = True
            self.logger.info(f"🔄 Signal Aggregator started with {self.aggregation_window_seconds}s window")

    def stop_aggregation(self):
        """Stop the aggregation process and process any remaining signals."""
        self.is_running = False

        # Process any remaining signals
        with self.signal_collection_lock:
            if self.collected_signals:
                self.logger.info(f"Processing {len(self.collected_signals)} remaining signals before stopping")
                self._perform_aggregation()

        self.logger.info("🛑 Signal Aggregator stopped")


# Global signal aggregator instance
signal_aggregator = SignalAggregator()