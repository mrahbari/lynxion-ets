"""Production trading orchestrator (relocated in E2.T5.3).

Moved verbatim out of ``run_trading_system.py`` so the entry point can become a
pure CLI router with no orchestration logic / no module-top infrastructure
imports. The orchestrator's internal logic is intentionally UNCHANGED (E3 scope):
same lifecycle, same four daemon background services, same ``stop_system``
semantics, same broker/data wiring expectations.

This module is constructed only through the composition root
(``production_orchestrator_factory``), which imports it lazily, so the heavy
deps it pulls (hyperopt via AutoRetuneOptimizer, dash via LiveDashboardAdapter)
are never loaded until production actually runs.
"""

import threading
import time
from datetime import datetime
from typing import Dict, Any, Callable

from shared.logger import EnhancedLogger
from domain.ports.data_ports import DataProviderPort
from domain.ports.execution_ports import ExecutionPort
from domain.ports.portfolio_ports import PortfolioManagementPort
from domain.ports.optimization_ports import IOptimizationService
from infrastructure.optimization.auto_retune_hyperopt import AutoRetuneOptimizer
from interface.reporting.live_dashboard import LiveDashboardAdapter


class ProductionTradingOrchestrator:
    """Production Trading Orchestrator following hexagonal architecture."""

    def __init__(self,
                 market_data_repo: DataProviderPort,
                 execution_service: ExecutionPort,
                 portfolio_service: PortfolioManagementPort,
                 optimization_service: IOptimizationService,
                 retune_interval_hours: int = 6,
                 evals_per_retune: int = 20):
        self.market_data_repo = market_data_repo
        self.execution_service = execution_service
        self.portfolio_service = portfolio_service
        self.optimization_service = optimization_service
        self.retune_interval_hours = retune_interval_hours
        self.evals_per_retune = evals_per_retune
        self.logger = EnhancedLogger("ProductionTradingOrchestrator")

        # Initialize core components
        self.auto_retune_optimizer = AutoRetuneOptimizer(
            strategy_name="crypto_breakout",
            performance_threshold=-5.0
        )
        # Initialize execution engine with proper parameters
        from infrastructure.execution.live_execution_engine import LiveExecutionEngine
        self.execution_engine = LiveExecutionEngine(
            broker_service=execution_service,
            data_loader=market_data_repo,  # market_data_repo acts as data_loader
            optimization_service=self.auto_retune_optimizer,
            execution_service=self.execution_service
        )
        self.dashboard = LiveDashboardAdapter(
            market_data_repo=market_data_repo,
            portfolio_service=portfolio_service
        )

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
        self.last_retune = datetime.now()
        self.active_strategies = {}
        self.active_symbols = set()
        self.background_threads = []
        # R1: periodic broker reconciliation cadence (seconds).
        self.reconcile_interval_seconds = 60

    def initialize_system(self):
        """Initialize the production trading system."""
        self.logger.info("Initializing Production Trading Orchestrator...")

        # No initialization needed for these services as they're configured in __init__

        # Start background services
        self._start_background_services()

        self.is_running = True
        self.logger.info("Production Trading Orchestrator initialized successfully")

    def _start_background_services(self):
        """Start all background services."""
        # Start auto-retune monitoring
        retune_thread = threading.Thread(target=self._auto_retune_monitor, daemon=True)
        retune_thread.start()
        self.background_threads.append(("auto_retune", retune_thread))

        # Start risk monitoring
        risk_thread = threading.Thread(target=self._risk_monitoring_loop, daemon=True)
        risk_thread.start()
        self.background_threads.append(("risk_monitoring", risk_thread))

        # Start performance monitoring
        perf_thread = threading.Thread(target=self._performance_monitoring_loop, daemon=True)
        perf_thread.start()
        self.background_threads.append(("performance_monitoring", perf_thread))

        # R1: start periodic broker reconciliation (halts on unrecoverable drift)
        recon_thread = threading.Thread(target=self._reconciliation_loop, daemon=True)
        recon_thread.start()
        self.background_threads.append(("broker_reconciliation", recon_thread))

        # Start dashboard
        dashboard_thread = self.dashboard.start_dashboard_thread()
        self.background_threads.append(("dashboard", dashboard_thread))

        self.logger.info(f"Started {len(self.background_threads)} background services")

    def _auto_retune_monitor(self):
        """Background thread to monitor and execute auto-retune."""
        self.logger.info("Auto-retune monitoring started")

        while self.is_running:
            try:
                current_time = datetime.now()
                if (current_time - self.last_retune).total_seconds() >= (self.retune_interval_hours * 3600):
                    self.logger.info(f"Running scheduled auto-retune at {current_time}")

                    # Run auto-retune for all active strategies
                    for strategy_name, config in self.active_strategies.items():
                        self.auto_retune_optimizer.run_auto_retune(
                            strategy_name=strategy_name,
                            symbols=config["symbols"],
                            risk_config=config["risk_config"]
                        )

                    self.last_retune = current_time
                    self.logger.info("Auto-retune cycle completed")

                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in auto-retune monitor: {e}")
                time.sleep(60)

    def _risk_monitoring_loop(self):
        """Background risk monitoring loop."""
        self.logger.info("Risk monitoring started")

        while self.is_running:
            try:
                # Get current positions and performance
                portfolio_metrics = self.portfolio_service.get_portfolio_metrics()

                # Check for risk violations. A critical breach now ENGAGES the
                # LIVE_EXECUTION_GUARD kill switch so the order path is actually halted
                # (previously this only emitted an alert and kept trading).
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
                    rep = svc.reconcile(broker, live_order_journal, halt_on_unrecoverable=True)
                    if rep.get("halted"):
                        self.logger.critical(f"🛑 RECONCILIATION HALT — unrecoverable drift: {rep['unrecoverable']}")
                        try:
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

    def _performance_monitoring_loop(self):
        """Background performance monitoring loop."""
        self.logger.info("Performance monitoring started")

        while self.is_running:
            try:
                # Get performance metrics
                performance_data = self.portfolio_service.get_performance_metrics()

                # Log performance metrics
                for strategy, metrics in performance_data.items():
                    self.logger.info(f"Strategy {strategy} performance: {metrics}")

                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {e}")
                time.sleep(300)

    def add_strategy(self, strategy_name: str, symbols: list, risk_config: Dict[str, Any] = None):
        """Add a strategy to the orchestrator."""
        if risk_config is None:
            risk_config = {
                "max_risk": 0.02,
                "atr_multiplier": 1.5,
                "use_dynamic_position": True
            }

        self.active_strategies[strategy_name] = {
            "symbols": symbols,
            "risk_config": risk_config,
            "status": "active"
        }

        for symbol in symbols:
            self.active_symbols.add(symbol)

        self.logger.info(f"Added strategy {strategy_name} for symbols: {symbols}")

    def remove_strategy(self, strategy_name: str):
        """Remove a strategy from the orchestrator."""
        if strategy_name in self.active_strategies:
            symbols = self.active_strategies[strategy_name]["symbols"]
            for symbol in symbols:
                self.active_symbols.discard(symbol)

            del self.active_strategies[strategy_name]
            self.logger.info(f"Removed strategy {strategy_name}")

    def run_production_trading(self,
                               data_fetcher: Callable[[], Dict[str, Any]],
                               strategy_name: str = "crypto_breakout",
                               risk_config: Dict[str, Any] = None):
        """Main production trading loop with auto-retune capability."""
        if risk_config is None:
            risk_config = {
                "max_risk": 0.02,
                "atr_multiplier": 1.5,
                "use_dynamic_position": True
            }

        self.add_strategy(strategy_name, list(self.active_symbols), risk_config)

        self.logger.info(f"Starting production trading for strategy: {strategy_name}")

        while self.is_running:
            try:
                # Fetch latest market data
                data_dict = data_fetcher()
                if not data_dict:
                    self.logger.warning("No data fetched, waiting...")
                    time.sleep(60)
                    continue

                # Execute trades based on current market conditions
                for asset_name, df in data_dict.items():
                    if asset_name in self.active_symbols:
                        # Execute trades through the execution engine
                        self.execution_engine.execute_strategy(
                            strategy_name=strategy_name,
                            symbol=asset_name,
                            data=df,
                            risk_config=risk_config
                        )

                # Sleep before next iteration
                time.sleep(1)  # Process data every second

            except Exception as e:
                self.logger.error(f"Error in production trading loop: {e}")
                time.sleep(5)  # Wait before continuing after error

    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "is_running": self.is_running,
            "active_strategies": len(self.active_strategies),
            "active_symbols": list(self.active_symbols),
            "last_retune": self.last_retune.isoformat(),
            "background_threads": len(self.background_threads),
            "timestamp": datetime.now().isoformat()
        }

    def stop_system(self):
        """Stop the production trading system."""
        self.logger.info("Stopping Production Trading Orchestrator...")
        self.is_running = False

        # The background threads are daemon threads, so they will stop automatically
        # when the main program exits

        self.logger.info("Production Trading Orchestrator stopped")
