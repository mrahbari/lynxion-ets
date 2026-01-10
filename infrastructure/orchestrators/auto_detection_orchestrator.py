"""
Auto-Detection Orchestrator for fully autonomous trading system following correct architecture.
Monitors markets continuously, identifies opportunities, and triggers appropriate strategies.
Following correct architecture: Watcher → Engine → Fusion → Strategy → Broker
"""
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from domain.ports.data_ports import DataProviderPort
from domain.ports.execution_ports import ExecutionPort
from domain.ports.portfolio_ports import PortfolioManagementPort
from domain.ports.optimization_ports import IOptimizationService
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from infrastructure.services.risk_alerts import RiskAlertService
import os


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
        self._pending_intents_lock = threading.Lock()
        self._pending_intents = {}  # symbol -> {direction: timestamp}

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

        while self.is_running:
            try:
                if self.opportunity_queue:
                    opportunity = self.opportunity_queue.pop(0)  # Get oldest opportunity
                    self._execute_strategy_for_opportunity(opportunity)
                    processed_count += 1
                else:
                    # Log when no opportunities are in the queue to show system is still active
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        current_time = time.time()
                        if current_time - last_report_time >= 10:  # Log every 10 seconds if no opportunities
                            self.logger.log_background_activity(
                                "Opportunity Monitoring",
                                f"No opportunities in queue, system monitoring {len(self.active_trades)} active trades",
                                queue_size=len(self.opportunity_queue),
                                active_trades=len(self.active_trades)
                            )
                            last_report_time = current_time

                # Log periodic detailed reports
                current_time = time.time()
                if current_time - last_report_time >= report_interval:
                    self.logger.info(f"📈 OPPORTUNITY PROCESSING: Processed: {processed_count} | "
                                     f"Queue size: {len(self.opportunity_queue)} | "
                                     f"Active trades: {len(self.active_trades)}")
                    processed_count = 0
                    rejected_count = 0
                    last_report_time = current_time

                time.sleep(1)  # Check queue every second
            except Exception as e:
                self.logger.error(f"Error in opportunity processing loop: {e}")
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

        # Check for duplicate execution intent before adding to queue
        if hasattr(execution_intent, 'side') and hasattr(execution_intent, 'symbol'):
            if self._check_duplicate_execution_intent(execution_intent):
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                self.logger.info(f"Duplicate execution intent rejected for {symbol} {execution_intent.side.name} | Intent Confidence: {confidence:.2%}")
                return  # Don't add duplicate to queue

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
        self.opportunity_queue.append(execution_intent)

    def _execute_strategy_for_opportunity(self, execution_intent):
        """Execute the appropriate strategy for an execution intent following correct architecture."""
        try:
            # The parameter should now be an execution intent directly
            if not execution_intent or not hasattr(execution_intent, 'symbol'):
                self.logger.warning(f"Invalid execution intent received: {execution_intent}")
                return

            symbol = execution_intent.symbol
            strategy_name = getattr(execution_intent, 'strategy_name', 'unknown')
            confidence = float(getattr(execution_intent.intent_confidence, 'value', 0.5))

            self.logger.info(
                f"🎯 Executing trade for {strategy_name} on {symbol.value} with intent confidence {confidence:.2%}")

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
                    f"✅ ACCEPTED TRADE: {execution_result['order']['side']} {execution_result['order']['quantity']} {symbol.value} | Strategy: {strategy_name} | Intent Confidence: {confidence:.2%}")

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

                # Add to active trades
                self.active_trades[execution_id] = trade_details
            else:
                # Extract error details for clearer logging
                error_msg = execution_result.get('error', 'Unknown error')

                # Log the failed execution with more detail
                self.logger.warning(
                    f"❌ REJECTED TRADE: {error_msg} | Symbol: {symbol.value} | Strategy: {strategy_name} | Intent Confidence: {confidence:.2%}")

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
            except:
                pass  # Ignore errors during cleanup
            self.logger.error(f"Error executing strategy for execution intent: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _handle_execution_intent_event(self, event):
        """Handle execution intent events from the event system."""
        try:
            execution_intent = event.data
            self.logger.info(f"Received execution intent event for {execution_intent.symbol.value}")

            # Check for duplicate execution intent before adding to queue
            if self._check_duplicate_execution_intent(execution_intent):
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                self.logger.info(f"Duplicate execution intent rejected for {execution_intent.symbol.value} {execution_intent.side.name} | Intent Confidence: {confidence:.2%}")
                return  # Don't add duplicate to queue

            # Add the execution intent to the opportunity queue for processing
            self.opportunity_queue.append(execution_intent)

            # Log the receipt of the execution intent
            self.logger.log_background_activity(
                "Execution Intent Received",
                f"Received execution intent for {execution_intent.symbol.value} from event system",
                symbol=execution_intent.symbol.value,
                strategy=execution_intent.strategy_name,
                confidence=float(execution_intent.intent_confidence.value)
            )
        except Exception as e:
            self.logger.error(f"Error handling execution intent event: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _check_duplicate_execution_intent(self, execution_intent) -> bool:
        """Check if an execution intent is a duplicate based on symbol and direction."""
        # Check if duplicate prevention is enabled
        prevent_same_direction = os.getenv('PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL', 'true').lower() == 'true'

        if not prevent_same_direction:
            return False  # No duplicate prevention needed

        symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
        direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)

        with self._pending_intents_lock:
            # Check if there's already a pending intent for this symbol and direction
            if symbol in self._pending_intents:
                if direction in self._pending_intents[symbol]:
                    confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                    self.logger.info(f"❌ DUPLICATE REJECTED: Pending {direction} intent exists for {symbol}. Preventing duplicate same-direction intent. | Intent Confidence: {confidence:.2%}")
                    return True  # Duplicate found

            # Add this intent to the pending list
            if symbol not in self._pending_intents:
                self._pending_intents[symbol] = {}
            self._pending_intents[symbol][direction] = datetime.now()

        return False  # Not a duplicate

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

    def _execute_trade_from_intent(self, execution_intent):
        """Execute trade based on execution intent from strategy layer."""
        try:
            # Check if this is a stablecoin pair that should be filtered out
            symbol_str = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)

            # Check if stablecoin pair filtering is enabled
            filter_stablecoin_pairs = os.getenv('FILTER_OUT_STABLECOIN_PAIRS', 'true').lower() == 'true'
            allowed_stablecoins = os.getenv('ALLOWED_STABLECOINS', 'USDT,BUSD,USDC,DAI,PAX,TUSD,USDD,FDUSD').split(',')

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
                    current_price = 50000.0  # Fallback price

            # Use risk parameters from the execution intent
            risk_params = execution_intent.risk_parameters
            position_size_pct = risk_params.get('max_position_size', 0.02)  # Default 2%

            # Fixed Position Size Configuration (for testing purposes)
            fixed_position_size_enabled = os.getenv('FIXED_POSITION_SIZE_ENABLED', 'false').lower() == 'true'
            fixed_position_amount = float(os.getenv('FIXED_POSITION_AMOUNT', '10.0'))  # Default to $10 for testing

            # Calculate quantity based on risk parameters and account balance
            try:
                if fixed_position_size_enabled:
                    # Use fixed position size for testing
                    quantity = fixed_position_amount / current_price
                    self.logger.info(f"Using fixed position size: ${fixed_position_amount} at ${current_price} = {quantity} units")
                else:
                    # In a real implementation, we'd get portfolio metrics from portfolio service
                    # For now, using a default account balance from environment variable
                    account_balance = float(os.getenv('DEFAULT_ACCOUNT_BALANCE', '10000.0'))  # Default to $10,000 if not available
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
                    default_account_balance = float(os.getenv('DEFAULT_ACCOUNT_BALANCE', '1000.0'))  # Default to $1,000 if not available
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

            # Determine position side based on order side for futures trading
            order_side = execution_intent.side
            position_side = "LONG" if order_side.name == 'BUY' else "SHORT"

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
            except:
                pass  # Ignore errors during cleanup
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
        self.logger.info("Stopping Auto-Detection Orchestrator...")
        self.is_running = False

        # The background threads are daemon threads, so they will stop automatically
        # when the main program exits

        self.logger.info("Auto-Detection Orchestrator stopped")