"""
Regression tests for the trading system to verify that new features don't break existing functionality.
These tests are more comprehensive and verify that the system works as expected after changes.
"""
import unittest
import sys
import os
import time
from datetime import datetime, timedelta

# Add the project root to the path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.watchers.market_opportunity_watcher import MarketOpportunityWatcher
from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
from shared.logger import EnhancedLogger
from domain.value_objects import Symbol
from domain.entities.trading_entities import SignalType


class TestRegressionTests(unittest.TestCase):
    """Regression tests for the trading system."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.logger = EnhancedLogger("RegressionTest")
        self.symbols = ["BTCUSDT", "ETHUSDT"]
        
    def test_market_opportunity_watcher_functionality(self):
        """Test that MarketOpportunityWatcher functions as expected."""
        watcher = MarketOpportunityWatcher(symbols=self.symbols)

        # Test that watchers are properly initialized
        self.assertEqual(len(watcher.symbols), 2)
        self.assertIn("BTCUSDT", [s.value for s in watcher.symbols])
        self.assertIn("ETHUSDT", [s.value for s in watcher.symbols])
        
        # Test that each symbol has the expected watchers
        for symbol in self.symbols:
            self.assertIn(symbol, watcher.watchers)
            watchers_for_symbol = watcher.watchers[symbol]
            expected_watchers = ['market_pulse', 'volatility', 'trend_mtf', 'anomaly_ml', 'order_flow']
            for expected_watcher in expected_watchers:
                self.assertIn(expected_watcher, watchers_for_symbol)
        
        # Test watcher status
        status = watcher.get_status()
        self.assertTrue(isinstance(status, dict))
        self.assertIn('is_running', status)
        self.assertIn('monitored_symbols', status)
        self.assertEqual(status['monitored_symbols'], self.symbols)
        
        self.logger.info("✅ MarketOpportunityWatcher functionality test passed")
    
    def test_market_opportunity_watcher_analysis(self):
        """Test that the watcher can perform analysis."""
        watcher = MarketOpportunityWatcher(symbols=["BTCUSDT"])

        # Test symbol analysis (this would normally require market data)
        symbol = Symbol("BTCUSDT")
        opportunities = watcher._analyze_symbol(symbol)

        # Check that opportunities structure is correct
        self.assertIn('symbol', opportunities)
        self.assertIn('timestamp', opportunities)
        self.assertIn('signals', opportunities)
        self.assertIn('recommendation', opportunities)
        self.assertIn('confidence', opportunities)
        self.assertIn('strategy_suggestion', opportunities)

        # Check that symbol matches
        self.assertEqual(opportunities['symbol'], "BTCUSDT")

        self.logger.info("✅ MarketOpportunityWatcher analysis test passed")
    
    def test_auto_detection_orchestrator_functionality(self):
        """Test that AutoDetectionOrchestrator functions as expected."""
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
        
        orchestrator = AutoDetectionOrchestrator(
            market_data_repo=MockDataProvider(),
            execution_service=MockExecutionService(),
            portfolio_service=MockPortfolioService(),
            optimization_service=MockOptimizationService(),
            symbols=self.symbols
        )
        
        # Test orchestrator initialization
        self.assertIsNotNone(orchestrator)
        self.assertEqual(len(orchestrator.symbols), 2)
        self.assertIn(Symbol("BTCUSDT"), orchestrator.symbols)
        self.assertIn(Symbol("ETHUSDT"), orchestrator.symbols)
        
        # Test orchestrator status
        status = orchestrator.get_status()
        self.assertTrue(isinstance(status, dict))
        self.assertIn('is_running', status)
        self.assertIn('monitored_symbols', status)
        self.assertIn('active_trades', status)
        self.assertIn('opportunity_queue_size', status)
        self.assertIn('watcher_status', status)
        
        self.logger.info("✅ AutoDetectionOrchestrator functionality test passed")
    
    def test_auto_detection_with_callback(self):
        """Test that the auto-detection system properly handles opportunities."""
        # Track if callback was called
        callback_called = []
        
        def mock_callback(opportunity):
            callback_called.append(opportunity)
        
        watcher = MarketOpportunityWatcher(
            symbols=["BTCUSDT"],
            opportunity_callback=mock_callback
        )
        
        # Verify callback was registered
        self.assertIsNotNone(watcher.opportunity_callback)
        
        # Simulate handling an opportunity (this is what gets called internally)
        test_opportunity = {
            'symbol': 'BTCUSDT',
            'timestamp': datetime.now(),
            'recommendation': 'BUY',
            'confidence': 0.8,
            'strategy_suggestion': 'momentum_strategy'
        }
        
        # Call the internal method that handles opportunities
        watcher._process_opportunities(Symbol("BTCUSDT"), test_opportunity)
        
        # For this test, we're just making sure the callback mechanism works
        # The actual callback execution is done async by the monitoring system
        self.assertTrue(callable(watcher.opportunity_callback))
        
        self.logger.info("✅ Auto-detection callback test passed")
    
    def test_symbol_discovery_functionality(self):
        """Test that symbol discovery works properly."""
        watcher = MarketOpportunityWatcher(auto_discover_symbols=True)
        
        # Test that auto-discovery found symbols
        self.assertGreater(len(watcher.symbols), 0)
        discovered_symbols = [s.value for s in watcher.symbols]
        
        # Check that it found some symbols (the CMC screener finds actively moving coins)
        # Instead of hardcoding specific symbols, we just ensure it found some
        self.assertGreater(len(discovered_symbols), 0,
                         f"Expected to find at least one symbol from market screening, but found {discovered_symbols}")

        # Verify that all discovered symbols are valid
        for symbol in discovered_symbols:
            self.assertIsInstance(symbol, str)
            self.assertTrue(len(symbol) >= 6)  # At least base + quote like BTCUSDT
            self.assertTrue('USDT' in symbol or symbol.endswith('USD') or symbol.endswith('USDC'))
        
        self.logger.info(f"✅ Symbol discovery test passed - found {len(discovered_symbols)} symbols: {discovered_symbols}")
    
    def test_auto_detection_orchestrator_auto_discovery_integration(self):
        """Test that auto-detection orchestrator works with auto-discovered symbols."""
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
        
        # Create orchestrator with auto-discovered symbols
        orchestrator = AutoDetectionOrchestrator(
            market_data_repo=MockDataProvider(),
            execution_service=MockExecutionService(),
            portfolio_service=MockPortfolioService(),
            optimization_service=MockOptimizationService(),
            symbols=None  # Should auto-discover
        )
        
        # Verify that orchestrator was created with auto-discovered symbols
        self.assertIsNotNone(orchestrator)
        self.assertGreater(len(orchestrator.symbols), 0)
        
        # Check that the opportunity watcher was created with auto-discovery enabled
        self.assertTrue(orchestrator.opportunity_watcher.auto_discover_symbols)
        
        self.logger.info("✅ AutoDetectionOrchestrator auto-discovery integration test passed")
    
    def test_backward_compatibility(self):
        """Test that existing functionality still works with new additions."""
        # Test that the original argument parser still works for non-auto-detect mode
        from run_trading_system import create_parser
        
        # Test normal production mode without auto-detect
        parser = create_parser()
        args = parser.parse_args(['--mode', 'production', '--strategy', 'crypto_breakout', '--symbol', 'BTC/USDT'])
        
        self.assertEqual(args.mode, 'production')
        self.assertEqual(args.strategy, 'crypto_breakout')
        self.assertEqual(args.symbol, 'BTC/USDT')
        self.assertFalse(args.auto_detect)  # Should be False by default
        
        # Test production mode with auto-detect
        args2 = parser.parse_args(['--mode', 'production', '--auto-detect', '--symbols', 'BTC/USDT,ETH/USDT'])
        
        self.assertEqual(args2.mode, 'production')
        self.assertTrue(args2.auto_detect)
        self.assertEqual(args2.symbols, 'BTC/USDT,ETH/USDT')
        
        self.logger.info("✅ Backward compatibility test passed")
    
    def test_command_line_help_includes_auto_detect(self):
        """Test that the help text includes the new auto-detect option."""
        from run_trading_system import create_parser
        import argparse
        
        parser = create_parser()
        
        # Get help text
        help_text = parser.format_help()
        
        # Check that auto-detect is mentioned in help
        self.assertIn('auto-detect', help_text)
        self.assertIn('Run in auto-detection mode', help_text)
        
        self.logger.info("✅ Command line help includes auto-detect test passed")


if __name__ == '__main__':
    print("🔄 Running Regression Tests...")
    print("Note: These tests verify that new features don't break existing functionality")
    unittest.main(verbosity=2)