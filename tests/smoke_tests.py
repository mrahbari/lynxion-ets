"""
Smoke tests for the trading system to verify basic functionality works properly.
These tests are quick and verify that the core components are functioning.
"""
import unittest
import sys
import os
from datetime import datetime

# Add the project root to the path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.watchers.market_opportunity_watcher import MarketOpportunityWatcher
from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
from shared.logger import EnhancedLogger


class TestSmokeTests(unittest.TestCase):
    """Smoke tests for the trading system."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.logger = EnhancedLogger("SmokeTest")
        self.symbols = ["BTCUSDT", "ETHUSDT"]
        
    def test_market_opportunity_watcher_creation(self):
        """Test that MarketOpportunityWatcher can be created without errors."""
        try:
            watcher = MarketOpportunityWatcher(symbols=self.symbols)
            self.assertIsNotNone(watcher)
            self.assertEqual(len(watcher.symbols), 2)
            self.assertEqual([s.value for s in watcher.symbols], self.symbols)
            self.logger.info("✅ MarketOpportunityWatcher creation test passed")
        except Exception as e:
            self.logger.error(f"❌ MarketOpportunityWatcher creation test failed: {e}")
            raise
    
    def test_market_opportunity_watcher_auto_discovery(self):
        """Test that MarketOpportunityWatcher can auto-discover symbols."""
        try:
            watcher = MarketOpportunityWatcher(auto_discover_symbols=True)
            self.assertIsNotNone(watcher)
            self.assertGreater(len(watcher.symbols), 0)
            self.logger.info("✅ MarketOpportunityWatcher auto-discovery test passed")
        except Exception as e:
            self.logger.error(f"❌ MarketOpportunityWatcher auto-discovery test failed: {e}")
            raise
    
    def test_auto_detection_orchestrator_creation(self):
        """Test that AutoDetectionOrchestrator can be created without errors."""
        # Import the required interfaces and create mock implementations
        from domain.ports.data_ports import DataProviderPort
        from domain.ports.execution_ports import ExecutionPort
        from domain.ports.portfolio_ports import PortfolioManagementPort
        from domain.ports.optimization_ports import IOptimizationService
        
        # Create simple mock implementations
        class MockDataProvider(DataProviderPort):
            def get_current_price(self, symbol):
                return 50000.0  # Mock price

            def get_historical_data(self, symbol, period, timeframe='1m'):
                return []  # Return empty list as mock data

            def subscribe_to_market_data(self, symbol, callback):
                return "mock_subscription_id"

            def unsubscribe_from_market_data(self, subscription_id):
                return True
        
        class MockExecutionService(ExecutionPort):
            def execute_order(self, order):
                return "mock_execution_id"

            def cancel_order(self, order_id: str) -> bool:
                return True

            def get_execution_status(self, execution_id: str) -> str:
                return "filled"

            def get_available_symbols(self) -> set:
                return {"BTCUSDT", "ETHUSDT"}        
        class MockPortfolioService(PortfolioManagementPort):
            def calculate_allocation(self, total_capital: float, symbols):
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
        
        try:
            orchestrator = AutoDetectionOrchestrator(
                market_data_repo=MockDataProvider(),
                execution_service=MockExecutionService(),
                portfolio_service=MockPortfolioService(),
                optimization_service=MockOptimizationService(),
                symbols=self.symbols
            )
            self.assertIsNotNone(orchestrator)
            self.assertEqual(len(orchestrator.symbols), 2)
            self.logger.info("✅ AutoDetectionOrchestrator creation test passed")
        except Exception as e:
            self.logger.error(f"❌ AutoDetectionOrchestrator creation test failed: {e}")
            raise
    
    def test_auto_detection_orchestrator_auto_discovery(self):
        """Test that AutoDetectionOrchestrator works with auto-discovered symbols."""
        # Import the required interfaces and create mock implementations
        from domain.ports.data_ports import DataProviderPort
        from domain.ports.execution_ports import ExecutionPort
        from domain.ports.portfolio_ports import PortfolioManagementPort
        from domain.ports.optimization_ports import IOptimizationService
        
        # Create simple mock implementations
        class MockDataProvider(DataProviderPort):
            def get_current_price(self, symbol):
                return 50000.0  # Mock price

            def get_historical_data(self, symbol, period, timeframe='1m'):
                return []  # Return empty list as mock data

            def subscribe_to_market_data(self, symbol, callback):
                return "mock_subscription_id"

            def unsubscribe_from_market_data(self, subscription_id):
                return True
        
        class MockExecutionService(ExecutionPort):
            def execute_order(self, order):
                return "mock_execution_id"

            def cancel_order(self, order_id: str) -> bool:
                return True

            def get_execution_status(self, execution_id: str) -> str:
                return "filled"

            def get_available_symbols(self) -> set:
                return {"BTCUSDT", "ETHUSDT"}        
        class MockPortfolioService(PortfolioManagementPort):
            def calculate_allocation(self, total_capital: float, symbols):
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
        
        try:
            orchestrator = AutoDetectionOrchestrator(
                market_data_repo=MockDataProvider(),
                execution_service=MockExecutionService(),
                portfolio_service=MockPortfolioService(),
                optimization_service=MockOptimizationService(),
                symbols=None  # Should auto-discover
            )
            self.assertIsNotNone(orchestrator)
            self.assertGreater(len(orchestrator.symbols), 0)  # Should have auto-discovered symbols
            self.logger.info("✅ AutoDetectionOrchestrator auto-discovery test passed")
        except Exception as e:
            self.logger.error(f"❌ AutoDetectionOrchestrator auto-discovery test failed: {e}")
            raise
    
    def test_run_trading_system_imports(self):
        """Test that run_trading_system.py can be imported without errors."""
        try:
            import run_trading_system
            self.assertIsNotNone(run_trading_system)
            self.logger.info("✅ run_trading_system.py import test passed")
        except ImportError as e:
            self.logger.error(f"❌ run_trading_system.py import test failed: {e}")
            raise
    
    def test_argument_parser_creation(self):
        """Test that the argument parser in run_trading_system.py works."""
        try:
            from run_trading_system import create_parser
            parser = create_parser()
            self.assertIsNotNone(parser)
            
            # Check that the --auto-detect argument was added
            args = parser.parse_args(['--mode', 'production', '--auto-detect'])
            self.assertTrue(args.auto_detect)
            self.logger.info("✅ Argument parser with --auto-detect test passed")
        except Exception as e:
            self.logger.error(f"❌ Argument parser test failed: {e}")
            raise


if __name__ == '__main__':
    print("🧪 Running Smoke Tests...")
    unittest.main(verbosity=2)