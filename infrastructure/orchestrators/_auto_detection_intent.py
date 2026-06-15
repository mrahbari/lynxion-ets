"""E5.T4 (infra-only mechanical split): execution-intent handling methods extracted
from ``AutoDetectionOrchestrator``.

Behavior-preserving mixin — ``_handle_execution_intent_event`` and
``_check_risk_acceptance_from_intent`` moved verbatim (signatures, ``self`` semantics,
event-handling + risk-gate behavior UNCHANGED) and composed via inheritance. The trade
placement they trigger remains in ``_AutoDetectionExecutionMixin`` (resolved via MRO).
No layer move, no port inversion, no logic change.
"""
import traceback


class _AutoDetectionIntentMixin:
    """Execution-intent event handling + risk-acceptance gate (no order placement)."""

    def _handle_execution_intent_event(self, event):
        """Handle execution intent events from the event system."""
        try:
            execution_intent = event.data
            confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5

            # Calculate opportunity score based on multiple factors
            opportunity_score = self._calculate_opportunity_score(execution_intent)

            self.logger.info(f"📥 RECEIVED EXECUTION INTENT: {execution_intent.symbol.value} | Side: {execution_intent.side.name} | Confidence: {confidence:.2%} | Score: {opportunity_score:.2f} | Strategy: {execution_intent.strategy_name}")

            # Log the decision point with comprehensive details
            self.logger.log_decision_reason(
                component="Orchestrator",
                symbol=execution_intent.symbol.value,
                decision="Intent Processing Started",
                reason=f"Received execution intent from strategy layer",
                confidence=confidence,
                score=opportunity_score,  # Add opportunity score
                details={
                    'strategy': execution_intent.strategy_name,
                    'side': execution_intent.side.name,
                    'regime_context': getattr(execution_intent.fused_signal, 'regime_context', 'unknown') if hasattr(execution_intent, 'fused_signal') else 'unknown',
                    'dominant_bias': getattr(execution_intent.fused_signal, 'dominant_bias', 'unknown').value if hasattr(execution_intent, 'fused_signal') and hasattr(getattr(execution_intent, 'fused_signal', None), 'dominant_bias') else 'unknown',
                    'dominance_score': getattr(execution_intent.fused_signal, 'dominance_score', 0.0) if hasattr(execution_intent, 'fused_signal') else 0.0,
                    'opportunity_score': opportunity_score
                }
            )

            # Check for active orders on the broker before processing the intent
            if not self._check_broker_active_orders_for_duplicate(execution_intent):
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                self.logger.info(f"❌ BROKER DUPLICATE CHECK FAILED: {execution_intent.symbol.value} {execution_intent.side.name} | Intent Confidence: {confidence:.2%}")

                # Log the rejection reason
                self.logger.log_decision_reason(
                    component="Orchestrator",
                    symbol=execution_intent.symbol.value,
                    decision="Intent Rejected - Broker Duplicate",
                    reason="Active order already exists on broker in same direction",
                    confidence=confidence,
                    score=opportunity_score
                )
                return  # Don't add to queue if broker already has active order in same direction

            # Check for duplicate execution intent before adding to queue
            if self._check_duplicate_execution_intent(execution_intent):
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                self.logger.info(f"❌ DUPLICATE INTENT REJECTED: {execution_intent.symbol.value} {execution_intent.side.name} | Intent Confidence: {confidence:.2%}")

                # Log the rejection reason
                self.logger.log_decision_reason(
                    component="Orchestrator",
                    symbol=execution_intent.symbol.value,
                    decision="Intent Rejected - Duplicate Prevention",
                    reason="Duplicate execution intent detected",
                    confidence=confidence,
                    score=opportunity_score
                )
                return  # Don't add duplicate to queue

            # Add some protection against one symbol dominating the queue
            # Count how many opportunities are already in the queue for this symbol
            symbol = execution_intent.symbol.value
            same_symbol_count = sum(1 for item in self.opportunity_queue
                                  if hasattr(item, 'symbol') and item.symbol.value == symbol)

            # Limit the number of opportunities for the same symbol in the queue
            max_same_symbol_in_queue = 10  # Adjust as needed
            if same_symbol_count >= max_same_symbol_in_queue:
                self.logger.warning(f"Queue limit reached for {symbol}, not adding more opportunities for this symbol")

                # Log the rejection reason
                self.logger.log_decision_reason(
                    component="Orchestrator",
                    symbol=execution_intent.symbol.value,
                    decision="Intent Rejected - Queue Limit",
                    reason=f"Queue limit reached for symbol ({max_same_symbol_in_queue} items)",
                    confidence=confidence,
                    score=opportunity_score
                )
                return  # Don't add to queue if too many for same symbol

            # Add the execution intent to the opportunity queue for processing
            self.opportunity_queue.append(execution_intent)

            # Log the successful addition to queue
            queue_size = len(self.opportunity_queue)
            self.logger.info(f"✅ EXECUTION INTENT QUEUED: {execution_intent.symbol.value} | Queue Size: {queue_size} | Confidence: {confidence:.2%} | Score: {opportunity_score:.2f}")

            # Log the receipt of the execution intent
            self.logger.log_decision_reason(
                component="Orchestrator",
                symbol=execution_intent.symbol.value,
                decision="Intent Queued for Execution",
                reason="Execution intent successfully added to processing queue",
                confidence=confidence,
                score=opportunity_score,
                details={
                    'queue_size': queue_size,
                    'strategy': execution_intent.strategy_name,
                    'side': execution_intent.side.name,
                    'opportunity_score': opportunity_score
                }
            )

            self.logger.log_background_activity(
                "Execution Intent Received",
                f"Received execution intent for {execution_intent.symbol.value} from event system",
                symbol=execution_intent.symbol.value,
                strategy=execution_intent.strategy_name,
                confidence=float(execution_intent.intent_confidence.value),
                score=opportunity_score
            )
        except Exception as e:
            self.logger.error(f"Error handling execution intent event: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _check_risk_acceptance_from_intent(self, execution_intent) -> bool:
        """Check if trade should be accepted based on risk parameters."""
        try:
            # Check if the intent's risk parameters are within acceptable limits
            risk_params = execution_intent.risk_parameters
            max_position_size = risk_params.get('max_position_size', 0.02)  # Default 2%
            
            # Check against configured risk limits
            configured_max_risk = self.risk_config.get('max_risk', 0.02)
            
            return max_position_size <= configured_max_risk
        except Exception:
            return False
