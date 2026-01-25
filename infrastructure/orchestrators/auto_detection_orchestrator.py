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
from application.configs.configs import Configs


class AutoDetectionOrchestrator:
    """Orchestrator for fully autonomous trading with auto-detection capability following correct architecture."""

    def __init__(self,
                 market_data_repo: DataProviderPort,
                 execution_service: ExecutionPort,
                 portfolio_service: PortfolioManagementPort,
                 optimization_service: IOptimizationService,
                 symbols: List[str],
                 risk_config: Optional[Dict[str, Any]] = None,
                 comprehensive_logging: bool = True):
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
        from shared.event_system import event_router, signal_processor

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
        from shared.event_system import EventType
        self.event_router.subscribe(EventType.EXECUTION_INTENT, self._handle_execution_intent_event)

        # Initialize the market opportunity watcher with the event router (no internal flow processing)
        from infrastructure.watchers.market_opportunity_watcher import MarketOpportunityWatcher
        self.opportunity_watcher = MarketOpportunityWatcher(
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

    def _get_symbol_lock(self, symbol: str) -> threading.Lock:
        """Get or create a lock for a specific symbol to prevent concurrent processing."""
        with self._symbol_processing_locks_lock:
            if symbol not in self._symbol_processing_locks:
                self._symbol_processing_locks[symbol] = threading.Lock()
            return self._symbol_processing_locks[symbol]

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

    def _calculate_opportunity_score(self, execution_intent) -> float:
        """Calculate a comprehensive opportunity score based on multiple factors."""
        try:
            # Base confidence score
            base_confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5

            # Get fused signal information if available
            fused_signal = getattr(execution_intent, 'fused_signal', None)
            if fused_signal:
                dominance_score = getattr(fused_signal, 'dominance_score', 0.0)
                regime_context = getattr(fused_signal, 'regime_context', 'normal')
            else:
                dominance_score = 0.0
                regime_context = 'normal'

            # Risk parameters
            risk_params = getattr(execution_intent, 'risk_parameters', {})
            position_size = risk_params.get('max_position_size', 0.02)
            stop_loss_pct = risk_params.get('stop_loss_pct', 0.02)
            take_profit_pct = risk_params.get('take_profit_pct', 0.03)

            # Calculate reward-to-risk ratio
            reward_risk_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 1.0

            # Calculate opportunity score based on multiple factors
            # Weighted combination of confidence, dominance, position size, and reward-to-risk ratio
            import os
            confidence_weight = Configs.strategy.opportunity_score_confidence_weight if Configs.strategy and hasattr(Configs.strategy, 'opportunity_score_confidence_weight') else 0.4
            dominance_weight = Configs.strategy.opportunity_score_dominance_weight if Configs.strategy and hasattr(Configs.strategy, 'opportunity_score_dominance_weight') else 0.2
            position_size_weight = Configs.strategy.opportunity_score_position_size_weight if Configs.strategy and hasattr(Configs.strategy, 'opportunity_score_position_size_weight') else 0.15
            reward_risk_weight = Configs.strategy.opportunity_score_reward_risk_weight if Configs.strategy and hasattr(Configs.strategy, 'opportunity_score_reward_risk_weight') else 0.15
            regime_bonus = Configs.strategy.opportunity_score_regime_bonus if Configs.strategy and hasattr(Configs.strategy, 'opportunity_score_regime_bonus') else 0.1  # Bonus for favorable market regimes

            # Normalize values to 0-1 scale
            normalized_confidence = min(1.0, base_confidence)
            normalized_dominance = min(1.0, max(0.0, dominance_score))
            normalized_position_size = min(1.0, position_size / 0.1)  # Assuming max position size of 10%
            normalized_reward_risk = min(1.0, reward_risk_ratio / 3.0)  # Assuming max R/R of 3:1

            # Calculate base score
            base_score = (
                confidence_weight * normalized_confidence +
                dominance_weight * normalized_dominance +
                position_size_weight * normalized_position_size +
                reward_risk_weight * normalized_reward_risk
            )

            # Add regime bonus for favorable market conditions
            regime_bonus_factor = 0.0
            if regime_context.lower() in ['trending', 'breakout', 'momentum']:
                regime_bonus_factor = regime_bonus
            elif regime_context.lower() in ['volatile', 'high_volatility']:
                # Slightly reduce score for high volatility
                regime_bonus_factor = -0.05

            final_score = base_score + regime_bonus_factor

            # Ensure score is within reasonable bounds
            final_score = max(0.0, min(2.0, final_score))

            return final_score

        except Exception as e:
            self.logger.error(f"Error calculating opportunity score: {e}")
            # Return a default score in case of error
            return 0.5

    def _check_duplicate_execution_intent(self, execution_intent) -> bool:
        """Check if an execution intent is a duplicate based on symbol and direction."""
        # Check if duplicate prevention is enabled
        prevent_same_direction = Configs.execution.prevent_same_direction_trade_per_symbol if Configs.execution and hasattr(Configs.execution, 'prevent_same_direction_trade_per_symbol') else True

        if not prevent_same_direction:
            return False  # No duplicate prevention needed

        symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
        direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)

        with self._pending_intents_lock:
            # Check the shared tracker used by execution services to ensure consistency
            # This is the primary check to avoid double-rejection issues
            from domain.value_objects import Symbol
            symbol_obj = Symbol(symbol)
            if self._pending_orders_tracker.has_pending_order_in_direction(symbol_obj, direction):
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                self.logger.debug(f"⚠️ DUPLICATE CHECK: Pending {direction} order exists in shared tracker for {symbol} — broker will handle final confirmation. | Intent Confidence: {confidence:.2%}")
                return True  # Duplicate found in shared tracker

            # Add this intent to the orchestrator's internal tracking only
            # The execution service will handle the shared tracker when actually placing the order
            if symbol not in self._pending_intents:
                self._pending_intents[symbol] = {}
            self._pending_intents[symbol][direction] = datetime.now()

            # Store a reference to the execution intent for later removal
            # Don't add to shared tracker here - let the execution service handle that
            self._pending_intent_temp_ids[id(execution_intent)] = None  # No shared tracker ID yet

        return False  # Not a duplicate

    def _check_broker_active_orders_for_duplicate(self, execution_intent) -> bool:
        """Check if there are active orders on the broker that would conflict with this execution intent."""
        # Check if duplicate prevention is enabled
        prevent_same_direction = Configs.execution.prevent_same_direction_trade_per_symbol if Configs.execution and hasattr(Configs.execution, 'prevent_same_direction_trade_per_symbol') else True

        if not prevent_same_direction:
            return True  # No duplicate prevention needed, allow the intent

        symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
        direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)

        try:
            # Determine the intended position side based on the order side
            intended_position_side = None
            if direction == 'BUY':
                intended_position_side = 'LONG'
            elif direction == 'SELL':
                intended_position_side = 'SHORT'
            else:
                # If it's not a standard BUY/SELL, we'll use the direction as-is
                intended_position_side = direction

            # Check if the execution service has access to broker methods
            # For BrokerExecutionService, check if it has the underlying broker with get_open_orders
            if hasattr(self.execution_service, 'broker'):
                # Check if the broker has get_open_orders method
                if hasattr(self.execution_service.broker, 'get_open_orders'):
                    try:
                        # Get open orders for this symbol
                        open_orders = self.execution_service.broker.get_open_orders(symbol)

                        # Check if there are any open orders in the same direction
                        for order in open_orders:
                            # Check if the order is for the same symbol and in the same direction
                            if (hasattr(order, 'symbol') and
                                (order.symbol.value if hasattr(order.symbol, 'value') else str(order.symbol)) == symbol and
                                hasattr(order, 'side')):

                                order_side = order.side.name if hasattr(order.side, 'name') else str(order.side)
                                order_position_side = 'LONG' if order_side == 'BUY' else 'SHORT'

                                if order_position_side == intended_position_side:
                                    confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                                    self.logger.info(f"❌ DUPLICATE REJECTED: Active {order_side} order already exists on broker for {symbol}. Preventing duplicate same-direction intent. | Intent Confidence: {confidence:.2%}")
                                    return False  # Found duplicate, don't allow this intent
                    except Exception as e:
                        # If we can't check open orders, log the error but continue
                        self.logger.warning(f"⚠️ Could not check open orders on broker for {symbol}: {e}. Continuing with execution attempt.")
                else:
                    # For MultiBrokerExecutionService, check if it has get_open_orders
                    if hasattr(self.execution_service, 'get_open_orders'):
                        try:
                            # Get open orders for this symbol
                            open_orders = self.execution_service.get_open_orders(symbol)

                            # Check if there are any open orders in the same direction
                            for order in open_orders:
                                # Check if the order is for the same symbol and in the same direction
                                if (hasattr(order, 'symbol') and
                                    (order.symbol.value if hasattr(order.symbol, 'value') else str(order.symbol)) == symbol and
                                    hasattr(order, 'side')):

                                    order_side = order.side.name if hasattr(order.side, 'name') else str(order.side)
                                    order_position_side = 'LONG' if order_side == 'BUY' else 'SHORT'

                                    if order_position_side == intended_position_side:
                                        confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                                        self.logger.info(f"❌ DUPLICATE REJECTED: Active {order_side} order already exists on broker for {symbol}. Preventing duplicate same-direction intent. | Intent Confidence: {confidence:.2%}")
                                        return False  # Found duplicate, don't allow this intent
                        except Exception as e:
                            # If we can't check open orders, log the error but continue
                            self.logger.warning(f"⚠️ Could not check open orders on broker for {symbol}: {e}. Continuing with execution attempt.")

            # If we couldn't check open orders or no duplicates found, allow the intent
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

    def _execute_trade_from_intent(self, execution_intent):
        """Execute trade based on execution intent from strategy layer."""
        try:
            # Check if the system is still running - if not, reject the execution
            if not self.is_running:
                self.logger.warning(f"System is shutting down, rejecting execution intent for {execution_intent.symbol.value}")
                # Remove from pending intents since we're not executing
                self._remove_pending_execution_intent(execution_intent)
                return {
                    'status': 'failed',
                    'error': f"SYSTEM_SHUTDOWN: Execution rejected as system is shutting down"
                }

            # Check for active orders on the broker before processing the intent
            # This prevents duplicate orders when the system doesn't have full awareness of broker state
            if not self._check_broker_active_orders_for_duplicate(execution_intent):
                # Remove from pending intents since we're not executing
                self._remove_pending_execution_intent(execution_intent)
                symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
                direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                return {
                    'status': 'failed',
                    'error': f"DUPLICATE:{symbol}:{direction} - Active order already exists on broker"
                }

            # Double-check for duplicates right before execution to prevent race conditions
            # This catches cases where multiple threads might have passed the initial check
            # but are now trying to execute simultaneously
            # NOTE: The actual broker service will also perform this check, so we'll just log if found
            # but allow the broker service to handle the rejection to avoid duplicate messages
            prevent_same_direction = Configs.execution.prevent_same_direction_trade_per_symbol if Configs.execution and hasattr(Configs.execution, 'prevent_same_direction_trade_per_symbol') else True
            if prevent_same_direction:
                symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
                direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)

                # Check the shared tracker again right before execution
                from domain.value_objects import Symbol
                symbol_obj = Symbol(symbol)
                if self._pending_orders_tracker.has_pending_order_in_direction(symbol_obj, direction):
                    confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                    self.logger.debug(f"DUPLICATE CHECK: Pending {direction} order exists in shared tracker for {symbol}. Broker service will handle rejection. | Intent Confidence: {confidence:.2%}")

                    # We'll let the broker service handle the actual rejection to avoid duplicate messages
                    # Continue to execution where the broker service will reject it

        # Check if this is a stablecoin pair that should be filtered out
            filter_stablecoin_pairs = Configs.data.filter_out_stablecoin_pairs if Configs.data and hasattr(Configs.data, 'filter_out_stablecoin_pairs') else True
            allowed_stablecoins = (Configs.data.allowed_stablecoins if Configs.data and Configs.data.allowed_stablecoins else 'USDT,BUSD,USDC,DAI,PAX,TUSD,USDD,FDUSD').split(',')

            symbol_str = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)

            if filter_stablecoin_pairs:
                # Check if both parts of the symbol are stablecoins (e.g., USDCUSDT)
                # Extract base and quote currencies assuming format like BTCUSDT
                if len(symbol_str) > 6:  # At least 3 chars for base + 3 chars for quote
                    # Look for common stablecoin endings
                    for stablecoin in allowed_stablecoins:
                        if symbol_str.endswith(stablecoin):
                            base_currency = symbol_str[:-len(stablecoin)]
                            if base_currency in allowed_stablecoins:
                                # Both base and quote are stablecoins (e.g., USDCUSDT, BUSDUSDT)
                                self.logger.info(f"❌ STABLECOIN PAIR REJECTED: {symbol_str} | Reason: Both base and quote are stablecoins | Strategy: {execution_intent.strategy_name} | Intent Confidence: {float(execution_intent.intent_confidence.value):.2%}")

                                # Remove from pending intents since we're not executing
                                self._remove_pending_execution_intent(execution_intent)
                                return {
                                    'status': 'failed',
                                    'error': f"Stablecoin pair {symbol_str} filtered out"
                                }

            # Create order from execution intent
            from domain.entities.signal_entities import Order, OrderSide
            from domain.value_objects import Money
            from decimal import Decimal

            # Get current price for the symbol to determine position size
            current_price = None
            if self.market_data_repo:
                try:
                    current_price = self.market_data_repo.get_current_price(execution_intent.symbol)
                except:
                    # If we can't get current price from data repo, try to get from exchange directly
                    pass

            # If we still don't have a price, use a fallback
            if current_price is None or current_price <= 0:
                # Try to get price from exchange directly
                try:
                    import ccxt
                    exchange = ccxt.binance()
                    ticker = exchange.fetch_ticker(execution_intent.symbol.value)
                    current_price = ticker['last'] if 'last' in ticker else ticker['close']
                except:
                    # If all methods fail, we'll still proceed but log the issue
                    self.logger.warning(f"Could not get current price for {execution_intent.symbol.value}, using default price")
                    # Use a more reasonable fallback price based on the symbol
                    # Extract base currency to estimate a reasonable price
                    symbol_str = execution_intent.symbol.value
                    if symbol_str.startswith(('BTC', 'WBTC')):
                        current_price = 45000.0  # Bitcoin price range
                    elif symbol_str.startswith(('ETH', 'WETH')):
                        current_price = 2500.0  # Ethereum price range
                    elif symbol_str.startswith(('SOL', 'AVAX', 'FTM', 'APT', 'AR')):
                        current_price = 90.0   # Mid-range altcoins
                    elif symbol_str.startswith(('BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC', 'LINK', 'UNI', 'LTC', 'BCH')):
                        current_price = 10.0   # Lower range altcoins
                    elif symbol_str.startswith(('XLM', 'TRX', 'ATOM', 'NEAR', 'FIL', 'ETC', 'VET', 'XTZ', 'ICX', 'HBAR', 'SUI')):
                        current_price = 0.5    # Penny stocks/crypto range
                    elif symbol_str.startswith(('SHIB', 'PEPE', 'FLOKI')):
                        current_price = 0.00001  # Meme coin range
                    else:
                        # For any other symbol, use a reasonable default based on common patterns
                        # Use a random price between $0.01 and $500 to cover most crypto ranges
                        import random
                        current_price = random.uniform(0.01, 500.0)

            # Use risk parameters from the execution intent
            risk_params = execution_intent.risk_parameters
            position_size_pct = risk_params.get('max_position_size', 0.02)  # Default 2%

            # Fixed Position Size Configuration (for testing purposes)
            fixed_position_size_enabled = Configs.position_sizing.fixed_position_size_enabled if Configs.position_sizing and hasattr(Configs.position_sizing, 'fixed_position_size_enabled') else False
            fixed_position_amount = Configs.position_sizing.fixed_position_amount if Configs.position_sizing and hasattr(Configs.position_sizing, 'fixed_position_amount') else 10.0  # Default to $10 for testing

            # Calculate quantity based on risk parameters and account balance
            try:
                if fixed_position_size_enabled:
                    # Use fixed position size for testing
                    quantity = fixed_position_amount / current_price
                    self.logger.info(f"Using fixed position size: ${fixed_position_amount} at ${current_price} = {quantity} units")
                else:
                    # In a real implementation, we'd get portfolio metrics from portfolio service
                    # For now, using a default account balance from environment variable
                    account_balance = Configs.position_sizing.default_account_balance if Configs.position_sizing and hasattr(Configs.position_sizing, 'default_account_balance') else 10000.0  # Default to $10,000 if not available
                    position_value = account_balance * position_size_pct

                    # Calculate quantity based on position value and current price
                    quantity = position_value / current_price

                    # Apply any quantity adjustments from risk parameters
                    if 'position_quantity' in risk_params:
                        quantity = risk_params['position_quantity']

            except:
                # If portfolio service fails, use a default quantity
                if fixed_position_size_enabled:
                    # Use fixed position size for testing
                    quantity = fixed_position_amount / current_price
                    self.logger.info(f"Using fixed position size (fallback): ${fixed_position_amount} at ${current_price} = {quantity} units")
                else:
                    # Use default account balance from environment variable
                    default_account_balance = Configs.position_sizing.default_account_balance if Configs.position_sizing and hasattr(Configs.position_sizing, 'default_account_balance') else 1000.0  # Default to $1,000 if not available
                    quantity = position_size_pct * default_account_balance / current_price

            # Ensure minimum quantity to avoid issues with small trades
            if quantity < 0.001:
                quantity = 0.001  # Minimum trade size

            # Create order object using domain entities
            from domain.entities.signal_entities import Order, OrderSide
            from domain.value_objects import Money

            # Use the side from the execution intent
            order_side = execution_intent.side

            # Ensure symbol is properly formatted for the broker
            symbol_value = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)

            # Determine position side based on order side for futures trading
            position_side = "LONG" if order_side.name == 'BUY' else "SHORT"

            # Create order with risk parameters from the execution intent (set by Strategy layer)
            # The Strategy layer should have already calculated all risk parameters including SL/TP
            order = Order(
                symbol=symbol_value,  # Use string value instead of Symbol object
                side=order_side,
                order_type="MARKET",  # Using string instead of enum
                quantity=quantity,
                price=Money(amount=float(current_price), currency='USDT') if current_price else None,
                strategy_name=execution_intent.strategy_name,  # Strategy name comes from intent
                timestamp=datetime.now(),
                position_side=position_side,  # Add position side for futures trading
                stop_loss_price=getattr(execution_intent, 'stop_loss_price', None),  # SL from strategy
                take_profit_price=getattr(execution_intent, 'take_profit_price', None),  # TP from strategy
                parent_execution_intent=execution_intent  # Link back to the execution intent
            )

            # Log the order creation with comprehensive details
            confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
            self.logger.info(f"📝 ORDER CREATED: {symbol_value} | Side: {order_side.name} | Quantity: {quantity:.6f} | Price: ${current_price:.4f} | Strategy: {execution_intent.strategy_name} | Confidence: {confidence:.2%}")

            # Log the decision to proceed with order execution
            self.logger.log_decision_reason(
                component="Orchestrator",
                symbol=symbol_value,
                decision="Order Created - Ready for Execution",
                reason="Order created with all required parameters from execution intent",
                confidence=confidence,
                details={
                    'quantity': quantity,
                    'price': current_price,
                    'position_side': position_side,
                    'stop_loss': getattr(execution_intent, 'stop_loss_price', 'N/A'),
                    'take_profit': getattr(execution_intent, 'take_profit_price', 'N/A')
                }
            )

            # Validate symbol availability before executing order
            if hasattr(self.execution_service, 'get_available_symbols'):
                try:
                    available_symbols = self.execution_service.get_available_symbols()
                    if symbol_value not in available_symbols:
                        self.logger.warning(f"⚠️ Symbol {symbol_value} not available on any configured broker. Skipping order.")
                        # Remove from pending intents since we're not executing
                        self._remove_pending_execution_intent(execution_intent)

                        # Log the rejection with clear reason
                        self.logger.info(
                            f"❌ REJECTED SYMBOL: {symbol_value} | Reason: Not available on any configured broker | Strategy: {execution_intent.strategy_name} | Intent Confidence: {float(execution_intent.intent_confidence.value):.2%}")

                        return {
                            'status': 'failed',
                            'error': f"Symbol {symbol_value} not available on broker"
                        }
                except Exception as e:
                    # If we can't check available symbols, log the error but continue with execution
                    self.logger.warning(f"⚠️ Could not check available symbols from execution service: {e}. Continuing with execution attempt.")
            else:
                # If the execution service doesn't have get_available_symbols method, log this
                self.logger.debug(f"Execution service doesn't have get_available_symbols method. Proceeding with execution attempt for {symbol_value}")

            # Execute order through execution service
            execution_id = self.execution_service.execute_order(order)

            # Check if execution was prevented by duplicate prevention (returns None)
            if execution_id is None:
                # Remove from pending intents since execution was prevented
                self._remove_pending_execution_intent(execution_intent)

                # Log the duplicate prevention with clear reason
                self.logger.info(
                    f"❌ DUPLICATE PREVENTION: {symbol_value} | Reason: Duplicate same-direction trade prevented | Strategy: {execution_intent.strategy_name} | Intent Confidence: {float(execution_intent.intent_confidence.value):.2%}")

                return {
                    'status': 'failed',
                    'error': f"DUPLICATE:{symbol_value}:{position_side}"
                }

            # If execution_id is valid, continue with successful execution
            # Remove from pending intents after successful execution
            self._remove_pending_execution_intent(execution_intent)

            # Log successful execution
            confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
            self.logger.info(f"✅ ORDER EXECUTED: {symbol_value} | ID: {execution_id} | Strategy: {execution_intent.strategy_name} | Confidence: {confidence:.2%}")

            # Log the successful execution decision
            self.logger.log_decision_reason(
                component="Orchestrator",
                symbol=symbol_value,
                decision="Order Executed Successfully",
                reason=f"Order executed successfully with ID: {execution_id}",
                confidence=confidence,
                details={
                    'execution_id': execution_id,
                    'quantity': quantity,
                    'side': execution_intent.side.name
                }
            )

            return {
                'status': 'executed',
                'execution_id': execution_id,
                'order': {
                    'side': execution_intent.side.name,
                    'quantity': quantity,
                    'symbol': execution_intent.symbol.value
                }
            }
        except Exception as e:
            # Remove from pending intents in case of exception
            try:
                self._remove_pending_execution_intent(execution_intent)
            except Exception as cleanup_error:
                self.logger.warning(f"Warning: Error during pending intent cleanup: {cleanup_error}")
            return {
                'status': 'failed',
                'error': str(e)
            }

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

    def _risk_monitoring_loop(self):
        """Background risk monitoring loop."""
        self.logger.info("Risk monitoring started")

        while self.is_running:
            try:
                # Get current positions and performance
                portfolio_metrics = self.portfolio_service.get_portfolio_metrics()

                # Check for risk violations
                if 'drawdown' in portfolio_metrics and portfolio_metrics['drawdown'] < -0.15:
                    self.logger.warning(f"Portfolio drawdown exceeded threshold: {portfolio_metrics['drawdown']}")
                    self.risk_alert_service.send_alert(
                        message=f"Portfolio drawdown exceeded threshold: {portfolio_metrics['drawdown']}",
                        alert_type="critical"
                    )

                # Check leverage limits
                if 'leverage' in portfolio_metrics and portfolio_metrics['leverage'] > 10.0:
                    self.logger.warning(f"Leverage exceeded threshold: {portfolio_metrics['leverage']}")
                    self.risk_alert_service.send_alert(
                        message=f"Leverage exceeded threshold: {portfolio_metrics['leverage']}",
                        alert_type="critical"
                    )

                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in risk monitoring: {e}")
                time.sleep(30)

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