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
        from shared.event_system import event_router

        self.engine_service = engine_service
        self.fusion_service = fusion_service
        self.strategy_manager = strategy_manager

        # Initialize the architecture orchestrator to handle proper flow
        from infrastructure.orchestrators.architecture_orchestrator import architecture_orchestrator
        architecture_orchestrator.start()

        # Initialize the market opportunity watcher with the event router (no internal flow processing)
        from infrastructure.watchers.market_opportunity_watcher import MarketOpportunityWatcher
        self.opportunity_watcher = MarketOpportunityWatcher(
            symbols=symbols if symbols else None,
            opportunity_callback=self._handle_opportunity,
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
        """Handle detected market opportunity."""
        self.logger.info(
            f"💎 Handling opportunity: {opportunity['symbol']} - Execution Intent: {opportunity.get('execution_intent', 'None')} with confidence {opportunity.get('confidence', 0):.2%}")

        # Log the flow from watcher to engine
        self.logger.log_watcher_to_engine_flow(
            symbol=opportunity['symbol'],
            watcher_name="MarketOpportunityWatcher",
            signal_generated=bool(opportunity.get('execution_intent')),
            signal_type=opportunity.get('execution_intent', {}).get('side', 'N/A') if opportunity.get('execution_intent') else 'N/A',
            confidence=opportunity.get('confidence', 0),
            reason=f"Opportunity detected with execution intent",
        )

        # Log the decision at the orchestrator level
        self.logger.log_decision_reason(
            component="Orchestrator",
            symbol=opportunity['symbol'],
            decision="Opportunity Queued",
            reason=f"Opportunity detected by watcher with execution intent",
            confidence=opportunity.get('confidence', 0)
        )

        # Log background activity in comprehensive mode
        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
            self.logger.log_background_activity(
                "Opportunity Detection",
                f"Detected opportunity for {opportunity['symbol']} with confidence {opportunity.get('confidence', 0):.2%}",
                symbol=opportunity['symbol'],
                execution_intent=bool(opportunity.get('execution_intent')),
                confidence=opportunity.get('confidence', 0)
            )

        self.opportunity_queue.append(opportunity)

    def _execute_strategy_for_opportunity(self, opportunity: Dict[str, Any]):
        """Execute the appropriate strategy for an opportunity following correct architecture."""
        try:
            # The opportunity should contain an execution intent from the strategy layer
            execution_intent = opportunity.get('execution_intent')
            if not execution_intent:
                self.logger.warning(f"No execution intent found in opportunity: {opportunity}")
                return

            symbol = execution_intent.symbol
            strategy_name = execution_intent.strategy_name
            confidence = float(execution_intent.intent_confidence.value)

            self.logger.info(
                f"🎯 Executing trade for {strategy_name} on {symbol.value} with intent confidence {confidence:.2%}")

            # Log the flow from strategy to broker
            self.logger.log_signal_progression(
                symbol=symbol.value,
                stage="strategy",
                status="Ready for Execution",
                details=f"Execution intent prepared for broker: {execution_intent.side.name}",
                confidence=confidence
            )

            self.logger.log_strategy_to_broker_flow(
                symbol=symbol.value,
                strategy_name=strategy_name,
                trade_executed=False,  # We don't know yet, so we'll log the execution separately
                signal_type=execution_intent.side.name,
                confidence=confidence,
                reason=f"Execution intent generated with confidence {confidence:.2%}",
            )

            # Execute trade through execution service using the execution intent
            execution_result = self._execute_trade_from_intent(execution_intent)

            # Track active trade with detailed decision data
            trade_details = {
                'strategy': strategy_name,
                'side': execution_intent.side.name,
                'timestamp': datetime.now().isoformat(),
                'execution_result': execution_result,
                'intent_confidence': confidence,
                'opportunity_confidence': opportunity.get('confidence', 0),
                'decision_factors': {
                    'intent_quality': confidence,
                    'opportunity_strength': opportunity.get('confidence', 0),
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
                    signal_type=execution_intent.side.name,
                    confidence=confidence,
                    reason=f"Trade executed successfully with ID: {execution_id}",
                )

                # Add to active trades
                self.active_trades[execution_id] = trade_details
            else:
                self.logger.warning(
                    f"❌ REJECTED TRADE: {execution_result.get('error', 'Unknown error')} | Strategy: {strategy_name} | Intent Confidence: {confidence:.2%}")
                
                # Log the failed execution
                self.logger.log_signal_progression(
                    symbol=symbol.value,
                    stage="broker",
                    status="Failed",
                    details=f"Order execution failed: {execution_result.get('error', 'Unknown error')}",
                    confidence=confidence
                )

                self.logger.log_strategy_to_broker_flow(
                    symbol=symbol.value,
                    strategy_name=strategy_name,
                    trade_executed=False,
                    signal_type=execution_intent.side.name,
                    confidence=confidence,
                    reason=f"Trade execution failed: {execution_result.get('error', 'Unknown error')}",
                )

        except Exception as e:
            self.logger.error(f"Error executing strategy for opportunity: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _execute_trade_from_intent(self, execution_intent):
        """Execute trade based on execution intent from strategy layer."""
        try:
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
            import os
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
                    import os
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
                    import os
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

            # Determine position side based on order side for futures trading
            position_side = "LONG" if order_side.name == 'BUY' else "SHORT"

            # Ensure symbol is properly formatted for the broker
            symbol_value = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)

            # Create order with proper risk parameters from the intent
            order = Order(
                symbol=symbol_value,  # Use string value instead of Symbol object
                side=order_side,
                order_type="MARKET",  # Using string instead of enum
                quantity=quantity,
                price=Money(amount=current_price, currency='USDT') if current_price else None,
                strategy_name=execution_intent.strategy_name,  # Strategy name comes from intent
                timestamp=datetime.now(),
                position_side=position_side,  # Add position side for futures trading
                stop_loss_price=Money(amount=risk_params.get('stop_loss_price', current_price * 0.98), currency='USDT'),  # Default SL
                take_profit_price=Money(amount=risk_params.get('take_profit_price', current_price * 1.03), currency='USDT'),  # Default TP
                parent_execution_intent=execution_intent  # Link back to the execution intent
            )

            # Validate symbol availability before executing order
            if hasattr(self.execution_service, 'get_available_symbols'):
                available_symbols = self.execution_service.get_available_symbols()
                if symbol_value not in available_symbols:
                    self.logger.warning(f"⚠️ Symbol {symbol_value} not available on any configured broker. Skipping order.")
                    return {
                        'status': 'failed',
                        'error': f"Symbol {symbol_value} not available on broker"
                    }

            # Execute order through execution service
            execution_id = self.execution_service.execute_order(order)

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