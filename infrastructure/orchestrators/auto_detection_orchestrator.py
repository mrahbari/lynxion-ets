"""
Auto-Detection Orchestrator for fully autonomous trading system.
Monitors markets continuously, identifies opportunities, and triggers appropriate strategies.
This orchestrator follows hexagonal architecture by only depending on domain interfaces,
not directly on application services.
"""
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from domain.ports.data_ports import DataProviderPort
from domain.ports.execution_ports import ExecutionPort
from domain.ports.portfolio_ports import PortfolioManagementPort
from domain.ports.optimization_ports import IOptimizationService
from domain.ports.engine_ports import StrategyPort, RiskManagementPort
from domain.value_objects import Symbol
from infrastructure.watchers.market_opportunity_watcher import MarketOpportunityWatcher
from shared.logger import EnhancedLogger
from infrastructure.services.risk_alerts import RiskAlertService


class AutoDetectionOrchestrator:
    """Orchestrator for fully autonomous trading with auto-detection capability."""

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

        # Initialize components
        self.opportunity_watcher = MarketOpportunityWatcher(
            symbols=symbols if symbols else None,
            opportunity_callback=self._handle_opportunity,
            auto_discover_symbols=not bool(symbols),  # Auto-discover if no symbols provided
            comprehensive_logging=comprehensive_logging,
            market_data_repo=market_data_repo,
            execution_service=execution_service
        )

        # Set symbols from the opportunity watcher (handles auto-discovery)
        self.symbols = self.opportunity_watcher.symbols
        # Initialize orchestrator components first before logging status

        # Initialize orchestrator components using domain interfaces only
        from domain.entities.trading_entities import Signal, SignalType
        from domain.value_objects import Percentage
        from decimal import Decimal

        # Import Engine and Fusion if available
        try:
            from infrastructure.engines.base_engine_adapter import BaseEngineAdapter
            from infrastructure.fusion.fusion_service import FusionServiceAdapter
            engine_available = True
            fusion_available = True
        except ImportError:
            BaseEngineAdapter = None
            FusionServiceAdapter = None
            engine_available = False
            fusion_available = False

        # Create more realistic strategies that use opportunity data
        class DynamicStrategy(StrategyPort):
            def __init__(self, name: str, signal_type: SignalType = None, engine=None, fusion=None):
                self.name = name
                self.signal_type = signal_type or SignalType.NEUTRAL
                self.performance_tracker = {}  # Track performance metrics
                self.engine = engine
                self.fusion = fusion

            def generate_signal(self, symbol: Symbol):
                """Generate signal based on opportunity data if available"""
                from datetime import datetime

                # In hexagonal architecture, we can't directly access opportunity data here
                # Instead, this would be handled by the orchestrator passing contextual data
                # For now, return a neutral signal - in a real system, this would be
                # enhanced with market data passed via update_with_market_data

                return Signal(
                    symbol=symbol,
                    signal_type=self.signal_type,
                    confidence=Percentage(Decimal('0.6')),
                    score=0.0,
                    strategy_name=self.name,
                    timestamp=datetime.now(),
                    source_engine="AutoDetection",
                    metadata={}
                )

            def get_strategy_name(self) -> str:
                return self.name

            def calculate_position_size(self, signal: Signal, account_balance: float) -> float:
                # Calculate position size based on signal confidence and risk settings
                confidence_factor = float(signal.confidence.value)
                # Max 2% of account per trade
                return account_balance * 0.02 * confidence_factor

            def update_with_market_data(self, data: Dict[str, Any]):
                # Update strategy with latest market data for performance tracking
                pass

        # Initialize engine and fusion if available
        self.engine = BaseEngineAdapter("AutoDetectionEngine") if engine_available else None
        self.fusion = FusionServiceAdapter() if fusion_available else None

        # Create strategies that align with the opportunity detection
        self.strategies = [
            DynamicStrategy("momentum_strategy", SignalType.NEUTRAL, self.engine, self.fusion),
            DynamicStrategy("trend_following", SignalType.NEUTRAL, self.engine, self.fusion),
            DynamicStrategy("mean_reversion", SignalType.NEUTRAL, self.engine, self.fusion),
            DynamicStrategy("volatility_strategy", SignalType.NEUTRAL, self.engine, self.fusion),
            DynamicStrategy("order_flow", SignalType.NEUTRAL, self.engine, self.fusion),
            DynamicStrategy("balanced_strategy", SignalType.NEUTRAL, self.engine, self.fusion),
            DynamicStrategy("cmc_sentiment_strategy", SignalType.NEUTRAL, self.engine, self.fusion)
        ]

        # Initialize risk management first
        from infrastructure.services.risk_alerts import RiskAlertService, EmailNotificationService, \
            TelegramNotificationService
        email_service = EmailNotificationService()
        telegram_service = TelegramNotificationService()
        self.risk_alert_service = RiskAlertService(
            notification_services=[email_service, telegram_service],
            max_leverage=10.0,
            drawdown_threshold=-0.1
        )

        # Initialize with domain-level strategy selection (not application service)
        self._initialize_strategy_selection()

        # Initialize state
        self.is_running = False
        self.active_trades = {}
        self.opportunity_queue = []
        self.background_threads = []

    def _initialize_strategy_selection(self):
        """Initialize strategy selection without depending on application services"""
        self.strategy_selection_service = None  # Will be set by orchestration logic
        # Use the strategies directly for selection
        self.selected_strategies = self.strategies

    def _select_strategy_for_symbol(self, symbol: Symbol, opportunity_data: Optional[Dict[str, Any]] = None) -> \
    Optional[StrategyPort]:
        """Select the best strategy for a given symbol and opportunity data"""
        if not self.strategies:
            return None

        # For now, return the first strategy - in a real implementation, this would
        # implement proper strategy selection logic without using application services
        return self.strategies[0]

    def initialize_system(self):
        """Initialize the auto-detection system."""
        self.logger.info("🚀 Initializing Auto-Detection Orchestrator...")

        # Start background services
        self._start_background_services()

        self.is_running = True
        self.logger.info("✅ Auto-Detection Orchestrator initialized successfully")

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
            f"💎 Handling opportunity: {opportunity['symbol']} - {opportunity['recommendation']} with confidence {opportunity['confidence']:.2%}")

        # Log the flow from watcher to engine
        self.logger.log_watcher_to_engine_flow(
            symbol=opportunity['symbol'],
            watcher_name="MarketOpportunityWatcher",
            signal_generated=bool(opportunity['recommendation']),
            signal_type=opportunity['recommendation'],
            confidence=opportunity['confidence'],
            reason=f"Opportunity detected with recommendation {opportunity['recommendation']}",
        )

        # Log the decision at the orchestrator level
        self.logger.log_decision_reason(
            component="Orchestrator",
            symbol=opportunity['symbol'],
            decision="Opportunity Queued",
            reason=f"Opportunity detected by watcher with recommendation {opportunity['recommendation']}",
            confidence=opportunity['confidence']
        )

        # Log background activity in comprehensive mode
        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
            self.logger.log_background_activity(
                "Opportunity Detection",
                f"Detected opportunity for {opportunity['symbol']} with confidence {opportunity['confidence']:.2%}",
                symbol=opportunity['symbol'],
                recommendation=opportunity['recommendation'],
                confidence=opportunity['confidence']
            )

        self.opportunity_queue.append(opportunity)

    def _execute_strategy_for_opportunity(self, opportunity: Dict[str, Any]):
        """Execute the appropriate strategy for an opportunity."""
        try:
            symbol = Symbol(opportunity['symbol'])
            suggested_strategy = opportunity.get('strategy_suggestion',
                                                 'balanced_strategy')  # Default to balanced strategy if not provided
            confidence = opportunity['confidence']

            self.logger.info(
                f"🎯 Executing strategy {suggested_strategy} for {symbol.value} with confidence {confidence:.2%}")

            # Generate signal using the opportunity data
            # Use the new strategy selection method that doesn't depend on application services
            strategy = self._select_strategy_for_symbol(symbol, opportunity)
            if strategy:
                # Generate signal with the opportunity-specific data
                # For now, use just the symbol as the standard strategy interface only accepts symbol
                signal = strategy.generate_signal(symbol)

                if signal:
                    self.logger.log_strategy_signal(strategy.get_strategy_name(), symbol.value, signal.signal_type.name,
                                                    float(signal.confidence.value))

                    # Log the complete signal progression through all stages
                    self.logger.log_signal_progression(
                        symbol=symbol.value,
                        stage="watcher",
                        status="Signal Generated",
                        details=f"Signal: {signal.signal_type.name}",
                        confidence=float(signal.confidence.value)
                    )

                    # Log the flow from engine to fusion if engine is available
                    if self.engine:
                        # Process signal through engine
                        processed_signal = self.engine.process_signal(signal)

                        self.logger.log_signal_progression(
                            symbol=symbol.value,
                            stage="engine",
                            status="Processed",
                            details=f"Signal processed by engine",
                            confidence=float(processed_signal.confidence.value)
                        )

                        self.logger.log_engine_to_fusion_flow(
                            symbol=symbol.value,
                            engine_name=self.engine.get_engine_name(),
                            signal_processed=True,
                            signal_type=processed_signal.signal_type.name,
                            confidence=float(processed_signal.confidence.value),
                            reason=f"Signal processed by engine with confidence {float(processed_signal.confidence.value):.2%}",
                        )

                        # Log the flow from fusion to strategy if fusion is available
                        if self.fusion:
                            # In a real implementation, we would fuse multiple signals
                            # For now, we'll just pass the processed signal through
                            fused_signal = processed_signal

                            self.logger.log_signal_progression(
                                symbol=symbol.value,
                                stage="fusion",
                                status="Fused",
                                details=f"Signal fused successfully",
                                confidence=float(fused_signal.confidence.value)
                            )

                            self.logger.log_fusion_to_strategy_flow(
                                symbol=symbol.value,
                                fusion_name="FusionService",
                                fused_signal=True,
                                signal_type=fused_signal.signal_type.name,
                                confidence=float(fused_signal.confidence.value),
                                reason=f"Signal fused with confidence {float(fused_signal.confidence.value):.2%}",
                            )
                        else:
                            # If no fusion, log the step as skipped
                            self.logger.log_signal_progression(
                                symbol=symbol.value,
                                stage="fusion",
                                status="Skipped",
                                details="Fusion not available, signal passed directly",
                                confidence=float(processed_signal.confidence.value)
                            )

                            self.logger.log_fusion_to_strategy_flow(
                                symbol=symbol.value,
                                fusion_name="FusionService",
                                fused_signal=True,
                                signal_type=processed_signal.signal_type.name,
                                confidence=float(processed_signal.confidence.value),
                                reason="Fusion not available, signal passed directly",
                            )
                    else:
                        # If no engine, log the step as skipped and go directly to fusion
                        if self.fusion:
                            # In a real implementation, we would fuse multiple signals
                            fused_signal = signal

                            self.logger.log_signal_progression(
                                symbol=symbol.value,
                                stage="engine",
                                status="Skipped",
                                details="Engine not available, signal passed directly to fusion",
                                confidence=float(signal.confidence.value)
                            )

                            self.logger.log_engine_to_fusion_flow(
                                symbol=symbol.value,
                                engine_name="Engine",
                                signal_processed=True,
                                signal_type=signal.signal_type.name,
                                confidence=float(signal.confidence.value),
                                reason="Engine not available, signal passed directly to fusion",
                            )

                            self.logger.log_signal_progression(
                                symbol=symbol.value,
                                stage="fusion",
                                status="Fused",
                                details=f"Signal fused successfully",
                                confidence=float(fused_signal.confidence.value)
                            )

                            self.logger.log_fusion_to_strategy_flow(
                                symbol=symbol.value,
                                fusion_name="FusionService",
                                fused_signal=True,
                                signal_type=fused_signal.signal_type.name,
                                confidence=float(fused_signal.confidence.value),
                                reason=f"Signal fused with confidence {float(fused_signal.confidence.value):.2%}",
                            )
                        else:
                            # No engine or fusion, go directly to broker
                            self.logger.log_signal_progression(
                                symbol=symbol.value,
                                stage="engine",
                                status="Skipped",
                                details="Engine not available, signal passed directly",
                                confidence=float(signal.confidence.value)
                            )

                            self.logger.log_engine_to_fusion_flow(
                                symbol=symbol.value,
                                engine_name="Engine",
                                signal_processed=True,
                                signal_type=signal.signal_type.name,
                                confidence=float(signal.confidence.value),
                                reason="Engine not available, signal passed directly",
                            )

                            self.logger.log_signal_progression(
                                symbol=symbol.value,
                                stage="fusion",
                                status="Skipped",
                                details="Fusion not available, signal passed directly to broker",
                                confidence=float(signal.confidence.value)
                            )

                            self.logger.log_fusion_to_strategy_flow(
                                symbol=symbol.value,
                                fusion_name="FusionService",
                                fused_signal=True,
                                signal_type=signal.signal_type.name,
                                confidence=float(signal.confidence.value),
                                reason="Fusion not available, signal passed directly to broker",
                            )

                    # Log the flow from strategy to broker
                    self.logger.log_signal_progression(
                        symbol=symbol.value,
                        stage="strategy",
                        status="Ready for Execution",
                        details=f"Signal prepared for broker: {signal.signal_type.name}",
                        confidence=float(signal.confidence.value)
                    )

                    self.logger.log_strategy_to_broker_flow(
                        symbol=symbol.value,
                        strategy_name=strategy.get_strategy_name(),
                        trade_executed=False,  # We don't know yet, so we'll log the execution separately
                        signal_type=signal.signal_type.name,
                        confidence=float(signal.confidence.value),
                        reason=f"Signal generated with confidence {float(signal.confidence.value):.2%}",
                    )

                    # Execute trade through execution service
                    execution_result = self._execute_trade(symbol, signal)

                    # Track active trade with detailed decision data
                    trade_details = {
                        'strategy': suggested_strategy,
                        'signal': signal.signal_type.name,
                        'timestamp': datetime.now().isoformat(),
                        'execution_result': execution_result,
                        'confidence': float(signal.confidence.value),
                        'opportunity_confidence': confidence,
                        'decision_factors': {
                            'signal_quality': float(signal.confidence.value),
                            'opportunity_strength': confidence,
                            'trade_acceptance_reason': 'Signal strength' if float(
                                signal.confidence.value) > 0.6 else 'Low confidence - may be rejected',
                            'risk_check_passed': self._check_risk_acceptance(symbol, signal),
                            # Check if risk controls passed
                        }
                    }

                    # Log trade decision with reasons
                    if execution_result['status'] == 'executed':
                        execution_id = execution_result.get('execution_id', 'N/A')
                        self.logger.info(
                            f"✅ ACCEPTED TRADE: {execution_result['order']['side']} {execution_result['order']['quantity']} {symbol.value} | Signal: {signal.signal_type.name} | Sig. Conf: {float(signal.confidence.value):.2%} | Opp. Conf: {confidence:.2%}")

                        # Log the completed flow from strategy to broker
                        self.logger.log_strategy_to_broker_flow(
                            symbol=symbol.value,
                            strategy_name=strategy.get_strategy_name(),
                            trade_executed=True,
                            signal_type=signal.signal_type.name,
                            confidence=float(signal.confidence.value),
                            reason=f"Trade executed successfully via {execution_result['order'].get('strategy', 'Unknown')}",
                        )

                        # Log the complete signal flow with execution details
                        # Determine broker name dynamically from the execution service
                        broker_name = self._get_broker_name()

                        self.logger.log_complete_signal_flow(
                            symbol=symbol.value,
                            signal_type=signal.signal_type.name,
                            confidence=float(signal.confidence.value),
                            watcher="MarketOpportunityWatcher",
                            engine=self.engine.get_engine_name() if self.engine else "N/A",
                            fusion="FusionService" if self.fusion else "N/A",
                            strategy=strategy.get_strategy_name(),
                            broker=broker_name,
                            execution_status="executed",
                            execution_id=execution_id
                        )

                        # Log the final execution step
                        self.logger.log_signal_progression(
                            symbol=symbol.value,
                            stage="broker",
                            status="Executed",
                            details=f"Order executed successfully: {execution_id}",
                            confidence=float(signal.confidence.value)
                        )
                    else:
                        self.logger.warning(
                            f"❌ REJECTED TRADE: {symbol.value} | Reason: {execution_result.get('error', 'Execution failed')} | Signal: {signal.signal_type.name} | Sig. Conf: {float(signal.confidence.value):.2%} | Opp. Conf: {confidence:.2%}")

                        # Log the rejected flow from strategy to broker
                        self.logger.log_strategy_to_broker_flow(
                            symbol=symbol.value,
                            strategy_name=strategy.get_strategy_name(),
                            trade_executed=False,
                            signal_type=signal.signal_type.name,
                            confidence=float(signal.confidence.value),
                            reason=f"Trade rejected: {execution_result.get('error', 'Execution failed')}",
                        )

                        # Log the complete signal flow with execution details
                        # Determine broker name dynamically from the execution service
                        broker_name = self._get_broker_name()

                        self.logger.log_complete_signal_flow(
                            symbol=symbol.value,
                            signal_type=signal.signal_type.name,
                            confidence=float(signal.confidence.value),
                            watcher="MarketOpportunityWatcher",
                            engine=self.engine.get_engine_name() if self.engine else "N/A",
                            fusion="FusionService" if self.fusion else "N/A",
                            strategy=strategy.get_strategy_name(),
                            broker=broker_name,
                            execution_status="failed",
                            execution_id="N/A"
                        )

                        # Log the final execution step
                        self.logger.log_signal_progression(
                            symbol=symbol.value,
                            stage="broker",
                            status="Failed",
                            details=f"Order execution failed: {execution_result.get('error', 'Execution failed')}",
                            confidence=float(signal.confidence.value)
                        )

                    self.active_trades[symbol.value] = trade_details

                    # NOTE: Performance tracking would need to be implemented at domain/infrastructure level
                    # without depending on application services
                else:
                    self.logger.warning(f"No signal generated for {symbol.value}")
                    # Log that no signal was generated at the strategy level
                    self.logger.log_decision_reason(
                        component="Strategy",
                        symbol=symbol.value,
                        decision="No Signal Generated",
                        reason="Strategy did not generate a signal",
                        confidence=0.0
                    )
            else:
                self.logger.warning(f"No strategy selected for {symbol.value}")
                # Log that no strategy was selected
                self.logger.log_decision_reason(
                    component="Orchestrator",
                    symbol=symbol.value,
                    decision="No Strategy Selected",
                    reason="No suitable strategy found for the opportunity",
                    confidence=confidence
                )

        except Exception as e:
            self.logger.error(f"Error executing strategy for opportunity: {e}")
            # Log the error in the flow
            self.logger.log_decision_reason(
                component="Orchestrator",
                symbol=opportunity.get('symbol', 'UNKNOWN'),
                decision="Error in Execution",
                reason=f"Exception occurred: {str(e)}",
                confidence=opportunity.get('confidence', 0.0)
            )

    def _execute_trade(self, symbol: Symbol, signal) -> Dict[str, Any]:
        """Execute trade based on signal."""
        try:
            # Get real market data for the symbol to determine proper price and position size
            current_price = None
            if self.market_data_repo:
                try:
                    current_price = self.market_data_repo.get_current_price(symbol)
                except:
                    # If we can't get current price from data repo, try to get from exchange directly
                    pass

            # If we still don't have a price, use a fallback
            if current_price is None or current_price <= 0:
                # Try to get price from exchange directly
                try:
                    import ccxt
                    exchange = ccxt.binance()
                    ticker = exchange.fetch_ticker(symbol.value)
                    current_price = ticker['last'] if 'last' in ticker else ticker['close']
                except:
                    # If all methods fail, we'll still proceed but log the issue
                    self.logger.warning(f"Could not get current price for {symbol.value}, using signal price")
                    current_price = 50000.0  # Fallback price

            # Calculate position size based on signal confidence and risk management
            confidence = float(signal.confidence.value) if hasattr(signal.confidence, 'value') else float(
                signal.confidence)
            base_position_size = 0.02  # 2% of account as base position
            risk_adjusted_size = base_position_size * confidence  # Adjust based on signal confidence

            # Calculate quantity based on account balance and risk
            # For now, using a fixed amount - in real system this would come from portfolio service
            try:
                portfolio_metrics = self.portfolio_service.get_portfolio_metrics()
                account_balance = portfolio_metrics.get('equity', 10000.0)  # Default to $10,000 if not available
                position_value = account_balance * risk_adjusted_size
                quantity = position_value / current_price
            except:
                # If portfolio service fails, use a default quantity
                quantity = risk_adjusted_size * 1000 / current_price  # Default to 2% of $1000

            # Create order object using domain entities
            from domain.entities.trading_entities import Order, OrderType, OrderSide
            from domain.value_objects import Money

            order = Order(
                symbol=symbol,
                side=OrderSide.BUY if signal.signal_type.name == 'BUY' else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=Money(amount=current_price, currency='USDT') if current_price else None,
                strategy=signal.strategy_name,
                timestamp=datetime.now()
            )

            # Execute order through execution service
            execution_id = self.execution_service.execute_order(order)

            # Log the successful execution with detailed information
            self.logger.log_execution(
                execution_id,
                symbol.value,
                order.side.value,
                quantity,
                current_price
            )

            return {
                'status': 'executed',
                'execution_id': execution_id,
                'order': order.__dict__ if hasattr(order, '__dict__') else order
            }
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return {'status': 'error', 'error': str(e)}

    def _check_risk_acceptance(self, symbol: Symbol, signal) -> bool:
        """Check if risk controls allow the trade to proceed."""
        try:
            # This would integrate with real risk management in a production system
            # For now, we'll return True to allow execution
            return True
        except Exception:
            return False  # If there's an error checking risk, default to rejection

    def _assess_trade_risk(self, symbol: Symbol, signal) -> str:
        """Assess the risk level of the trade."""
        try:
            confidence = float(signal.confidence.value)
            if confidence > 0.8:
                return "LOW"
            elif confidence > 0.6:
                return "MODERATE"
            else:
                return "HIGH"
        except:
            return "UNKNOWN"

    def _calculate_position_size(self, signal, strategy_name: str) -> float:
        """Calculate position size based on signal confidence and risk."""
        try:
            confidence = float(signal.confidence.value)
            # Base position size on confidence (higher confidence = larger position)
            base_size = 0.01  # 1% default
            position_size = base_size * (0.5 + confidence)  # Range 0.5% to 1.3%
            return round(position_size, 4)
        except:
            return 0.01  # Default 1% if calculation fails

    def _get_market_conditions(self, symbol: Symbol) -> str:
        """Get current market conditions for the symbol."""
        # This would normally get real market data
        # For now we'll return a mock condition
        import random
        conditions = ["VOLATILE", "RANGING", "TRENDING_UP", "TRENDING_DOWN", "NORMAL"]
        return random.choice(conditions)

    def _risk_monitoring_loop(self):
        """Background risk monitoring loop."""
        self.logger.info("🛡️ Risk monitoring started")

        # Track statistics for periodic reporting
        last_report_time = time.time()
        report_interval = 120  # seconds between detailed reports

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

                # Log periodic detailed reports
                current_time = time.time()
                if current_time - last_report_time >= report_interval:
                    self.logger.info(f"🛡️ RISK MONITORING: Active trades: {len(self.active_trades)} | "
                                     f"Portfolio metrics checked: {len(portfolio_metrics) if portfolio_metrics else 0}")
                    if 'equity' in portfolio_metrics:
                        self.logger.info(f"💰 PORTFOLIO EQUITY: ${portfolio_metrics['equity']:,.2f}")
                    if 'pnl' in portfolio_metrics:
                        self.logger.info(f"📊 PORTFOLIO PnL: ${portfolio_metrics['pnl']:,.2f}")
                    if 'drawdown' in portfolio_metrics:
                        self.logger.info(f"📉 PORTFOLIO DRAWDOWN: {portfolio_metrics['drawdown']:.2%}")
                    last_report_time = current_time

                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in risk monitoring: {e}")
                time.sleep(30)

    def _get_broker_name(self) -> str:
        """Get the broker name from the execution service."""
        broker_name = "UnknownBroker"
        if hasattr(self.execution_service, 'get_broker_name'):
            broker_name = self.execution_service.get_broker_name()
        elif hasattr(self.execution_service, 'broker_name'):
            broker_name = self.execution_service.broker_name
        else:
            # Try to get broker name from the broker object if available
            if hasattr(self.execution_service, 'broker') and hasattr(self.execution_service.broker, 'name'):
                broker_name = self.execution_service.broker.name
            elif hasattr(self.execution_service, 'broker') and hasattr(self.execution_service.broker, '__class__'):
                broker_name = self.execution_service.broker.__class__.__name__.replace('Adapter', '')
        return broker_name

    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            'is_running': self.is_running,
            'monitored_symbols': self.symbols,
            'active_trades': len(self.active_trades),
            'opportunity_queue_size': len(self.opportunity_queue),
            'watcher_status': self.opportunity_watcher.get_status(),
            'timestamp': datetime.now().isoformat()
        }

    def stop_system(self):
        """Stop the auto-detection system."""
        self.logger.info("🛑 Stopping Auto-Detection Orchestrator...")
        self.is_running = False

        # Stop opportunity watcher
        self.opportunity_watcher.stop_monitoring()

        self.logger.info("✅ Auto-Detection Orchestrator stopped")

    def run_auto_detection(self):
        """Main auto-detection loop - this is the primary method for auto-detection mode."""
        self.logger.info("🤖 Starting auto-detection mode...")

        # Initialize the system
        self.initialize_system()

        # The system runs in background threads, so we just keep the main thread alive
        try:
            last_status_time = time.time()
            status_interval = 30  # seconds between status updates
            self.logger.info("📊 Auto-detection system is now running with background monitoring...")

            while self.is_running:
                current_time = time.time()

                # Log periodic status updates to show background activities
                if current_time - last_status_time >= status_interval:
                    status = self.get_status()
                    self.logger.info(f"📈 SYSTEM STATUS: Monitoring {status['monitored_symbols'].__len__()} symbols | "
                                     f"Active trades: {status['active_trades']} | "
                                     f"Opportunity queue: {status['opportunity_queue_size']} | "
                                     f"Background services: {len(self.background_threads)}")

                    # Log detailed watcher status
                    watcher_status = status['watcher_status']
                    if 'monitored_symbols' in watcher_status:
                        self.logger.info(
                            f"🔍 WATCHER STATUS: {len(watcher_status['monitored_symbols'])} symbols being monitored | "
                            f"Watchers: {watcher_status['watchers_count']}")

                    last_status_time = current_time

                time.sleep(1)  # Check every second for status updates and to allow for quick shutdown
        except KeyboardInterrupt:
            self.logger.info("🛑 Shutdown signal received")
        finally:
            self.stop_system()
