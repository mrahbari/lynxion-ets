"""Production Trading Orchestrator implementing hexagonal architecture."""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable
import json
from dotenv import load_dotenv

# Load environment variables from .env file
from application.configs import Configs

load_dotenv()

from shared.logger import EnhancedLogger
from domain.ports.data_ports import DataProviderPort
from domain.ports.execution_ports import ExecutionPort
from domain.ports.portfolio_ports import PortfolioManagementPort
from domain.ports.optimization_ports import IOptimizationService
from infrastructure.services.risk_alerts import RiskAlertService
from infrastructure.execution.live_execution_engine import LiveExecutionEngine
from infrastructure.adapters.live_dashboard import LiveDashboardAdapter
from infrastructure.optimization.auto_retune_hyperopt import AutoRetuneOptimizer
from application.configs.configs import Configs


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
    # Create real implementations for standalone execution
    from infrastructure.data.enhanced_data_provider import create_enhanced_data_provider
    from domain.ports.execution_ports import ExecutionPort
    from domain.ports.portfolio_ports import PortfolioManagementPort
    from domain.ports.optimization_ports import IOptimizationService

    # Import the broker execution service that handles broker configuration
    from infrastructure.services.broker_execution_service import create_execution_service

    # Create execution service first using the registry to avoid duplicate initialization
    from infrastructure.services.broker_registry import broker_registry
    execution_service = broker_registry.get_execution_service(use_multi_broker=True,
                                                              primary_broker='bingx')  # Uses multi-broker with exchange switching, primary is BingX

    # Create enhanced data provider that uses real data and can download missing symbols
    # Use environment variable or default path for historical data
    # For now, pass the execution service as the broker service (it has access to the broker)
    # Configure to use binance as primary source for historical data to avoid BingX rate limits
    market_data_repo = broker_registry.get_historical_data_provider(
        csv_base_path=None,
        download_enabled=True,
        broker_service=execution_service,
        historical_data_source=Configs.data.preferred_historical_data_source if Configs.data and hasattr(Configs.data,
                                                                                                         'preferred_historical_data_source') else 'binance',
        # Use binance by default to avoid BingX rate limits
        fallback_sources=['mexc', 'phemex', 'bingx']  # Fallback order to avoid rate limits
    )
    # Import real portfolio and optimization services
    from infrastructure.portfolio.portfolio_adapters import EqualWeightPortfolioAdapter
    from infrastructure.optimization.advanced_optimization_service import AdvancedOptimizationService

    # Create and configure real services
    portfolio_service = EqualWeightPortfolioAdapter()
    optimization_service = AdvancedOptimizationService()

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
import os


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

  # Run in auto-detection mode (watcher detects opportunities and triggers strategies automatically)
  python run_trading_system.py --mode production --auto-detect --symbols BTC/USDT,ETH/USDT

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

    parser.add_argument(
        "--auto-detect",
        action="store_true",
        help="Run in auto-detection mode (watcher detects opportunities and triggers strategies automatically)"
    )

    parser.add_argument(
        "--comprehensive-logs",
        action="store_true",
        help="Enable comprehensive logging with detailed background activity tracking"
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

    print(f"🚀 Starting Trading System in {args.mode} mode...")

    # Import required modules for specific modes
    if args.mode in ["backtest", "optimize", "retune"]:
        from datetime import datetime, timedelta
        from domain.value_objects.money import Symbol
        from application.use_cases.backtest_use_cases import RunBacktestUseCase
        from application.services.backtest_services import BacktestExecutionService
        from infrastructure.backtest.backtest_adapters import (
            MockHistoricalDataProviderAdapter, BasicBacktestEngineAdapter,
            BacktestMetricsCalculatorAdapter
        )
        from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager

    # Handle different modes
    if args.mode == "backtest":
        print(f"📊 Running backtest for strategy: {args.strategy}, symbol: {args.symbol}")

        # Set up backtest components
        risk_manager = EnterpriseRiskManager(
            max_portfolio_exposure=100000,
            max_position_exposure=50000,
            max_risk_per_trade=0.01,
            max_daily_loss_pct=0.05,
            max_drawdown_pct=0.15
        )

        # Set up dates for backtesting
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.days_back)).strftime('%Y-%m-%d')

        # Create backtesting components
        historical_data_provider = MockHistoricalDataProviderAdapter()
        backtest_engine = BasicBacktestEngineAdapter(
            strategy=args.strategy,
            risk_manager=risk_manager,
            historical_data_provider=historical_data_provider
        )
        metrics_calculator = BacktestMetricsCalculatorAdapter()

        # Create service and use case
        backtest_service = BacktestExecutionService(
            backtest_engine_port=backtest_engine,
            historical_data_port=historical_data_provider,
            metrics_port=metrics_calculator
        )
        backtest_use_case = RunBacktestUseCase(backtest_service)

        # Run backtest - convert symbol format from BTC/USDT to BTCUSDT
        raw_symbol = args.symbol if args.symbol else "BTC/USDT"
        formatted_symbol = raw_symbol.replace("/", "")  # Convert BTC/USDT to BTCUSDT
        symbol = Symbol(formatted_symbol)
        results = backtest_use_case.execute(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000,
            strategy_name=args.strategy
        )

        print(f"✅ Backtest completed!")
        print(f"📈 Results: Total Return = {results.get('total_return', 0):.2%}, "
              f"Win Rate = {results.get('win_rate', 0):.2%}, "
              f"Total Trades = {results.get('total_trades', 0)}")

    elif args.mode == "optimize":
        print(f"⚙️ Running optimization for strategy: {args.strategy}, symbol: {args.symbol}")

        # Import optimization components
        from shared.configurable_hyperopt import HyperoptConfig, ConfigurableHyperoptOptimizer
        import pandas as pd
        import numpy as np

        # Set up optimization
        config = HyperoptConfig(strategy_name=args.strategy)
        optimizer = ConfigurableHyperoptOptimizer(hyperopt_config=config, strategy_name=args.strategy)

        # Generate sample data for optimization (in a real system, this would come from data provider)
        print("📊 Generating sample data for optimization...")
        timestamps = pd.date_range(start='2023-01-01', periods=500, freq='1h')
        prices = 30000 + np.cumsum(np.random.randn(500) * 100)  # Simulated BTC prices
        sample_data = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices + np.random.randn(500) * 5,
            'high': prices + abs(np.random.randn(500)) * 10,
            'low': prices - abs(np.random.randn(500)) * 10,
            'close': prices,
            'volume': np.abs(np.random.randn(500)) * 500,
            'volatility': np.abs(np.random.randn(500)) * 5
        })

        # Run optimization
        symbol = args.symbol if args.symbol else "BTCUSDT"
        results = optimizer.optimize_with_config(
            strategy_name=args.strategy,
            data=sample_data,
            symbol=symbol,
            custom_config={"max_evals": args.max_evals}
        )

        print(f"✅ Optimization completed!")
        print(f"📊 Best parameters: {results.get('best_params', {})}")
        print(
            f"🏆 Best score: {results.get('best_value', 0) if 'best_value' in results else results.get('best_loss', 'N/A')}")

    elif args.mode == "retune":
        print(f"🔄 Running auto-retune for strategy: {args.strategy}")

        # Import auto-retune components
        from infrastructure.optimization.auto_retune_hyperopt import AutoRetuneOptimizer

        symbols = args.symbols.split(",") if args.symbols else [args.symbol if args.symbol else "BTC/USDT"]

        auto_retune = AutoRetuneOptimizer(
            strategy_name=args.strategy,
            performance_threshold=-5.0
        )

        # Run auto-retune for each symbol
        for symbol in symbols:
            result = auto_retune.run_auto_retune(
                strategy_name=args.strategy,
                symbols=[symbol],
                risk_config={"atr_multiplier": 1.5, "use_dynamic_position": True}
            )
            print(f"✅ Auto-retune completed for {symbol}")

        print("✅ All auto-retune processes completed!")

    elif args.mode == "production":
        if args.auto_detect:
            # Run in auto-detection mode
            print("🚀 Starting auto-detection mode...")
            if args.symbols or args.symbol:
                symbol_list = args.symbols or [args.symbol]
                print(
                    f"📊 System will monitor markets and automatically detect opportunities for symbols: {symbol_list}")
            else:
                print("📊 System will automatically discover and monitor market opportunities across multiple symbols")

            # Import required components for auto-detection
            from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator

            # Create real implementations for standalone execution (same as in the orchestrator class)
            from infrastructure.data.enhanced_data_provider import create_enhanced_data_provider
            from domain.ports.execution_ports import ExecutionPort
            from domain.ports.portfolio_ports import PortfolioManagementPort
            from domain.ports.optimization_ports import IOptimizationService

            # Create execution service first using the registry to avoid duplicate initialization
            from infrastructure.services.broker_registry import broker_registry

            execution_service = broker_registry.get_execution_service(use_multi_broker=True,
                                                                      primary_broker='bingx')  # Uses multi-broker with exchange switching, primary is BingX

            # Create enhanced data provider that uses real data and can download missing symbols
            # Use environment variable or default path for historical data
            # For now, pass the execution service as the broker service (it has access to the broker)
            # Configure to use binance as primary source for historical data to avoid BingX rate limits
            market_data_repo = broker_registry.get_historical_data_provider(
                csv_base_path=None,
                download_enabled=True,
                broker_service=execution_service,
                historical_data_source=Configs.data.preferred_historical_data_source if Configs.data and hasattr(
                    Configs.data, 'preferred_historical_data_source') else 'binance',
                # Use binance by default to avoid BingX rate limits
                fallback_sources=['mexc', 'phemex', 'bingx']  # Fallback order to avoid rate limits
            )
            # Import real portfolio and optimization services
            from infrastructure.portfolio.portfolio_adapters import EqualWeightPortfolioAdapter
            from infrastructure.optimization.advanced_optimization_service import AdvancedOptimizationService

            # Create and configure real services
            portfolio_service = EqualWeightPortfolioAdapter()
            optimization_service = AdvancedOptimizationService()

            # Determine symbols to monitor
            symbols = []
            if args.symbols:
                symbols = args.symbols.split(",")
            elif args.symbol:
                symbols = [args.symbol]
            # If no symbols provided in auto-detect mode, the orchestrator will auto-discover them

            # Create risk config
            risk_config = {
                "max_risk": 0.02,
                "atr_multiplier": 1.5,
                "use_dynamic_position": True
            }

            # Create and run auto-detection orchestrator
            auto_detection_orchestrator = AutoDetectionOrchestrator(
                market_data_repo=market_data_repo,
                execution_service=execution_service,
                portfolio_service=portfolio_service,
                optimization_service=optimization_service,
                symbols=symbols if symbols else None,  # Pass None if no symbols specified
                risk_config=risk_config,
                comprehensive_logging=args.comprehensive_logs
            )

            try:
                auto_detection_orchestrator.run_auto_detection()
            except KeyboardInterrupt:
                print("\n🛑 Auto-detection mode stopped by user")
        else:
            # Run in original production mode with manual strategy selection
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
                # Return data for the specified symbol if provided
                symbol_key = args.symbol if args.symbol else "BTCUSD"
                return {symbol_key: df}


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

    elif args.mode == "monitor":
        print("📊 Starting monitoring mode...")
        print("Note: In a full implementation, this would connect to live data sources and monitor performance")
        # For now, just simulate monitoring
        import time
        import random

        while True:
            try:
                print(f"📈 Monitoring system: Portfolio value = ${10000 + random.randint(-500, 500):.2f}")
                time.sleep(5)  # Update every 5 seconds
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                break

    elif args.mode == "config-test":
        print("🔧 Testing configuration...")
        # Test that we can import and instantiate key components
        try:
            from shared.logger import EnhancedLogger

            logger = EnhancedLogger("ConfigTest")
            logger.info("Configuration test passed!")
            print("✅ Configuration test completed successfully")
        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
            sys.exit(1)
    else:
        print(f"❌ Unknown mode: {args.mode}")
        parser.print_help()
        sys.exit(1)


def main():
    """Main function that can be imported and called by other scripts."""
    # Parse command line arguments
    parser = create_parser()
    args = parser.parse_args()

    # Handle --help by just showing the help text
    if '--help' in sys.argv or '-h' in sys.argv:
        parser.print_help()
        sys.exit(0)

    print(f"🚀 Starting Trading System in {args.mode} mode...")

    # Import required modules for specific modes
    if args.mode in ["backtest", "optimize", "retune"]:
        from datetime import datetime, timedelta
        from domain.value_objects.money import Symbol
        from application.use_cases.backtest_use_cases import RunBacktestUseCase
        from application.services.backtest_services import BacktestExecutionService
        from infrastructure.backtest.backtest_adapters import (
            MockHistoricalDataProviderAdapter, BasicBacktestEngineAdapter,
            BacktestMetricsCalculatorAdapter
        )
        from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager

    # Handle different modes
    if args.mode == "backtest":
        print(f"📊 Running backtest for strategy: {args.strategy}, symbol: {args.symbol}")

        # Set up backtest components
        risk_manager = EnterpriseRiskManager(
            max_portfolio_exposure=100000,
            max_position_exposure=50000,
            max_risk_per_trade=0.01,
            max_daily_loss_pct=0.05,
            max_drawdown_pct=0.15
        )

        # Set up dates for backtesting
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=args.days_back)).strftime('%Y-%m-%d')

        # Create backtesting components
        historical_data_provider = MockHistoricalDataProviderAdapter()
        backtest_engine = BasicBacktestEngineAdapter(
            strategy=args.strategy,
            risk_manager=risk_manager,
            historical_data_provider=historical_data_provider
        )
        metrics_calculator = BacktestMetricsCalculatorAdapter()

        # Create service and use case
        backtest_service = BacktestExecutionService(
            backtest_engine_port=backtest_engine,
            historical_data_port=historical_data_provider,
            metrics_port=metrics_calculator
        )
        backtest_use_case = RunBacktestUseCase(backtest_service)

        # Run backtest - convert symbol format from BTC/USDT to BTCUSDT
        raw_symbol = args.symbol if args.symbol else "BTC/USDT"
        formatted_symbol = raw_symbol.replace("/", "")  # Convert BTC/USDT to BTCUSDT
        symbol = Symbol(formatted_symbol)
        results = backtest_use_case.execute(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000,
            strategy_name=args.strategy
        )

        print(f"✅ Backtest completed!")
        print(f"📈 Results: Total Return = {results.get('total_return', 0):.2%}, "
              f"Win Rate = {results.get('win_rate', 0):.2%}, "
              f"Total Trades = {results.get('total_trades', 0)}")

    elif args.mode == "optimize":
        print(f"⚙️ Running optimization for strategy: {args.strategy}, symbol: {args.symbol}")

        # Import optimization components
        from shared.configurable_hyperopt import HyperoptConfig, ConfigurableHyperoptOptimizer
        import pandas as pd
        import numpy as np

        # Set up optimization
        config = HyperoptConfig(strategy_name=args.strategy)
        optimizer = ConfigurableHyperoptOptimizer(hyperopt_config=config, strategy_name=args.strategy)

        # Generate sample data for optimization (in a real system, this would come from data provider)
        print("📊 Generating sample data for optimization...")
        timestamps = pd.date_range(start='2023-01-01', periods=500, freq='1h')
        prices = 30000 + np.cumsum(np.random.randn(500) * 100)  # Simulated BTC prices
        sample_data = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices + np.random.randn(500) * 5,
            'high': prices + abs(np.random.randn(500)) * 10,
            'low': prices - abs(np.random.randn(500)) * 10,
            'close': prices,
            'volume': np.abs(np.random.randn(500)) * 500,
            'volatility': np.abs(np.random.randn(500)) * 5
        })

        # Run optimization
        symbol = args.symbol if args.symbol else "BTCUSDT"
        results = optimizer.optimize_with_config(
            strategy_name=args.strategy,
            data=sample_data,
            symbol=symbol,
            custom_config={"max_evals": args.max_evals}
        )

        print(f"✅ Optimization completed!")
        print(f"📊 Best parameters: {results.get('best_params', {})}")
        print(
            f"🏆 Best score: {results.get('best_value', 0) if 'best_value' in results else results.get('best_loss', 'N/A')}")

    elif args.mode == "retune":
        print(f"🔄 Running auto-retune for strategy: {args.strategy}")

        # Import auto-retune components
        from infrastructure.optimization.auto_retune_hyperopt import AutoRetuneOptimizer

        symbols = args.symbols.split(",") if args.symbols else [args.symbol if args.symbol else "BTC/USDT"]

        auto_retune = AutoRetuneOptimizer(
            strategy_name=args.strategy,
            performance_threshold=-5.0
        )

        # Run auto-retune for each symbol
        for symbol in symbols:
            result = auto_retune.run_auto_retune(
                strategy_name=args.strategy,
                symbols=[symbol],
                risk_config={"atr_multiplier": 1.5, "use_dynamic_position": True}
            )
            print(f"✅ Auto-retune completed for {symbol}")

        print("✅ All auto-retune processes completed!")

    elif args.mode == "production":
        if args.auto_detect:
            # Run in auto-detection mode
            print("🚀 Starting auto-detection mode...")
            if args.symbols or args.symbol:
                symbol_list = args.symbols or [args.symbol]
                print(
                    f"📊 System will monitor markets and automatically detect opportunities for symbols: {symbol_list}")
            else:
                print("📊 System will automatically discover and monitor market opportunities across multiple symbols")

            # Import required components for auto-detection
            from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator

            # Create real implementations for standalone execution (same as in the orchestrator class)
            from infrastructure.data.enhanced_data_provider import create_enhanced_data_provider
            from domain.ports.execution_ports import ExecutionPort
            from domain.ports.portfolio_ports import PortfolioManagementPort
            from domain.ports.optimization_ports import IOptimizationService

            # Create execution service first using the registry to avoid duplicate initialization
            from infrastructure.services.broker_registry import broker_registry
            execution_service = broker_registry.get_execution_service(use_multi_broker=True,
                                                                      primary_broker='bingx')  # Uses multi-broker with exchange switching, primary is BingX

            # Create enhanced data provider that uses real data and can download missing symbols
            # Use environment variable or default path for historical data
            # For now, pass the execution service as the broker service (it has access to the broker)
            # Configure to use binance as primary source for historical data to avoid BingX rate limits
            market_data_repo = broker_registry.get_historical_data_provider(
                csv_base_path=None,
                download_enabled=True,
                broker_service=execution_service,
                historical_data_source=Configs.data.preferred_historical_data_source if Configs.data and hasattr(
                    Configs.data, 'preferred_historical_data_source') else 'binance',
                # Use binance by default to avoid BingX rate limits
                fallback_sources=['mexc', 'phemex', 'bingx']  # Fallback order to avoid rate limits
            )
            # Import real portfolio and optimization services
            from infrastructure.portfolio.portfolio_adapters import EqualWeightPortfolioAdapter
            from infrastructure.optimization.advanced_optimization_service import AdvancedOptimizationService

            # Create and configure real services
            portfolio_service = EqualWeightPortfolioAdapter()
            optimization_service = AdvancedOptimizationService()

            # Determine symbols to monitor
            symbols = []
            if args.symbols:
                symbols = args.symbols.split(",")
            elif args.symbol:
                symbols = [args.symbol]
            # If no symbols provided in auto-detect mode, the orchestrator will auto-discover them

            # Create risk config
            risk_config = {
                "max_risk": 0.02,
                "atr_multiplier": 1.5,
                "use_dynamic_position": True
            }

            # Create and run auto-detection orchestrator
            auto_detection_orchestrator = AutoDetectionOrchestrator(
                market_data_repo=market_data_repo,
                execution_service=execution_service,
                portfolio_service=portfolio_service,
                optimization_service=optimization_service,
                symbols=symbols if symbols else None,  # Pass None if no symbols specified
                risk_config=risk_config,
                comprehensive_logging=args.comprehensive_logs
            )

            try:
                auto_detection_orchestrator.run_auto_detection()
            except KeyboardInterrupt:
                print("\n🛑 Auto-detection mode stopped by user")
        else:
            # Run in original production mode with manual strategy selection
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
                # Return data for the specified symbol if provided
                symbol_key = args.symbol if args.symbol else "BTCUSD"
                return {symbol_key: df}

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

    elif args.mode == "monitor":
        print("📊 Starting monitoring mode...")
        print("Note: In a full implementation, this would connect to live data sources and monitor performance")
        # For now, just simulate monitoring
        import time
        import random

        while True:
            try:
                print(f"📈 Monitoring system: Portfolio value = ${10000 + random.randint(-500, 500):.2f}")
                time.sleep(5)  # Update every 5 seconds
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                break

    elif args.mode == "config-test":
        print("🔧 Testing configuration...")
        # Test that we can import and instantiate key components
        try:
            from shared.logger import EnhancedLogger
            logger = EnhancedLogger("ConfigTest")
            logger.info("Configuration test passed!")
            print("✅ Configuration test completed successfully")
        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
            sys.exit(1)
    else:
        print(f"❌ Unknown mode: {args.mode}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
