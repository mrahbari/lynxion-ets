"""Full Hedge-Fund pipeline following hexagonal architecture."""

import threading
import time
from typing import Dict, Any

from shared.logger import EnhancedLogger
from infrastructure.optimization.auto_retune_hyperopt import AutoRetuneOptimizer, AutoRetuneScheduler
from infrastructure.execution.live_execution_engine import LiveExecutionEngine, BrokerAPIService
# Import dashboard with error handling for missing dash dependency
try:
    from infrastructure.adapters.live_dashboard import LiveDashboardAdapter
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    LiveDashboardAdapter = None
from infrastructure.services.risk_alerts import RiskAlertService, EmailNotificationService, TelegramNotificationService
from domain.ports.optimization_ports import IDataLoader
from domain.ports.execution_ports import ExecutionPort
from domain.ports.portfolio_ports import PortfolioManagementPort
from typing import List, Any
from domain.value_objects import Symbol, Percentage
from domain.ports.data_ports import DataProviderPort


class FullHedgeFundPipeline:
    """Complete Hedge-Fund pipeline following hexagonal architecture."""

    def __init__(self,
                 data_loader: IDataLoader,
                 execution_service: ExecutionPort,
                 portfolio_service: PortfolioManagementPort,
                 market_data_repo: DataProviderPort):
        self.data_loader = data_loader
        self.execution_service = execution_service
        self.portfolio_service = portfolio_service
        self.market_data_repo = market_data_repo
        self.logger = EnhancedLogger("FullHedgeFundPipeline")

        # Initialize all services based on provided dependencies
        self.auto_retune_optimizer = AutoRetuneOptimizer()
        self.auto_retune_scheduler = AutoRetuneScheduler(self.auto_retune_optimizer)

        # Create broker service (for now, mock implementation)
        self.broker_service = BrokerAPIService()

        # Create execution engine
        self.execution_engine = LiveExecutionEngine(
            broker_service=self.broker_service,
            data_loader=self.data_loader,
            optimization_service=self.auto_retune_optimizer,
            execution_service=self.execution_service
        )

        # Create dashboard if available
        if DASHBOARD_AVAILABLE and LiveDashboardAdapter is not None:
            self.dashboard = LiveDashboardAdapter(
                market_data_repo=self.market_data_repo,
                portfolio_service=self.portfolio_service
            )
        else:
            self.dashboard = None

        # Create notification services (with placeholder credentials)
        email_service = EmailNotificationService(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="example@gmail.com",
            password="password",
            from_email="example@gmail.com",
            to_email="recipient@gmail.com"
        )
        telegram_service = TelegramNotificationService(
            bot_token="YOUR_BOT_TOKEN",
            chat_id="YOUR_CHAT_ID"
        )

        # Create risk alert service
        self.risk_alert_service = RiskAlertService(
            notification_services=[email_service, telegram_service],
            max_leverage=10.0,
            drawdown_threshold=-0.1
        )

        # Initialize threads
        self.threads = []

    def data_fetcher(self) -> Dict[str, Any]:
        """
        Mock data fetcher - in real implementation this would fetch from market data repo.
        Returns: {"XAUUSD": df, "BTCUSD": df, ...}
        """
        import pandas as pd
        import numpy as np
        timestamp = pd.date_range(start='2025-01-01', periods=10, freq='T')
        df_sample = pd.DataFrame({
            "timestamp": timestamp,
            "open": np.random.rand(10)*100+1000,
            "high": np.random.rand(10)*100+1000,
            "low": np.random.rand(10)*100+1000,
            "close": np.random.rand(10)*100+1000,
            "volume": np.abs(np.random.randn(10))*10,
            "volatility": np.abs(np.random.randn(10))*5
        })
        return {"XAUUSD": df_sample, "BTCUSD": df_sample.copy()}

    def start_dashboard(self):
        """Start dashboard in a separate thread."""
        if self.dashboard is not None:
            dashboard_thread = self.dashboard.start_dashboard_thread()
            self.threads.append(("dashboard", dashboard_thread))
            self.logger.info("Dashboard thread started")
        else:
            self.logger.info("Dashboard not available, skipping dashboard thread")

    def start_execution(self):
        """Start live execution in a separate thread."""
        def execution_worker():
            self.execution_engine.run_live_execution_with_auto_retune(
                data_fetcher=self.data_fetcher,
                strategy_name="crypto_breakout",
                risk_config={
                    "max_risk": 0.02,
                    "atr_multiplier": 1.5,
                    "use_dynamic_position": True
                }
            )

        execution_thread = threading.Thread(target=execution_worker)
        execution_thread.daemon = True
        execution_thread.start()
        self.threads.append(("execution", execution_thread))
        self.logger.info("Execution thread started")

    def start_alerts(self):
        """Start risk alerts in a separate thread."""
        def alerts_worker():
            while True:
                try:
                    # In a real implementation, this would fetch actual data
                    # from repositories or services rather than using placeholders
                    trade_log = {}
                    equity_curve = {}
                    asset_performance = {}

                    self.risk_alert_service.check_and_alert(
                        trade_log, equity_curve, asset_performance
                    )
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    self.logger.error(f"Error in alerts thread: {e}")
                    time.sleep(60)

        alerts_thread = threading.Thread(target=alerts_worker)
        alerts_thread.daemon = True
        alerts_thread.start()
        self.threads.append(("alerts", alerts_thread))
        self.logger.info("Alerts thread started")

    def start_all_services(self):
        """Start all services in the pipeline."""
        self.logger.info("Starting full Hedge-Fund pipeline...")

        # Start all services in threads
        self.start_dashboard()  # Only starts if dashboard is available
        self.start_execution()
        self.start_alerts()

        self.logger.info("All available pipeline services started")

    def run_pipeline(self):
        """Run the complete pipeline."""
        self.start_all_services()

        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Pipeline stopped by user")


# Mock implementations for standalone execution
class MockDataLoader(IDataLoader):
    def load_historical_data(self, symbol: str, timeframe: str, limit: int):
        import pandas as pd
        return pd.DataFrame()

    def cache_exists(self, symbol: str, timeframe: str) -> bool:
        return False


class MockExecutionService(ExecutionPort):
    def execute_order(self, order):
        return "mock_execution_id"

    def cancel_order(self, order_id: str) -> bool:
        return True

    def get_execution_status(self, execution_id: str) -> str:
        return "filled"


class MockPortfolioService(PortfolioManagementPort):
    def calculate_allocation(self, total_capital: float, symbols: List[Symbol]) -> Dict[Symbol, float]:
        """Mock allocation - distribute equally"""
        if symbols:
            equal_alloc = total_capital / len(symbols)
            return {symbol: equal_alloc for symbol in symbols}
        return {}

    def rebalance_portfolio(self, target_allocations: Dict[Symbol, Percentage]) -> List:
        """Mock rebalancing"""
        return []

    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Mock portfolio metrics"""
        return {
            "sharpe_ratio": 1.5,
            "max_drawdown": 0.1,
            "total_return": 0.15,
            "volatility": 0.2
        }


class MockMarketDataRepository(DataProviderPort):
    def get_current_price(self, symbol: Symbol):
        """Mock current price"""
        return 100.0  # Default price

    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m'):
        """Mock historical data"""
        return []

    def subscribe_to_market_data(self, symbol: Symbol, callback):
        """Mock subscription"""
        return "subscription_id"

    def unsubscribe_from_market_data(self, subscription_id: str):
        """Mock unsubscription"""
        pass


def run_full_pipeline():
    """Standalone function to run the complete pipeline."""
    # Create mock implementations for dependencies
    data_loader = MockDataLoader()
    execution_service = MockExecutionService()
    portfolio_service = MockPortfolioService()
    market_data_repo = MockMarketDataRepository()

    # Create pipeline
    pipeline = FullHedgeFundPipeline(
        data_loader=data_loader,
        execution_service=execution_service,
        portfolio_service=portfolio_service,
        market_data_repo=market_data_repo
    )

    # Run the pipeline
    pipeline.run_pipeline()


if __name__ == "__main__":
    print("🚀 Starting Full Hedge-Fund Pipeline...")
    print("📊 Dashboard, Execution, and Alerts services will start in separate threads...")
    print("⚠️  This is a demo - using placeholder implementations for external services...")

    run_full_pipeline()