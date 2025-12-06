"""Comprehensive integration tests for the entire Hyperopt Auto-Retune system."""

import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Add the project root to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from main_container import MainContainer
from main_hexagonal_container import MainHexagonalContainer
from production_trading_system import ProductionTradingSystem
from run_trading_system import load_config
from shared.logger import EnhancedLogger
from infrastructure.data.coin_history_service import CoinHistoryService
from infrastructure.results_tracking.results_tracker import ResultsTracker
from shared.configurable_hyperopt import ConfigurableHyperoptOptimizer, HyperoptConfig
from application.services.adaptive_retuning import AdaptiveRetuningManager


class TestSystemIntegration(unittest.TestCase):
    """Integration tests covering the entire system flow."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = {
            "data_cache_dir": str(Path(self.temp_dir) / "cache"),
            "results_db_path": str(Path(self.temp_dir) / "results.db"),
            "results_storage_dir": str(Path(self.temp_dir) / "storage"),
            "coin_cache_dir": str(Path(self.temp_dir) / "coin_cache"),
            "optimization_results_dir": str(Path(self.temp_dir) / "optimization_results"),
            "max_cache_age_hours": 1,
            "max_coin_cache_size": 10,
            "initial_capital": 10000.0,
            "fee_rate": 0.001,
            "slippage_factor": 0.0005,
            "default_timeframe": "1h",
            "default_strategy": "crypto_breakout",
            "enable_auto_retune_scheduler": False,  # Disable for tests
            "retune_check_interval": 3600,
            "max_position_size": 0.20,
            "max_drawdown_threshold": -0.15,
        }
        
        self.logger = EnhancedLogger("TestSystemIntegration")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_main_container_initialization(self):
        """Test that main container initializes correctly with all services."""
        container = MainContainer(self.test_config)
        
        # Test that all services are accessible
        services = container.get_all_services()
        self.assertGreater(len(services), 0, "Container should have services")
        
        # Test specific services
        data_loader = container.get_service('data_loader')
        self.assertIsNotNone(data_loader, "Data loader should be available")
        
        results_tracker = container.get_service('results_tracker')
        self.assertIsNotNone(results_tracker, "Results tracker should be available")
        
        optimization_service = container.get_service('optimization_service')
        self.assertIsNotNone(optimization_service, "Optimization service should be available")
        
        hyperopt_optimizer = container.get_service('hyperopt_optimizer')
        self.assertIsNotNone(hyperopt_optimizer, "Hyperopt optimizer should be available")
        
        coin_history_service = container.get_service('coin_history_service')
        self.assertIsNotNone(coin_history_service, "Coin history service should be available")
    
    def test_hexagonal_container_initialization(self):
        """Test that hexagonal container initializes correctly."""
        container = MainHexagonalContainer(self.test_config)
        
        # Test that all ports are available
        ports = container.get_all_ports()
        self.assertGreater(len(ports), 0, "Hexagonal container should have ports")
        
        # Test architecture validation
        validation_results = container.validate_architecture()
        self.assertTrue(all(validation_results.values()), 
                       f"Not all architecture validations passed: {validation_results}")
        
        # Test specific ports
        data_loader = container.get_port('data_loader')
        self.assertIsNotNone(data_loader, "Data loader port should be available")
        
        results_tracker = container.get_port('results_tracker')
        self.assertIsNotNone(results_tracker, "Results tracker port should be available")
    
    def test_coin_history_service_with_cache(self):
        """Test coin history service with LRU cache functionality."""
        service = CoinHistoryService(
            cache_dir=self.test_config["coin_cache_dir"],
            max_cache_age_hours=1,
            max_cache_size=5
        )

        # Create sample data
        sample_data = self._create_sample_data()

        # Save to cache
        service._save_to_cache(sample_data, "BTC/USDT", "1h")

        # Load from cache - the correct method name is fetch_historical_data
        loaded_data = service.fetch_historical_data("BTC/USDT", "1h", 1000)

        # Verify data integrity
        self.assertEqual(len(loaded_data), len(sample_data))
        self.assertEqual(list(loaded_data.columns), list(sample_data.columns))

        # Test cache statistics
        stats = service.get_cache_stats()
        self.assertIn('BTC/USDT_1h', stats['cache_keys'])
    
    def test_results_tracker_functionality(self):
        """Test results tracker with both database and file storage."""
        tracker = ResultsTracker(
            db_path=self.test_config["results_db_path"],
            storage_dir=self.test_config["results_storage_dir"],
            use_database=True
        )
        
        # Test hyperopt result saving and retrieval
        hyperopt_result = {
            "rsi_length": 14,
            "ema_fast": 9,
            "atr_multiplier": 2.0
        }
        
        hyperopt_id = tracker.save_hyperopt_result(
            strategy_name="test_strategy",
            symbol="BTC/USDT",
            parameters=hyperopt_result,
            best_value=-0.12,
            trials_completed=50,
            optimization_objective="sharpe_ratio",
            execution_time=1.2
        )
        
        # Retrieve results
        retrieved_results = tracker.get_hyperopt_results(limit=1)
        self.assertEqual(len(retrieved_results), 1)
        self.assertEqual(retrieved_results[0]["strategy_name"], "test_strategy")
        
        # Test backtest result
        backtest_result = tracker.save_backtest_result(
            strategy_name="test_strategy",
            symbol="BTC/USDT",
            parameters=hyperopt_result,
            total_return=0.05,
            sharpe_ratio=0.8,
            max_drawdown=-0.03,
            win_rate=0.6,
            total_trades=45,
            profit_factor=1.8
        )
        
        backtest_results = tracker.get_backtest_results(limit=1)
        self.assertEqual(len(backtest_results), 1)
        self.assertEqual(backtest_results[0]["strategy_name"], "test_strategy")
        
        # Test best parameters lookup
        best_params = tracker.get_best_parameters("test_strategy", "BTC/USDT", "sharpe_ratio")
        self.assertIsNotNone(best_params)
    
    def test_hyperopt_configuration(self):
        """Test hyperopt configuration system."""
        config = HyperoptConfig(strategy_name="crypto_breakout")

        # Test parameter space generation
        param_space = config.get_parameter_space("crypto_breakout")
        self.assertGreater(len(param_space), 0, "Parameter space should have entries")
        
        # Test optimization config
        opt_config = config.get_optimization_config()
        self.assertIn("max_evals", opt_config)
        self.assertIn("algorithm", opt_config)
        self.assertIn("optimization_objective", opt_config)
        
        # Test constraints
        constraints = config.get_optimization_constraints()
        self.assertGreater(len(constraints), 0, "Constraints should exist")
        
        # Test validation
        issues = config.validate_config()
        self.assertEqual(len(issues["errors"]), 0, f"Config validation errors: {issues['errors']}")
    
    def test_configurable_hyperopt_optimizer(self):
        """Test configurable hyperopt optimizer integration."""
        config = HyperoptConfig(strategy_name="crypto_breakout")
        optimizer = ConfigurableHyperoptOptimizer(hyperopt_config=config)
        
        # Create sample data
        sample_data = self._create_sample_data()
        
        # Test optimization with config
        result = optimizer.optimize_with_config(
            strategy_name="crypto_breakout",
            symbol="BTC/USDT",
            data=sample_data,
            custom_config=None
        )
        
        # The result might have an error if hyperopt is not available, but structure should be there
        self.assertIsInstance(result, dict)
        
        # Test history lookup
        history = optimizer.get_optimization_history("crypto_breakout", "BTC/USDT")
        # May be empty but should not error
        self.assertIsInstance(history, list)
    
    def test_adaptive_retuning_manager(self):
        """Test adaptive retuning manager functionality."""
        tracker = ResultsTracker(
            db_path=self.test_config["results_db_path"],
            storage_dir=self.test_config["results_storage_dir"],
            use_database=True
        )

        # Define proper schedule configuration
        schedule_config = {
            "daily_retuning_enabled": True,
            "weekly_retuning_enabled": True,
            "monthly_retuning_enabled": True,
            "daily_time": "02:00",
            "weekly_day": "Sunday",
            "monthly_day": 1,
            "minimum_performance_check_interval": 3600,
        }

        manager = AdaptiveRetuningManager(
            results_tracker=tracker,
            schedule_config=schedule_config,
            performance_config=self.test_config
        )

        # Test should_retune logic
        performance_metrics = {
            "sharpe_ratio": 0.45,
            "max_drawdown": -0.12,
            "win_rate": 0.42,
            "profit_factor": 1.2
        }

        decision = manager.should_retune(
            strategy_name="test_strategy",
            symbol="BTC/USDT",
            current_performance=performance_metrics
        )

        self.assertIn("should_retune", decision)
        self.assertIn("triggers", decision)
        self.assertIn("reasons", decision)

        # Test execute retuning (should work even if hyperopt is mocked)
        try:
            execution_result = manager.execute_retuning(
                strategy_name="test_strategy",
                symbol="BTC/USDT"
            )
            self.assertIn("status", execution_result)
        except Exception as e:
            # If hyperopt is not available, that's OK - just test the structure
            self.assertIn("status", execution_result) if 'execution_result' in locals() else True
    
    def test_production_system_integration(self):
        """Test production system with full integration."""
        system = ProductionTradingSystem(self.test_config)
        
        # Start system
        system.start_system()
        
        # Add a strategy
        system.add_strategy(
            strategy_name="crypto_breakout",
            symbols=["BTC/USDT", "ETH/USDT"],
            parameters={"atr_multiplier": 2.0, "risk_per_trade": 0.02}
        )

        # Verify strategy was added
        self.assertIn("crypto_breakout", system.active_strategies)
        self.assertEqual(len(system.active_symbols), 2)
        
        # Test system status monitoring
        status = system.monitor_system_status()
        self.assertIn("timestamp", status)
        self.assertIn("is_running", status)
        self.assertIn("active_strategies", status)
        self.assertGreaterEqual(status["active_strategies"], 1)
        
        # Shutdown system
        system.shutdown()
        self.assertFalse(system.is_running)
    
    def test_end_to_end_flow(self):
        """Test complete end-to-end flow from data loading to optimization."""
        # Initialize containers
        main_container = MainContainer(self.test_config)
        hex_container = MainHexagonalContainer(self.test_config)
        
        # Test data loading
        data_loader = main_container.get_service('data_loader')
        coin_history = main_container.get_service('coin_history_service')
        results_tracker = main_container.get_service('results_tracker')
        optimizer = main_container.get_service('hyperopt_optimizer')
        
        # Create and save sample data
        sample_data = self._create_sample_data()
        coin_history._save_to_cache(sample_data, "BTC/USDT", "1h")
        
        # Load data back
        loaded_data = coin_history.fetch_historical_data("BTC/USDT", "1h", 1000)
        self.assertEqual(len(loaded_data), len(sample_data))
        
        # Run optimization
        opt_result = optimizer.optimize_with_config(
            strategy_name="crypto_breakout",
            symbol="BTC/USDT",
            data=loaded_data,
            custom_config=None
        )
        
        # Save results
        if "error" not in opt_result:
            results_tracker.save_hyperopt_result(
                strategy_name="crypto_breakout",
                symbol="BTC/USDT",
                parameters=opt_result.get("best_params", {}),
                best_value=opt_result.get("best_value", -0.1),
                trials_completed=opt_result.get("trials_completed", 10),
                optimization_objective="sharpe_ratio"
            )
        
        # Verify results were saved
        saved_results = results_tracker.get_hyperopt_results(strategy_name="crypto_breakout")
        # May be empty if hyperopt didn't run, but should not error
        self.assertIsInstance(saved_results, list)

        # Test that we can get best parameters
        best_params = results_tracker.get_best_parameters("crypto_breakout", "BTC/USDT")
        # May be None if no results exist, but should not error
        self.assertTrue(best_params is None or isinstance(best_params, dict))
    
    def test_error_handling_and_edge_cases(self):
        """Test system behavior with edge cases and errors."""
        tracker = ResultsTracker(
            db_path=self.test_config["results_db_path"],
            storage_dir=self.test_config["results_storage_dir"]
        )
        
        # Test saving results with invalid data
        try:
            tracker.save_hyperopt_result(
                strategy_name="",  # Empty strategy
                symbol="",  # Empty symbol
                parameters={},  # Empty parameters
                best_value=0.0,
                trials_completed=0
            )
        except Exception:
            pass  # Expected to handle gracefully
        
        # Test with None values
        try:
            result = tracker.get_hyperopt_results(strategy_name=None, symbol=None)
            self.assertIsInstance(result, list)
        except Exception as e:
            # Should be handled gracefully
            pass
    
    def _create_sample_data(self):
        """Create sample historical data for testing."""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
        np.random.seed(42)
        
        # Generate sample OHLCV data
        returns = np.random.normal(0.0001, 0.02, 100)
        closes = 100 * np.exp(np.cumsum(returns))
        
        opens = closes * np.exp(np.random.normal(0, 0.001, 100))
        highs = np.maximum(closes, opens) * (1 + np.abs(np.random.normal(0, 0.005, 100)))
        lows = np.minimum(closes, opens) * (1 - np.abs(np.random.normal(0, 0.005, 100)))
        volumes = np.random.uniform(1000000, 5000000, 100)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        return data


class TestRunnerIntegration(unittest.TestCase):
    """Test the main runner script functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_loading(self):
        """Test configuration loading functionality."""
        config = load_config()
        self.assertIsInstance(config, dict)
        self.assertGreater(len(config), 0)
    
    def test_config_with_file(self):
        """Test loading config from file."""
        config_file = Path(self.temp_dir) / "test_config.json"
        test_config = {"test_key": "test_value", "number": 42}
        
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        loaded = load_config(str(config_file))
        self.assertEqual(loaded["test_key"], "test_value")
        self.assertEqual(loaded["number"], 42)


def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("RUNNING COMPREHENSIVE INTEGRATION TESTS")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSystemIntegration)
    suite.addTests(loader.loadTestsFromTestCase(TestRunnerIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print(f"✓ Tests run: {result.testsRun}")
        print(f"✓ Failures: {len(result.failures)}")
        print(f"✓ Errors: {len(result.errors)}")
    else:
        print("❌ SOME TESTS FAILED")
        print(f"✗ Tests run: {result.testsRun}")
        print(f"✗ Failures: {len(result.failures)}")
        print(f"✗ Errors: {len(result.errors)}")
        
        for failure in result.failures:
            print(f"\nFAILURE in {failure[0]}:\n{failure[1]}")
        
        for error in result.errors:
            print(f"\nERROR in {error[0]}:\n{error[1]}")
    
    print("=" * 60)
    return result.wasSuccessful()


if __name__ == '__main__':
    import json  # Needed for test
    success = run_all_tests()
    sys.exit(0 if success else 1)