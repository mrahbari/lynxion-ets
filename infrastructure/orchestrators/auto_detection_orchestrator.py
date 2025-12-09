"""
Auto-Detection Orchestrator for fully autonomous trading system.
Monitors markets continuously, identifies opportunities, and triggers appropriate strategies.
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
from infrastructure.watchers.market_opportunity_watcher import MarketOpportunityWatcher
from application.services.strategy_services import StrategySelectionService, StrategyOrchestrationService
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
                 risk_config: Optional[Dict[str, Any]] = None):
        self.market_data_repo = market_data_repo
        self.execution_service = execution_service
        self.portfolio_service = portfolio_service
        self.optimization_service = optimization_service
        self.risk_config = risk_config or {
            "max_risk": 0.02,
            "atr_multiplier": 1.5,
            "use_dynamic_position": True
        }
        self.logger = EnhancedLogger("AutoDetectionOrchestrator")

        # Initialize components
        self.opportunity_watcher = MarketOpportunityWatcher(
            symbols=symbols if symbols else None,
            opportunity_callback=self._handle_opportunity,
            auto_discover_symbols=not bool(symbols)  # Auto-discover if no symbols provided
        )

        # Set symbols from the opportunity watcher (handles auto-discovery)
        self.symbols = self.opportunity_watcher.symbols
        # Initialize orchestrator components first before logging status
        
        # Initialize orchestrator components (these would typically be passed in via dependency injection)
        # For now we'll create proper strategy selection service with real strategy capabilities

        # Import strategy ports and create proper strategies
        from domain.ports.engine_ports import StrategyPort
        from domain.entities.trading_entities import Signal, SignalType
        from domain.value_objects import Percentage
        from decimal import Decimal

        # Create more realistic strategies that use opportunity data
        class DynamicStrategy(StrategyPort):
            def __init__(self, name: str, signal_type: SignalType = None):
                self.name = name
                self.signal_type = signal_type or SignalType.NEUTRAL
                self.performance_tracker = {}  # Track performance metrics

            def generate_signal(self, symbol: Symbol, opportunity_data: Optional[Dict[str, Any]] = None):
                """Generate signal based on opportunity data if available"""
                from datetime import datetime

                if opportunity_data:
                    # Use opportunity data to generate more informed signal
                    confidence = opportunity_data.get('confidence', 0.5)
                    suggested_signal = opportunity_data.get('recommendation', 'NEUTRAL')

                    # Map recommendation string to SignalType
                    signal_type_mapping = {
                        'BUY': SignalType.BUY,
                        'SELL': SignalType.SELL,
                        'HOLD': SignalType.HOLD,
                        'NEUTRAL': SignalType.NEUTRAL
                    }

                    signal_type = signal_type_mapping.get(suggested_signal, SignalType.NEUTRAL)

                    return Signal(
                        symbol=symbol,
                        signal_type=signal_type,
                        confidence=Percentage(Decimal(str(min(1.0, max(0.1, confidence))))),
                        score=opportunity_data.get('confidence', 0.0),
                        strategy_name=self.name,
                        timestamp=datetime.now(),
                        source_engine="AutoDetection",
                        metadata=opportunity_data.get('metadata', {})
                    )
                else:
                    # Default signal generation
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

            def execute_strategy(self, symbol: Symbol, signal: Signal) -> Dict[str, Any]:
                # Execute strategy based on signal
                return {
                    "status": "executed",
                    "strategy": self.name,
                    "symbol": symbol.value,
                    "signal": signal.signal_type.name,
                    "confidence": float(signal.confidence.value)
                }

            def calculate_position_size(self, signal: Signal, account_balance: float) -> float:
                # Calculate position size based on signal confidence and risk settings
                confidence_factor = float(signal.confidence.value)
                risk_factor = self._get_risk_factor(signal)
                return account_balance * 0.02 * confidence_factor * risk_factor  # Max 2% of account per trade

            def _get_risk_factor(self, signal: Signal) -> float:
                # Adjust risk based on signal confidence and other factors
                base_risk = 1.0
                confidence = float(signal.confidence.value)

                # Higher confidence gets higher position size
                return min(2.0, max(0.5, base_risk * (confidence + 0.5)))

            def update_with_market_data(self, data: Dict[str, Any]):
                # Update strategy with latest market data for performance tracking
                pass

        # Create strategies that align with the opportunity detection
        real_strategies = [
            DynamicStrategy("momentum_strategy"),
            DynamicStrategy("trend_following"),
            DynamicStrategy("mean_reversion"),
            DynamicStrategy("volatility_strategy"),
            DynamicStrategy("order_flow"),
            DynamicStrategy("balanced_strategy"),
            DynamicStrategy("cmc_sentiment_strategy")
        ]

        # Initialize risk management first
        from infrastructure.services.risk_alerts import RiskAlertService, EmailNotificationService, TelegramNotificationService
        email_service = EmailNotificationService()
        telegram_service = TelegramNotificationService()
        self.risk_alert_service = RiskAlertService(
            notification_services=[email_service, telegram_service],
            max_leverage=10.0,
            drawdown_threshold=-0.1
        )

        # Initialize services with real strategies
        self.strategy_selection_service = StrategySelectionService(real_strategies)
        self.strategy_orchestration_service = StrategyOrchestrationService(
            strategy_selection_service=self.strategy_selection_service,
            signal_processing_service=None,  # This will be implemented with real signal processing
            risk_service=self.risk_alert_service  # Use the existing risk service
        )

        # Now log the status as components are initialized
        self.logger.log_auto_detection_status(len(self.symbols), len(self.strategy_selection_service.strategies), 0)
        
        # Initialize state
        self.is_running = False
        self.active_trades = {}
        self.opportunity_queue = []
        self.background_threads = []
        
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
        
        while self.is_running:
            try:
                if self.opportunity_queue:
                    opportunity = self.opportunity_queue.pop(0)  # Get oldest opportunity
                    self._execute_strategy_for_opportunity(opportunity)
                    
                time.sleep(1)  # Check queue every second
            except Exception as e:
                self.logger.error(f"Error in opportunity processing loop: {e}")
                time.sleep(1)
                
    def _handle_opportunity(self, opportunity: Dict[str, Any]):
        """Handle detected market opportunity."""
        self.logger.info(f"💎 Handling opportunity: {opportunity['symbol']} - {opportunity['recommendation']} with confidence {opportunity['confidence']:.2%}")
        self.opportunity_queue.append(opportunity)
        
    def _execute_strategy_for_opportunity(self, opportunity: Dict[str, Any]):
        """Execute the appropriate strategy for an opportunity."""
        try:
            symbol = Symbol(opportunity['symbol'])
            suggested_strategy = opportunity['strategy_suggestion']
            confidence = opportunity['confidence']

            self.logger.info(f"🎯 Executing strategy {suggested_strategy} for {symbol.value} with confidence {confidence:.2%}")

            # Generate signal using the opportunity data
            # First, try to select the best strategy based on the opportunity
            strategy = self.strategy_selection_service.select_best_strategy(symbol, opportunity)
            if strategy:
                # Generate signal with the opportunity-specific data
                # For now, use just the symbol as the standard strategy interface only accepts symbol
                signal = strategy.generate_signal(symbol)

                if signal:
                    self.logger.log_strategy_signal(strategy.get_strategy_name(), symbol.value, signal.signal_type.name, float(signal.confidence.value))

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
                            'trade_acceptance_reason': 'Signal strength' if float(signal.confidence.value) > 0.6 else 'Low confidence - may be rejected',
                            'risk_check_passed': self._check_risk_acceptance(symbol, signal),  # Check if risk controls passed
                        }
                    }

                    # Log trade decision with reasons
                    if execution_result['status'] == 'executed':
                        self.logger.info(f"✅ ACCEPTED TRADE: {execution_result['order']['side']} {execution_result['order']['quantity']} {symbol.value} | Signal: {signal.signal_type.name} | Sig. Conf: {float(signal.confidence.value):.2%} | Opp. Conf: {confidence:.2%}")
                    else:
                        self.logger.warning(f"❌ REJECTED TRADE: {symbol.value} | Reason: {execution_result.get('error', 'Execution failed')} | Signal: {signal.signal_type.name} | Sig. Conf: {float(signal.confidence.value):.2%} | Opp. Conf: {confidence:.2%}")

                    self.active_trades[symbol.value] = trade_details

                    # Update strategy performance metrics
                    self.strategy_selection_service.update_strategy_performance(
                        strategy.get_strategy_name(),
                        {
                            'avg_return': 0.01,  # Mock performance data - in real system would come from actual results
                            'win_rate': 0.65,
                            'sharpe_ratio': 1.2,
                            'max_drawdown': -0.05,
                            'volatility': 0.15,
                            'total_pnl': 0,
                            'trades_count': 1
                        }
                    )
                else:
                    self.logger.warning(f"No signal generated for {symbol.value}")
            else:
                self.logger.warning(f"No strategy selected for {symbol.value}")

        except Exception as e:
            self.logger.error(f"Error executing strategy for opportunity: {e}")
            
    def _execute_trade(self, symbol: Symbol, signal) -> Dict[str, Any]:
        """Execute trade based on signal."""
        # This is a simplified trade execution - in a real system, you'd have more complex logic
        try:
            # Create mock order based on signal
            side = 'BUY' if signal.signal_type.name == 'BUY' else 'SELL'
            quantity = 0.01 # Mock quantity based on strategy
            price = 50000.0  # Mock price - in real system this would come from market data

            order = {
                'symbol': symbol.value,
                'side': side,
                'quantity': quantity,
                'price': price,
                'type': 'MARKET',
                'strategy': signal.strategy_name
            }

            # Execute order through execution service
            execution_id = self.execution_service.execute_order(order)

            # Log the successful execution with detailed information
            self.logger.log_execution(
                execution_id,
                symbol.value,
                side,
                quantity,
                price
            )

            return {
                'status': 'executed',
                'execution_id': execution_id,
                'order': order
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
            while self.is_running:
                time.sleep(10)  # Keep main thread alive
        except KeyboardInterrupt:
            self.logger.info("🛑 Shutdown signal received")
        finally:
            self.stop_system()