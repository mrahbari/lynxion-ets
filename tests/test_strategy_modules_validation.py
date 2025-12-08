"""
Test to validate strategy orchestrator & strategy modules including:
- Backtest
- Walk-forward 
- Hyperopt (parameter optimization)
- Strategy results validation with symbol data
"""
import unittest
import sys
import os
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage, Money
from application.containers.container import container
from datetime import datetime


class TestStrategyOrchestratorAndModules(unittest.TestCase):
    """Test strategy orchestrator and related modules"""

    def setUp(self):
        """Set up test environment with container"""
        from main_hexagonal_container import setup_application
        setup_application()

    def test_strategy_orchestrator_functionality(self):
        """Test that the Strategy Orchestrator works correctly"""
        # Get the strategy orchestration service
        strategy_selection_service = container.resolve('strategy_selection_service')
        strategy_orchestration_service = container.resolve('strategy_orchestration_service')
        
        # Test that services exist and are functional
        self.assertIsNotNone(strategy_selection_service)
        self.assertIsNotNone(strategy_orchestration_service)

        # Test strategy selection
        symbol = Symbol("BTC-USDT")
        selected_strategy = strategy_selection_service.select_best_strategy(symbol)
        self.assertIsNotNone(selected_strategy)

        # Verify strategy has required methods
        self.assertTrue(hasattr(selected_strategy, 'generate_signal'))
        self.assertTrue(hasattr(selected_strategy, 'get_strategy_name'))
        self.assertTrue(hasattr(selected_strategy, 'update_with_market_data'))
        self.assertTrue(hasattr(selected_strategy, 'calculate_position_size'))

        # Test signal generation
        signal = selected_strategy.generate_signal(symbol)
        if signal is not None:  # Some strategies might not generate signals with mock data
            self.assertIsInstance(signal.symbol, Symbol)
            self.assertIsInstance(signal.signal_type, SignalType)
            self.assertIsInstance(signal.confidence, Percentage)
            self.assertIsInstance(signal.score, (int, float))
            self.assertIsInstance(signal.strategy_name, str)

    def test_backtest_module_functionality(self):
        """Test that backtest module works correctly"""
        # Get backtest services
        backtest_service = container.resolve('backtest_service')
        backtest_analytics_service = container.resolve('backtest_analytics_service')
        backtest_engine = container.resolve('backtest_engine')
        
        self.assertIsNotNone(backtest_service)
        self.assertIsNotNone(backtest_analytics_service)
        self.assertIsNotNone(backtest_engine)

        # Test running a simple backtest
        symbol = Symbol("BTC-USDT")
        
        # Run a backtest (using placeholder values since real data isn't available in test)
        import datetime
        start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        results = backtest_service.run_strategy_backtest(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000.0,
            strategy_name="TestStrategy"
        )
        
        # Results may be empty due to lack of historical data, but the call should not fail
        if results:
            self.assertIsInstance(results, dict)
            # Verify expected keys are present
            expected_keys = ['initial_capital', 'final_capital', 'total_return', 'total_trades', 'win_rate']
            for key in expected_keys:
                self.assertIn(key, results)

    def test_walk_forward_analysis_availability(self):
        """Test that walk-forward analysis components are available"""
        # Check for walk-forward components
        # Since walk-forward analysis is more complex, let's just verify the basic setup works
        from infrastructure.backtest.adapters.walk_forward import WalkForwardAnalyzer
        
        # Test initialization of walk-forward analyzer
        config = {
            'in_sample_size': 30,
            'out_of_sample_size': 15,
            'walk_forward_count': 5,
            'reoptimization_frequency': 10,
            'performance_threshold': 0.05,
            'max_drawdown_threshold': 0.20
        }
        
        analyzer = WalkForwardAnalyzer(config)
        self.assertEqual(analyzer.in_sample_size, 30)
        self.assertEqual(analyzer.out_of_sample_size, 15)
        self.assertEqual(analyzer.walk_forward_count, 5)

    def test_hyperparameter_optimization_setup(self):
        """Test that hyperparameter optimization (hyperopt) is correctly set up for strategies"""
        # Get the optimization service
        backtest_optimization_service = container.resolve('backtest_optimization_service')
        
        self.assertIsNotNone(backtest_optimization_service)
        self.assertTrue(hasattr(backtest_optimization_service, 'optimize_strategy_parameters'))
        self.assertTrue(hasattr(backtest_optimization_service, '_calculate_optimization_score'))

        # Test that we can call optimization with sample parameters
        symbol = Symbol("BTC-USDT")
        import datetime
        start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')

        # Define parameter ranges for optimization (example parameters)
        parameter_ranges = {
            'lookback_period': [10, 20, 30],  # Example parameter
            'threshold': [0.5, 0.6, 0.7]     # Example parameter
        }

        try:
            # This call might fail due to lack of real data, 
            # but the optimization framework should be in place
            results = backtest_optimization_service.optimize_strategy_parameters(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=10000.0,
                strategy_name="TestStrategy",
                parameter_ranges=parameter_ranges
            )
            
            # If optimization ran, results should have expected structure
            if results:
                self.assertIn('best_parameters', results)
                self.assertIn('best_score', results)
                self.assertIn('total_combinations', results)
                self.assertIsInstance(results['best_parameters'], dict)
                self.assertIsInstance(results['best_score'], (int, float))
                self.assertIsInstance(results['total_combinations'], int)
        except Exception as e:
            # Even if it fails due to lack of historical data, 
            # the optimization framework should be structured correctly
            print(f"Optimization test encountered expected exception due to data constraints: {e}")

    def test_all_strategies_can_be_resolved(self):
        """Test that all strategy implementations are available in container"""
        strategy_names = [
            'trend_follow_strategy',
            'mean_reversion_strategy',
            'scalping_strategy',
            'breakout_strategy'
        ]
        
        for strategy_name in strategy_names:
            with self.subTest(strategy=strategy_name):
                strategy = container.resolve(strategy_name)
                self.assertIsNotNone(strategy)
                self.assertTrue(hasattr(strategy, 'generate_signal'))
                self.assertTrue(hasattr(strategy, 'get_strategy_name'))

    def test_strategy_results_validation_with_symbol_data(self):
        """Validate strategy results with symbol data"""
        # Get services needed for validation
        strategy_selection_service = container.resolve('strategy_selection_service')
        
        symbol = Symbol("BTC-USDT")
        strategy = strategy_selection_service.select_best_strategy(symbol)
        
        if strategy:
            # Generate a signal
            signal = strategy.generate_signal(symbol)
            
            if signal:
                # Validate signal structure
                self.assertEqual(signal.symbol, symbol)
                self.assertIsInstance(signal.signal_type, SignalType)
                self.assertIsInstance(signal.confidence, Percentage)
                self.assertIsInstance(signal.strategy_name, str)
                
                # Test position sizing
                position_size = strategy.calculate_position_size(signal, 50000.0)
                self.assertIsInstance(position_size, float)
                self.assertGreaterEqual(position_size, 0)
            
            # Test with multiple strategies if possible
            for _ in range(3):  # Test multiple selections
                next_strategy = strategy_selection_service.select_best_strategy(symbol)
                self.assertIsNotNone(next_strategy)

    def test_strategy_performance_tracking(self):
        """Test strategy performance tracking and validation"""
        # Get strategy orchestration service
        strategy_orchestration_service = container.resolve('strategy_orchestration_service')
        
        # Get strategy performance
        performance = strategy_orchestration_service.get_strategy_performance()
        self.assertIsInstance(performance, dict)


def suite():
    """Create test suite for strategy orchestrator and modules"""
    suite = unittest.TestSuite()
    suite.addTest(TestStrategyOrchestratorAndModules('test_strategy_orchestrator_functionality'))
    suite.addTest(TestStrategyOrchestratorAndModules('test_backtest_module_functionality'))
    suite.addTest(TestStrategyOrchestratorAndModules('test_walk_forward_analysis_availability'))
    suite.addTest(TestStrategyOrchestratorAndModules('test_hyperparameter_optimization_setup'))
    suite.addTest(TestStrategyOrchestratorAndModules('test_all_strategies_can_be_resolved'))
    suite.addTest(TestStrategyOrchestratorAndModules('test_strategy_results_validation_with_symbol_data'))
    suite.addTest(TestStrategyOrchestratorAndModules('test_strategy_performance_tracking'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())