"""
Auto-Detection Orchestrator for fully autonomous trading system following correct architecture.
Monitors markets continuously, identifies opportunities, and triggers appropriate strategies.
Following correct architecture: Watcher → Engine → Fusion → Strategy → Broker
"""
import threading
import time
import traceback
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from domain.ports.data_ports import DataProviderPort
from domain.ports.execution_ports import ExecutionPort
from domain.ports.portfolio_ports import PortfolioManagementPort
from domain.ports.optimization_ports import IOptimizationService
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from infrastructure.services.risk_alerts import RiskAlertService
from infrastructure.orchestrators._auto_detection_helpers import _AutoDetectionHelpersMixin
from infrastructure.orchestrators._auto_detection_dedup import _AutoDetectionDedupMixin
from infrastructure.orchestrators._auto_detection_execution import _AutoDetectionExecutionMixin
from infrastructure.orchestrators._auto_detection_intent import _AutoDetectionIntentMixin


class AutoDetectionOrchestrator(_AutoDetectionHelpersMixin, _AutoDetectionDedupMixin, _AutoDetectionExecutionMixin, _AutoDetectionIntentMixin):
    """Orchestrator for fully autonomous trading with auto-detection capability following correct architecture."""

    def __init__(self,
                 settings,
                 market_data_repo: DataProviderPort,
                 execution_service: ExecutionPort,
                 portfolio_service: PortfolioManagementPort,
                 optimization_service: IOptimizationService,
                 symbols: List[str],
                 risk_config: Optional[Dict[str, Any]] = None,
                 comprehensive_logging: bool = True):
        # Settings injected by the composition root (E1.T4); the auto-detection
        # mixins read the same fields off self._settings instead of importing
        # bootstrap.settings.loaders.
        self._settings = settings
        self.market_data_repo = market_data_repo
        self.execution_service = execution_service
        self.portfolio_service = portfolio_service
        self.optimization_service = optimization_service
        self.risk_config = risk_config or {
            "max_risk": 0.02,
            "atr_multiplier": 1.5,
            "use_dynamic_position": True
        }
        self.logger = EnhancedLogger("AutoDetectionOrchestrator", comprehensive_mode=comprehensive_logging)
        self.comprehensive_logging = comprehensive_logging

        # Import new architecture components
        from infrastructure.engines.engine_service import engine_service
        from infrastructure.fusion.fusion_service import fusion_service
        from infrastructure.strategies.strategy_manager import strategy_manager
        from infrastructure.messaging.event_system import event_router, signal_processor

        self.engine_service = engine_service
        self.fusion_service = fusion_service
        self.strategy_manager = strategy_manager
        self.event_router = event_router  # Store the event router as an instance variable

        # Initialize the architecture orchestrator to handle proper flow
        from infrastructure.orchestrators.architecture_orchestrator import architecture_orchestrator
        # Pass the execution service to the architecture orchestrator
        architecture_orchestrator.execution_service = self.execution_service
        architecture_orchestrator.start()

        # Subscribe to execution intent events to handle them in the orchestrator
        from infrastructure.messaging.event_system import EventType
        self.event_router.subscribe(EventType.EXECUTION_INTENT, self._handle_execution_intent_event)

        # Initialize the market opportunity watcher with the event router (no internal flow processing)
        from infrastructure.watchers.market_opportunity_watcher import MarketOpportunityWatcher
        self.opportunity_watcher = MarketOpportunityWatcher(
            settings=self._settings,
            symbols=symbols if symbols else None,
            opportunity_callback=None,  # No callback needed since we're using event-driven flow
            auto_discover_symbols=not bool(symbols),  # Auto-discover if no symbols provided
            comprehensive_logging=comprehensive_logging,
            market_data_repo=market_data_repo,
            event_router=event_router  # Use event router instead of direct services
        )

        # Set symbols from the opportunity watcher (handles auto-discovery)
        self.symbols = self.opportunity_watcher.symbols

        # Initialize risk management
        from infrastructure.services.risk_alerts import RiskAlertService, EmailNotificationService, \
            TelegramNotificationService
        email_service = EmailNotificationService()
        telegram_service = TelegramNotificationService()
        self.risk_alert_service = RiskAlertService(
            notification_services=[email_service, telegram_service],
            max_leverage=10.0,
            drawdown_threshold=-0.1
        )

        # Initialize state
        self.is_running = False
        self.active_trades = {}
        self.opportunity_queue = []
        self.background_threads = []
        self.reconcile_interval_seconds = 60   # R1: periodic broker reconciliation cadence

        # Initialize duplicate prevention tracking
        self._pending_intents_lock = threading.RLock()  # Use RLock for recursive locking if needed
        self._pending_intents = {}  # symbol -> {direction: timestamp}
        self._pending_intent_temp_ids = {}  # execution_intent_id -> temp_order_id

        # Initialize symbol-level locks to prevent concurrent processing of same symbol
        self._symbol_processing_locks = {}  # symbol -> threading.Lock()
        self._symbol_processing_locks_lock = threading.Lock()  # Lock for the locks dictionary itself

        # Initialize opportunity queue lock for thread-safe operations
        self._opportunity_queue_lock = threading.RLock()

        # Also use the shared PendingOrdersTracker for consistency with execution services
        from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
        self._pending_orders_tracker = PendingOrdersTracker

    def initialize_system(self):
        """Initialize the auto-detection system."""
        self.logger.info("🚀 Initializing Auto-Detection Orchestrator with correct architecture...")

        # Start background services
        self._start_background_services()

        self.is_running = True
        self.logger.info("✅ Auto-Detection Orchestrator initialized successfully with correct architecture")

    def _start_background_services(self):
        """Start all background services."""
        # Start market opportunity watcher
        self.opportunity_watcher.start_monitoring()

        # Start opportunity processing thread
        opportunity_thread = threading.Thread(target=self._opportunity_processing_loop, daemon=True)
        opportunity_thread.start()
        self.background_threads.append(("opportunity_processing", opportunity_thread))

        # Start risk monitoring
        risk_thread = threading.Thread(target=self._risk_monitoring_loop, daemon=True)
        risk_thread.start()
        self.background_threads.append(("risk_monitoring", risk_thread))

        # R1: start periodic broker reconciliation (halts on unrecoverable drift)
        recon_thread = threading.Thread(target=self._reconciliation_loop, daemon=True)
        recon_thread.start()
        self.background_threads.append(("broker_reconciliation", recon_thread))

        # Dynamic Trailing Stop & Breakeven Protection Service (5s high-frequency loop)
        pos_mgr_thread = threading.Thread(target=self._active_position_management_loop, daemon=True)
        pos_mgr_thread.start()
        self.background_threads.append(("active_position_management", pos_mgr_thread))

        # Start persistent trade feature collector for ongoing trade analysis & research dataset
        try:
            from infrastructure.execution.trade_feature_collector import trade_feature_collector
            trade_feature_collector.start()
            self.logger.info("📊 Started persistent TradeFeatureCollector background thread")
        except Exception as collector_err:
            self.logger.warning(f"Could not start TradeFeatureCollector: {collector_err}")

        self.logger.info(f"⚙️ Started {len(self.background_threads)} background services")

    def _opportunity_processing_loop(self):
        """Process queued opportunities in a separate thread."""
        self.logger.info("🔄 Opportunity processing loop started")

        # Track statistics for periodic reporting
        last_report_time = time.time()
        report_interval = 60  # seconds between detailed reports
        processed_count = 0
        rejected_count = 0

        # Track recently processed symbols to ensure diversity
        recent_symbols = []  # Track symbols processed in the last few iterations
        max_recent_symbols = 5  # Maximum number of recent symbols to track

        # Track symbol processing statistics to ensure even distribution
        symbol_processing_stats = {}  # symbol -> count of processed opportunities
        last_symbol_processing_reset = time.time()
        symbol_processing_reset_interval = 300  # Reset stats every 5 minutes

        while self.is_running:
            try:
                with self._opportunity_queue_lock:
                    if self.opportunity_queue:
                        # Look for an opportunity that's not from a recently processed symbol
                        opportunity = None
                        opportunity_idx = 0

                        # First, try to find an opportunity from a symbol that hasn't been processed recently
                        # and hasn't been processed as much as others (to ensure even distribution)
                        for idx, queued_opportunity in enumerate(self.opportunity_queue):
                            symbol = getattr(queued_opportunity, 'symbol', None)
                            if symbol:
                                symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)

                                # Check if this symbol hasn't been processed recently
                                not_recent = symbol_str not in recent_symbols

                                # Check if this symbol has been processed less than others (for even distribution)
                                symbol_count = symbol_processing_stats.get(symbol_str, 0)
                                max_processed_count = max(symbol_processing_stats.values()) if symbol_processing_stats else 0
                                below_average = symbol_count < max_processed_count * 0.7  # Allow up to 70% of max

                                # Use this opportunity if it's not recent and below average processing
                                if not_recent and below_average:
                                    opportunity = self.opportunity_queue.pop(idx)
                                    break

                        # If no non-recent symbol found that's below average, try to find any non-recent symbol
                        if opportunity is None:
                            for idx, queued_opportunity in enumerate(self.opportunity_queue):
                                symbol = getattr(queued_opportunity, 'symbol', None)
                                if symbol:
                                    symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)

                                    # If this symbol hasn't been processed recently, use it
                                    if symbol_str not in recent_symbols:
                                        opportunity = self.opportunity_queue.pop(idx)
                                        break

                        # If no non-recent symbol found, try to find a symbol that's been processed less
                        if opportunity is None:
                            # Find the symbol with the lowest processing count
                            min_count = float('inf')
                            min_idx = 0
                            for idx, queued_opportunity in enumerate(self.opportunity_queue):
                                symbol = getattr(queued_opportunity, 'symbol', None)
                                if symbol:
                                    symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
                                    symbol_count = symbol_processing_stats.get(symbol_str, 0)
                                    if symbol_count < min_count:
                                        min_count = symbol_count
                                        min_idx = idx
                                        opportunity = self.opportunity_queue.pop(idx)
                                        break

                        # If still no opportunity found, just take the first one
                        if opportunity is None:
                            opportunity = self.opportunity_queue.pop(0)
                            opportunity_idx = 0

                    # Only process if we found an opportunity
                    if opportunity:
                        # Track which symbol was processed
                        symbol = getattr(opportunity, 'symbol', None)
                        if symbol:
                            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)

                            # Add to recent symbols and maintain the list size
                            recent_symbols.append(symbol_str)
                            if len(recent_symbols) > max_recent_symbols:
                                recent_symbols.pop(0)  # Remove oldest

                            # Update processing statistics
                            symbol_processing_stats[symbol_str] = symbol_processing_stats.get(symbol_str, 0) + 1

                            # Check cooldown gate before processing strategy
                            try:
                                from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
                                allowed, cd_reason = symbol_cooldown_gate.is_symbol_allowed(symbol)
                                if not allowed:
                                    self.logger.debug(f"Skipping opportunity for {symbol_str}: {cd_reason}")
                                    continue
                            except Exception:
                                pass

                            self.logger.debug(f"Processing opportunity for symbol: {symbol_str}, Recent symbols: {recent_symbols}")

                        self._execute_strategy_for_opportunity(opportunity)
                        processed_count += 1
                # End of with self._opportunity_queue_lock block
                # Log when no opportunities are in the queue to show system is still active
                if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                    current_time = time.time()
                    if current_time - last_report_time >= 10:  # Log every 10 seconds if no opportunities
                        # Need to access queue size inside the lock
                        with self._opportunity_queue_lock:
                            queue_size = len(self.opportunity_queue)

                        self.logger.log_background_activity(
                            "Opportunity Monitoring",
                            f"No opportunities in queue, system monitoring {len(self.active_trades)} active trades",
                            queue_size=queue_size,
                            active_trades=len(self.active_trades)
                        )
                        last_report_time = current_time

                # Log periodic detailed reports
                current_time = time.time()
                if current_time - last_report_time >= report_interval:
                    # Reset symbol processing stats periodically to prevent long-term bias
                    if current_time - last_symbol_processing_reset >= symbol_processing_reset_interval:
                        self.logger.info(f"🔄 Resetting symbol processing statistics to ensure even distribution")
                        symbol_processing_stats.clear()
                        last_symbol_processing_reset = current_time

                    # Create a summary of symbol processing distribution
                    symbol_summary = {symbol: count for symbol, count in symbol_processing_stats.items() if count > 0}

                    # Access queue size inside the lock
                    with self._opportunity_queue_lock:
                        queue_size = len(self.opportunity_queue)

                    self.logger.info(f"📈 OPPORTUNITY PROCESSING: Processed: {processed_count} | "
                                     f"Queue size: {queue_size} | "
                                     f"Active trades: {len(self.active_trades)} | "
                                     f"Symbol distribution: {symbol_summary}")
                    processed_count = 0
                    rejected_count = 0
                    last_report_time = current_time

                time.sleep(0.1)  # Check queue more frequently to improve responsiveness
            except Exception as e:
                self.logger.error(f"Error in opportunity processing loop: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                time.sleep(1)

    def _handle_opportunity(self, opportunity: Dict[str, Any]):
        """Handle detected market opportunity - this should receive execution intents from the strategy layer."""
        # Check if this is an execution intent (which comes from the strategy layer after processing)
        execution_intent = opportunity.get('execution_intent') if isinstance(opportunity, dict) else opportunity

        if hasattr(execution_intent, 'symbol'):
            symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
            confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
        else:
            # This might be the old format, handle it appropriately
            symbol = opportunity.get('symbol', 'UNKNOWN')
            confidence = opportunity.get('confidence', 0)

        self.logger.info(
            f"💎 Handling execution intent: {symbol} - Intent: {execution_intent if hasattr(execution_intent, 'side') else 'None'} with confidence {confidence:.2%}")

        # Log the flow from strategy to broker
        if hasattr(execution_intent, 'side'):
            self.logger.log_strategy_to_broker_flow(
                symbol=symbol,
                strategy_name=getattr(execution_intent, 'strategy_name', 'unknown'),
                trade_executed=False,  # We don't know yet
                signal_type=execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side),
                confidence=confidence,
                reason=f"Execution intent received from strategy layer",
            )

        # Log the decision at the orchestrator level
        self.logger.log_decision_reason(
            component="Orchestrator",
            symbol=symbol,
            decision="Execution Intent Queued",
            reason=f"Execution intent received from strategy layer",
            confidence=confidence
        )

        # Track and log symbol distribution statistics
        total_queue_size = len(self.opportunity_queue)
        symbol_in_queue_count = sum(1 for item in self.opportunity_queue
                                  if hasattr(item, 'symbol') and item.symbol.value == symbol)

        # Log symbol distribution for monitoring
        self.logger.debug(f"📊 SYMBOL DISTRIBUTION: {symbol} appears {symbol_in_queue_count}/{total_queue_size} in queue ({symbol_in_queue_count/total_queue_size*100:.1f}% if present) | Total symbols in queue: {len(set(getattr(item, 'symbol', None).value if hasattr(getattr(item, 'symbol', None), 'value') else 'UNKNOWN' for item in self.opportunity_queue if hasattr(item, 'symbol', None))) if self.opportunity_queue else 0}")

        # Check for active orders on the broker before processing the intent
        if hasattr(execution_intent, 'side') and hasattr(execution_intent, 'symbol'):
            if not self._check_broker_active_orders_for_duplicate(execution_intent):
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                self.logger.info(f"Broker active orders check failed for {symbol} {execution_intent.side.name} | Intent Confidence: {confidence:.2%}")
                return  # Don't add to queue if broker already has active order in same direction

        # Check for duplicate execution intent before adding to queue
        if hasattr(execution_intent, 'side') and hasattr(execution_intent, 'symbol'):
            if self._check_duplicate_execution_intent(execution_intent):
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                self.logger.info(f"Duplicate execution intent rejected for {symbol} {execution_intent.side.name} | Intent Confidence: {confidence:.2%}")
                return  # Don't add duplicate to queue

        # Add some protection against one symbol dominating the queue
        # Count how many opportunities are already in the queue for this symbol
        same_symbol_count = sum(1 for item in self.opportunity_queue
                              if hasattr(item, 'symbol') and item.symbol.value == symbol)

        # Limit the number of opportunities for the same symbol in the queue
        max_same_symbol_in_queue = 10  # Adjust as needed
        if same_symbol_count >= max_same_symbol_in_queue:
            self.logger.warning(f"Queue limit reached for {symbol}, not adding more opportunities for this symbol")
            return  # Don't add to queue if too many for same symbol

        # Log background activity in comprehensive mode
        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
            self.logger.log_background_activity(
                "Execution Intent Received",
                f"Received execution intent for {symbol} with confidence {confidence:.2%}",
                symbol=symbol,
                execution_intent=hasattr(execution_intent, 'side'),
                confidence=confidence
            )

        # Add the execution intent directly to the queue instead of the opportunity dict
        with self._opportunity_queue_lock:
            self.opportunity_queue.append(execution_intent)

    def _execute_strategy_for_opportunity(self, execution_intent):
        """Execute the appropriate strategy for an execution intent following correct architecture."""
        try:
            # The parameter should now be an execution intent directly
            if not execution_intent or not hasattr(execution_intent, 'symbol'):
                self.logger.warning(f"Invalid execution intent received: {execution_intent}")
                return

            symbol = execution_intent.symbol
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)

            # Acquire symbol-level lock to prevent concurrent processing of same symbol
            with self._get_symbol_lock(symbol_str):
                strategy_name = getattr(execution_intent, 'strategy_name', 'unknown')
                confidence = float(getattr(execution_intent.intent_confidence, 'value', 0.5))

                self.logger.info(
                    f"🎯 EXECUTING TRADE: {strategy_name} on {symbol.value} | Side: {execution_intent.side.name if hasattr(execution_intent, 'side') and hasattr(execution_intent.side, 'name') else str(execution_intent.side)} | Confidence: {confidence:.2%}")

                # Log the flow from strategy to broker
                self.logger.log_signal_progression(
                    symbol=symbol.value,
                    stage="strategy",
                    status="Ready for Execution",
                    details=f"Execution intent prepared for broker: {execution_intent.side.name if hasattr(execution_intent, 'side') and hasattr(execution_intent.side, 'name') else str(execution_intent.side)}",
                    confidence=confidence
                )

                signal_type = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)
                self.logger.log_strategy_to_broker_flow(
                    symbol=symbol.value,
                    strategy_name=strategy_name,
                    trade_executed=False,  # We don't know yet, so we'll log the execution separately
                    signal_type=signal_type,
                    confidence=confidence,
                    reason=f"Execution intent generated with confidence {confidence:.2%}",
                )

                # Log the decision point with comprehensive details before execution
                self.logger.log_decision_reason(
                    component="Orchestrator",
                    symbol=symbol.value,
                    decision="Trade Execution Attempt",
                    reason=f"Attempting to execute trade based on execution intent from strategy layer",
                    confidence=confidence,
                    details={
                        'strategy': strategy_name,
                        'side': signal_type,
                        'regime_context': getattr(execution_intent.fused_signal, 'regime_context', 'unknown') if hasattr(execution_intent, 'fused_signal') else 'unknown',
                        'dominant_bias': getattr(execution_intent.fused_signal, 'dominant_bias', 'unknown').value if hasattr(execution_intent, 'fused_signal') and hasattr(getattr(execution_intent, 'fused_signal', None), 'dominant_bias') else 'unknown',
                        'dominance_score': getattr(execution_intent.fused_signal, 'dominance_score', 0.0) if hasattr(execution_intent, 'fused_signal') else 0.0,
                        'risk_parameters': execution_intent.risk_parameters if hasattr(execution_intent, 'risk_parameters') else 'N/A'
                    }
                )

                # Execute trade through execution service using the execution intent
                execution_result = self._execute_trade_from_intent(execution_intent)

            # Track active trade with detailed decision data
            trade_details = {
                'strategy': strategy_name,
                'side': signal_type,
                'timestamp': datetime.now().isoformat(),
                'execution_result': execution_result,
                'intent_confidence': confidence,
                'decision_factors': {
                    'intent_quality': confidence,
                    'trade_acceptance_reason': 'Intent strength' if confidence > 0.6 else 'Low confidence - may be rejected',
                    'risk_check_passed': self._check_risk_acceptance_from_intent(execution_intent),
                }
            }

            # Log trade decision with reasons
            if execution_result['status'] == 'executed':
                execution_id = execution_result.get('execution_id', 'N/A')
                self.logger.info(
                    f"✅ TRADE EXECUTED: {execution_result['order']['side']} {execution_result['order']['quantity']} {symbol.value} | ID: {execution_id} | Strategy: {strategy_name} | Confidence: {confidence:.2%}")

                # Log the successful execution
                self.logger.log_signal_progression(
                    symbol=symbol.value,
                    stage="broker",
                    status="Executed",
                    details=f"Order executed successfully: {execution_id}",
                    confidence=confidence
                )

                self.logger.log_strategy_to_broker_flow(
                    symbol=symbol.value,
                    strategy_name=strategy_name,
                    trade_executed=True,
                    signal_type=signal_type,
                    confidence=confidence,
                    reason=f"Trade executed successfully with ID: {execution_id}",
                )

                # Log the successful execution decision
                self.logger.log_decision_reason(
                    component="Orchestrator",
                    symbol=symbol.value,
                    decision="Trade Executed Successfully",
                    reason=f"Order executed successfully with ID: {execution_id}",
                    confidence=confidence,
                    details={
                        'execution_id': execution_id,
                        'quantity': execution_result['order']['quantity'],
                        'side': execution_result['order']['side']
                    }
                )

                # Add to active trades
                self.active_trades[execution_id] = trade_details
            else:
                # Extract error details for clearer logging
                error_msg = execution_result.get('error', 'Unknown error')

                # Log the failed execution with more detail
                self.logger.warning(
                    f"❌ TRADE REJECTED: {error_msg} | Symbol: {symbol.value} | Strategy: {strategy_name} | Intent Confidence: {confidence:.2%}")

                # Log the failed execution
                self.logger.log_signal_progression(
                    symbol=symbol.value,
                    stage="broker",
                    status="Failed",
                    details=f"Order execution failed: {error_msg}",
                    confidence=confidence
                )

                self.logger.log_strategy_to_broker_flow(
                    symbol=symbol.value,
                    strategy_name=strategy_name,
                    trade_executed=False,
                    signal_type=signal_type,
                    confidence=confidence,
                    reason=f"Trade execution failed: {error_msg}",
                )

                # Log the rejection decision
                self.logger.log_decision_reason(
                    component="Orchestrator",
                    symbol=symbol.value,
                    decision="Trade Rejected",
                    reason=f"Trade execution failed: {error_msg}",
                    confidence=confidence,
                    details={'error_message': str(error_msg)}
                )

                # Log specific rejection reason for observability
                if "DUPLICATE:" in str(error_msg):
                    # This is a duplicate prevention rejection from the execution service
                    parts = str(error_msg).split(':')
                    if len(parts) >= 3:
                        dup_symbol = parts[1]
                        dup_direction = parts[2]
                        self.logger.info(
                            f"❌ DUPLICATE PREVENTION: {dup_symbol} {dup_direction} | Strategy: {strategy_name} | Intent Confidence: {confidence:.2%}")
                elif "not available on broker" in str(error_msg):
                    # Symbol not available on broker
                    self.logger.info(
                        f"❌ SYMBOL UNAVAILABLE: {symbol.value} | Strategy: {strategy_name} | Intent Confidence: {confidence:.2%}")
                elif "Stablecoin pair" in str(error_msg):
                    # Stablecoin pair filtered out
                    self.logger.info(
                        f"❌ STABLECOIN PAIR FILTERED: {symbol.value} | Strategy: {strategy_name} | Intent Confidence: {confidence:.2%}")
                else:
                    # Other execution errors
                    self.logger.info(
                        f"❌ EXECUTION ERROR: {symbol.value} | Error: {error_msg} | Strategy: {strategy_name} | Intent Confidence: {confidence:.2%}")

        except Exception as e:
            # Remove from pending intents in case of exception
            try:
                self._remove_pending_execution_intent(execution_intent)
            except Exception as cleanup_error:
                self.logger.warning(f"Warning: Error during pending intent cleanup: {cleanup_error}")
            self.logger.error(f"Error executing strategy for execution intent: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _get_reconcile_broker(self):
        """Return a broker adapter exposing get_all_positions for reconciliation (primary if multi)."""
        es = self.execution_service
        broker = getattr(es, "broker", es)
        brokers = getattr(broker, "brokers", None)
        if isinstance(brokers, dict) and brokers:
            primary = getattr(broker, "primary_broker", None)
            return brokers.get(primary) or next(iter(brokers.values()))
        return broker

    def _reconciliation_loop(self):
        """R1: periodically reconcile local journal vs broker; halt on unrecoverable drift."""
        self.logger.info("Broker reconciliation monitoring started")
        from infrastructure.execution.broker_reconciliation import BrokerReconciliationService
        from infrastructure.execution.live_order_journal import live_order_journal
        svc = BrokerReconciliationService()
        while self.is_running:
            try:
                broker = self._get_reconcile_broker()
                if broker is not None and hasattr(broker, "get_all_positions"):
                    from bootstrap.settings.loaders import load_settings
                    from shared.live_execution_guard import live_execution_guard
                    import os
                    
                    is_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None
                    is_live = False
                    if not is_pytest:
                        try:
                            settings = load_settings()
                            es = self.execution_service
                            broker_name = getattr(es, "broker_name", "bingx")
                            is_live = live_execution_guard.evaluate(broker_name, settings).is_live_send
                        except Exception:
                            is_live = False
                    
                    rep = svc.reconcile(broker, live_order_journal, halt_on_unrecoverable=is_live or is_pytest)
                    if rep.get("halted"):
                        self.logger.critical(f"🛑 RECONCILIATION HALT — unrecoverable drift: {rep['unrecoverable']}")
                        try:
                            if hasattr(self, "risk_alert_service") and self.risk_alert_service:
                                self.risk_alert_service.send_alert(
                                    message=f"Reconciliation halt: {rep['unrecoverable']}", alert_type="critical")
                        except Exception as alert_err:
                            self.logger.warning(f"Reconciliation halt alert failed (non-fatal): {alert_err}")
                    elif not rep.get("in_sync"):
                        self.logger.warning(
                            f"Reconciliation drift (recoverable): resolved={len(rep.get('orders_resolved', []))} "
                            f"recoverable={len(rep.get('recoverable', []))}")
                time.sleep(self.reconcile_interval_seconds)
            except Exception as e:
                self.logger.error(f"Error in reconciliation loop: {e}")
                time.sleep(self.reconcile_interval_seconds)

    def _risk_monitoring_loop(self):
        """Background risk monitoring loop."""
        self.logger.info("Risk monitoring started")

        while self.is_running:
            try:
                # Get current positions and performance
                portfolio_metrics = self.portfolio_service.get_portfolio_metrics()

                # Check for risk violations. A critical breach ENGAGES the
                # LIVE_EXECUTION_GUARD kill switch so the order path is actually halted.
                from shared.live_execution_guard import live_execution_guard

                if 'drawdown' in portfolio_metrics and portfolio_metrics['drawdown'] < -0.15:
                    reason = f"Portfolio drawdown exceeded threshold: {portfolio_metrics['drawdown']}"
                    self.logger.warning(reason)
                    live_execution_guard.engage_kill_switch(reason)
                    self.risk_alert_service.send_alert(message=reason, alert_type="critical")

                # Check leverage limits
                if 'leverage' in portfolio_metrics and portfolio_metrics['leverage'] > 10.0:
                    reason = f"Leverage exceeded threshold: {portfolio_metrics['leverage']}"
                    self.logger.warning(reason)
                    live_execution_guard.engage_kill_switch(reason)
                    self.risk_alert_service.send_alert(message=reason, alert_type="critical")

                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in risk monitoring: {e}")
                time.sleep(30)

    def _active_position_management_loop(self):
        """High-frequency (5s) background loop for dynamic Trailing Stops & Breakeven Protection."""
        self.logger.info("🛡️ Active Position Trailing Stop & Breakeven Management loop started")
        from infrastructure.risk.active_position_manager import active_position_manager

        while self.is_running:
            try:
                # Gather all connected broker adapters
                target_brokers = []
                es = getattr(self, "execution_service", None)
                broker_root = getattr(es, "broker", es)
                sub_brokers = getattr(broker_root, "brokers", None)
                if isinstance(sub_brokers, dict) and sub_brokers:
                    target_brokers.extend(sub_brokers.values())
                elif broker_root:
                    target_brokers.append(broker_root)

                for broker in target_brokers:
                    if not broker:
                        continue
                    positions = []
                    if hasattr(broker, "get_all_positions"):
                        positions = broker.get_all_positions() or []
                    elif hasattr(broker, "get_positions"):
                        positions = broker.get_positions() or []

                    if not positions:
                        continue

                    current_prices = {}
                    for pos in positions:
                        raw_sym = getattr(pos, "symbol", "") or (pos.get("symbol") if isinstance(pos, dict) else "")
                        clean_sym = active_position_manager.normalize_symbol(raw_sym)
                        if not clean_sym:
                            continue

                        # 1. Mark price from position
                        mark_p = getattr(pos, "mark_price", 0) or (pos.get("markPrice") if isinstance(pos, dict) else 0)
                        if mark_p and float(mark_p) > 0:
                            current_prices[clean_sym] = float(mark_p)
                        elif hasattr(self, "market_data_repo") and self.market_data_repo:
                            try:
                                from domain.value_objects import Symbol as DomainSymbol
                                p = self.market_data_repo.get_current_price(DomainSymbol(clean_sym))
                                if p and float(p) > 0:
                                    current_prices[clean_sym] = float(p)
                            except Exception:
                                pass

                    actions = active_position_manager.evaluate_open_positions(broker, current_prices=current_prices)
                    if actions:
                        broker_name = getattr(broker, "name", "broker")
                        self.logger.warning(f"🛡️ Active Position Manager executed {len(actions)} protection action(s) on {broker_name}: {actions}")

                time.sleep(5)
            except Exception as e:
                self.logger.error(f"Error in active position management loop: {e}", exc_info=True)
                time.sleep(5)

    def run_auto_detection(self):
        """Main method to run the auto-detection system."""
        self.initialize_system()
        
        try:
            # Keep the main thread alive to allow background services to run
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("🛑 Auto-detection mode stopped by user")
        finally:
            self.stop_system()

    def stop_system(self):
        """Stop the auto-detection system."""
        self.logger.info("🛑 Stopping Auto-Detection Orchestrator...")

        # Set the flag to stop main loops
        self.is_running = False

        # Notify the execution service that the system is shutting down to prevent new orders
        if hasattr(self, 'execution_service') and self.execution_service:
            try:
                self.execution_service.set_system_running_state(False)
                self.logger.info("Execution service notified of system shutdown")
            except Exception as e:
                self.logger.error(f"Error notifying execution service of shutdown: {e}")

        # Stop the opportunity watcher
        if hasattr(self, 'opportunity_watcher') and self.opportunity_watcher:
            try:
                self.opportunity_watcher.stop_monitoring()
                self.logger.info("Market opportunity watcher stopped")
            except Exception as e:
                self.logger.error(f"Error stopping opportunity watcher: {e}")

        # Clear the opportunity queue to prevent any remaining executions
        with self._pending_intents_lock:
            self.opportunity_queue.clear()
            self.logger.info("Opportunity queue cleared")

        # Clear pending intents tracking
        with self._pending_intents_lock:
            self._pending_intents.clear()
            self._pending_intent_temp_ids.clear()
            self.logger.info("Pending intents tracking cleared")

        # Stop all background threads gracefully
        for thread_name, thread in self.background_threads:
            try:
                # Threads are daemon threads, but we should still wait for them to finish
                thread.join(timeout=2.0)  # Wait up to 2 seconds for each thread to finish
                self.logger.info(f"Background thread '{thread_name}' stopped")
            except Exception as e:
                self.logger.error(f"Error stopping background thread '{thread_name}': {e}")

        # Clear the background threads list
        self.background_threads.clear()

        # Stop the architecture orchestrator if it exists
        try:
            from infrastructure.orchestrators.architecture_orchestrator import architecture_orchestrator
            if hasattr(architecture_orchestrator, 'stop'):
                architecture_orchestrator.stop()
                self.logger.info("Architecture orchestrator stopped")
        except Exception as e:
            self.logger.error(f"Error stopping architecture orchestrator: {e}")

        # Clear any remaining pending orders from the shared tracker
        try:
            from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
            PendingOrdersTracker.clear_all_pending_orders()
            self.logger.info("Shared pending orders tracker cleared")
        except Exception as e:
            self.logger.error(f"Error clearing pending orders tracker: {e}")

        self.logger.info("✅ Auto-Detection Orchestrator stopped successfully")