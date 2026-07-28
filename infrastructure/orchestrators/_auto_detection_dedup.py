"""E5.T4 (infra-only mechanical split): duplicate-prevention / pending-intent
tracking methods extracted from ``AutoDetectionOrchestrator``.

Behavior-preserving mixin — methods moved verbatim (signatures, ``self`` semantics,
broker-dedup behavior unchanged) and composed back via inheritance. No layer move,
no port inversion, no logic change.
"""
from datetime import datetime


class _AutoDetectionDedupMixin:
    """Pending-intent dedup + broker active-order conflict checks (no order placement)."""

    def _check_duplicate_execution_intent(self, execution_intent) -> bool:
        """Check if an execution intent is a duplicate based on symbol."""
        # Check if duplicate prevention is enabled
        prevent_same_direction = self._settings.execution.prevent_same_direction_trade_per_symbol if self._settings.execution and hasattr(self._settings.execution, 'prevent_same_direction_trade_per_symbol') else True

        if not prevent_same_direction:
            return False  # No duplicate prevention needed

        symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
        direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)

        with self._pending_intents_lock:
            # Check the shared tracker used by execution services to ensure consistency
            from domain.value_objects import Symbol
            symbol_obj = Symbol(symbol)
            
            # Check if there are any pending orders for this symbol (either direction) to prevent conflicts
            pending_orders = self._pending_orders_tracker.get_pending_orders_for_symbol(symbol_obj)
            if pending_orders:
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                self.logger.info(f"❌ DUPLICATE REJECTED: Pending order already exists in shared tracker for {symbol}. Preventing conflicting {direction} intent. | Intent Confidence: {confidence:.2%}")
                return True  # Duplicate/conflict found in shared tracker

            # Add this intent to the orchestrator's internal tracking only
            if symbol not in self._pending_intents:
                self._pending_intents[symbol] = {}
            self._pending_intents[symbol][direction] = datetime.now()

            # Store a reference to the execution intent for later removal
            self._pending_intent_temp_ids[id(execution_intent)] = None  # No shared tracker ID yet

        return False  # Not a duplicate

    def _check_broker_active_orders_for_duplicate(self, execution_intent) -> bool:
        """Check if there are active orders on the broker that would conflict with this execution intent."""
        # Check if duplicate prevention is enabled
        prevent_same_direction = self._settings.execution.prevent_same_direction_trade_per_symbol if self._settings.execution and hasattr(self._settings.execution, 'prevent_same_direction_trade_per_symbol') else True

        if not prevent_same_direction:
            return True  # No duplicate prevention needed, allow the intent

        symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
        direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)

        try:
            # Check if the execution service has access to broker methods
            if hasattr(self.execution_service, 'broker'):
                if hasattr(self.execution_service.broker, 'get_open_orders'):
                    try:
                        # Get open orders for this symbol
                        open_orders = self.execution_service.broker.get_open_orders(symbol)
                        if open_orders:
                            confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                            self.logger.info(f"❌ DUPLICATE REJECTED: Active order already exists on broker for {symbol}. Preventing conflicting {direction} intent. | Intent Confidence: {confidence:.2%}")
                            return False  # Open order exists, prevent this conflicting intent
                    except Exception as e:
                        self.logger.warning(f"⚠️ Could not check open orders on broker for {symbol}: {e}. Continuing with execution attempt.")
                else:
                    if hasattr(self.execution_service, 'get_open_orders'):
                        try:
                            # Get open orders for this symbol
                            open_orders = self.execution_service.get_open_orders(symbol)
                            if open_orders:
                                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                                self.logger.info(f"❌ DUPLICATE REJECTED: Active order already exists on broker for {symbol}. Preventing conflicting {direction} intent. | Intent Confidence: {confidence:.2%}")
                                return False  # Open order exists, prevent this conflicting intent
                        except Exception as e:
                            self.logger.warning(f"⚠️ Could not check open orders on broker for {symbol}: {e}. Continuing with execution attempt.")

            return True

        except Exception as e:
            self.logger.error(f"Error checking broker active orders for duplicate: {e}")
            # In case of error, we'll allow the intent to proceed to avoid blocking the system
            return True

    def _remove_pending_execution_intent(self, execution_intent):
        """Remove an execution intent from the pending tracking."""
        symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
        direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)

        with self._pending_intents_lock:
            if symbol in self._pending_intents and direction in self._pending_intents[symbol]:
                del self._pending_intents[symbol][direction]
                # Clean up empty symbol entries
                if not self._pending_intents[symbol]:
                    del self._pending_intents[symbol]

            # Also remove from shared tracker if we had added one
            from domain.value_objects import Symbol
            symbol_obj = Symbol(symbol)
            # Use the stored temp order ID
            execution_intent_id = id(execution_intent)
            if execution_intent_id in self._pending_intent_temp_ids:
                temp_order_id = self._pending_intent_temp_ids[execution_intent_id]
                if temp_order_id is not None:  # Only remove from shared tracker if we actually added one
                    self._pending_orders_tracker.remove_pending_order(symbol_obj, temp_order_id)
                # Clean up the stored temp ID
                del self._pending_intent_temp_ids[execution_intent_id]
