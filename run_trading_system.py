"""Production Trading Orchestrator implementing hexagonal architecture."""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable
import json

from shared.logger import EnhancedLogger
from domain.ports.data_ports import DataProviderPort
from domain.ports.execution_ports import ExecutionPort
from domain.ports.portfolio_ports import PortfolioManagementPort
from domain.ports.optimization_ports import IOptimizationService
from infrastructure.services.risk_alerts import RiskAlertService
from infrastructure.execution.live_execution_engine import LiveExecutionEngine
from infrastructure.adapters.live_dashboard import LiveDashboardAdapter
from infrastructure.optimization.auto_retune_hyperopt import AutoRetuneOptimizer


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
        from infrastructure.services.risk_alerts import RiskAlertService, EmailNotificationService, TelegramNotificationService
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


# Standalone function for backward compatibility
def run_production_orchestrator(data_fetcher, strategy_name="crypto_breakout",
                               risk_config=None, retune_interval_hours=6):
    """Standalone function to run the production orchestrator."""
    # Create mock implementations for standalone execution
    from infrastructure.data.data_adapters import MockDataProviderAdapter
    from domain.ports.execution_ports import ExecutionPort
    from domain.ports.portfolio_ports import PortfolioManagementPort
    from domain.ports.optimization_ports import IOptimizationService

    # Create mock implementations since the actual implementations may not exist yet
    class MockExecutionService(ExecutionPort):
        def execute_order(self, order):
            print(f"Mock execution of order: {order}")
            return "mock_execution_id"

        def cancel_order(self, order_id: str) -> bool:
            print(f"Mock cancellation of order: {order_id}")
            return True

        def get_execution_status(self, execution_id: str) -> str:
            return "filled"

    class MockPortfolioService(PortfolioManagementPort):
        def calculate_allocation(self, total_capital: float, symbols):
            from domain.value_objects import Symbol, Percentage
            return {sym: total_capital/len(symbols) if symbols else 0 for sym in symbols}

        def rebalance_portfolio(self, target_allocations):
            return []

        def get_portfolio_metrics(self):
            return {"sharpe_ratio": 1.0, "max_drawdown": -0.05, "total_return": 0.1}

    class MockOptimizationService(IOptimizationService):
        def optimize_strategy(self, strategy_name, data, parameters):
            return {"status": "success", "best_params": {}}

        def get_optimized_parameters(self, strategy_name, symbol):
            return {}

        def save_optimized_parameters(self, strategy_name, symbol, parameters):
            pass

    # Create mock implementations for standalone execution
    market_data_repo = MockDataProviderAdapter()
    execution_service = MockExecutionService()
    portfolio_service = MockPortfolioService()
    optimization_service = MockOptimizationService()

    # Create orchestrator
    orchestrator = ProductionTradingOrchestrator(
        market_data_repo=market_data_repo,
        execution_service=execution_service,
        portfolio_service=portfolio_service,
        optimization_service=optimization_service
    )

    # Initialize system
    orchestrator.initialize_system()

    # Run production trading
    # Note: The orchestrator.run_production_trading method is called differently in the class
    # Let's call the run_production_trading method directly
    orchestrator.run_production_trading(
        data_fetcher=data_fetcher,
        strategy_name=strategy_name,
        risk_config=risk_config
    )


import sys
import argparse


def create_parser():
    """Create argument parser for the trading system."""
    parser = argparse.ArgumentParser(
        description="Hedge Fund Trading System - Production-Ready Algorithmic Trading Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run optimization for a specific strategy/symbol
  python run_trading_system.py --mode optimize --strategy crypto_breakout --symbol BTC/USDT

  # Run backtest with optimized parameters
  python run_trading_system.py --mode backtest --strategy crypto_breakout --symbol BTC/USDT --use-optimized-params

  # Run auto-retune on multiple symbols
  python run_trading_system.py --mode retune --strategy crypto_breakout --symbols BTC/USDT,ETH/USDT,SOL/USDT

  # Monitor system performance
  python run_trading_system.py --mode monitor

  # Run in production mode (with all features enabled)
  python run_trading_system.py --mode production

  # Test configuration
  python run_trading_system.py --mode config-test
        """
    )

    parser.add_argument(
        "--mode",
        choices=["optimize", "backtest", "retune", "monitor", "production", "config-test"],
        default="optimize",
        help="Operation mode to run (default: optimize)"
    )

    parser.add_argument(
        "--strategy",
        default="crypto_breakout",
        help="Trading strategy to use (default: crypto_breakout)"
    )

    parser.add_argument(
        "--symbol",
        help="Trading pair symbol (e.g., BTC/USDT)"
    )

    parser.add_argument(
        "--symbols",
        help="Comma-separated list of symbols (e.g., BTC/USDT,ETH/USDT)"
    )

    parser.add_argument(
        "--timeframe",
        default="1h",
        help="Timeframe for data (default: 1h)"
    )

    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )

    parser.add_argument(
        "--max-evals",
        type=int,
        default=100,
        help="Maximum number of hyperopt evaluations (default: 100)"
    )

    parser.add_argument(
        "--use-optimized-params",
        action="store_true",
        help="Use previously optimized parameters instead of defaults"
    )

    parser.add_argument(
        "--days-back",
        type=int,
        default=30,
        help="Number of days of historical data to use (default: 30)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for log files (default: logs)"
    )

    return parser


if __name__ == "__main__":
    # Parse command line arguments
    parser = create_parser()
    args = parser.parse_args()

    # Handle --help by just showing the help text
    if '--help' in sys.argv or '-h' in sys.argv:
        parser.print_help()
        sys.exit(0)

    print(f"🚀 Starting Production Trading Orchestrator in {args.mode} mode...")

    def sample_data_fetcher():
        """Sample data fetcher for testing."""
        import pandas as pd
        import numpy as np
        timestamps = pd.date_range(start='2023-01-01', periods=100, freq='1min')
        prices = 2000 + np.cumsum(np.random.randn(100) * 0.1)
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices + np.random.randn(100) * 0.05,
            'high': prices + abs(np.random.randn(100)) * 0.1,
            'low': prices - abs(np.random.randn(100)) * 0.1,
            'close': prices,
            'volume': np.abs(np.random.randn(100)) * 100,
            'volatility': np.abs(np.random.randn(100)) * 0.1
        })
        return {"XAUUSD": df, "BTCUSD": df.copy()}

    risk_config = {
        "max_risk": 0.02,
        "atr_multiplier": 1.5,
        "use_dynamic_position": True
    }

    print("📊 Running production orchestrator with sample data...")
    run_production_orchestrator(
        data_fetcher=sample_data_fetcher,
        strategy_name=args.strategy,
        risk_config=risk_config,
        retune_interval_hours=1
    )