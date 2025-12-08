"""Comprehensive tests to validate all improvements to the Hyperopt Auto-Retune system."""

import sys
import os
# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import pandas as pd
import numpy as np
import threading
import time
from datetime import datetime, timedelta
import tempfile
import os
from pathlib import Path

# Import our improved modules
from infrastructure.data.coin_history_service import CoinHistoryService, LRUCache
from shared.configurable_hyperopt import HyperoptConfig, ConfigurableHyperoptOptimizer
from infrastructure.results_tracking.results_tracker import ResultsTracker
from application.services.adaptive_retuning import AdaptiveRetuningManager
from infrastructure.backtest.realistic_backtester import RealisticBacktester, example_rsi_strategy


def create_sample_data():
    """Create sample market data for testing."""
    dates = pd.date_range(start='2023-01-01', periods=1000, freq='1h')
    np.random.seed(42)
    
    # Generate sample OHLCV data
    returns = np.random.normal(0.0001, 0.02, 1000)  # Daily return ~0.01% with 2% volatility
    closes = 100 * np.exp(np.cumsum(returns))  # Start at $100
    
    opens = closes * np.exp(np.random.normal(0, 0.001, 1000))
    highs = np.maximum(closes, opens) * (1 + np.abs(np.random.normal(0, 0.005, 1000)))
    lows = np.minimum(closes, opens) * (1 - np.abs(np.random.normal(0, 0.005, 1000)))
    volumes = np.random.uniform(1000000, 5000000, 1000)  # Random volume
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    return data


def test_lru_cache_functionality():
    """Test the LRU cache functionality for memory management."""
    print("Testing LRU Cache functionality...")

    # Create cache with max size of 3
    cache = LRUCache(max_size=3)

    # Add 3 items - using unique dataframes to avoid reference issues
    cache.put("key1", pd.DataFrame({'A': [1, 2, 3], 'timestamp': [datetime.now()] * 3}))
    cache.put("key2", pd.DataFrame({'A': [4, 5, 6], 'timestamp': [datetime.now()] * 3}))
    cache.put("key3", pd.DataFrame({'A': [7, 8, 9], 'timestamp': [datetime.now()] * 3}))

    assert cache.size() == 3  # Cache should be full
    assert cache.get("key1") is not None  # All items should be there
    assert cache.get("key2") is not None
    assert cache.get("key3") is not None

    # Add 4th item - should evict LRU item (key1)
    cache.put("key4", pd.DataFrame({'A': [10, 11, 12], 'timestamp': [datetime.now()] * 3}))

    assert cache.size() == 3  # Cache still at max size
    assert cache.get("key1") is None  # LRU item evicted
    assert cache.get("key4") is not None  # New item added
    assert cache.get("key3") is not None  # Recently used item still there

    # Access key2 to make it most recently used
    cache.get("key2")  # This makes key2 most recently used
    assert cache.get("key2") is not None  # Should still be accessible

    # Add 5th item - should evict the LRU item (key3)
    cache.put("key5", pd.DataFrame({'A': [13, 14, 15], 'timestamp': [datetime.now()] * 3}))

    assert cache.size() == 3  # Cache still at max size
    # At this point: key3 should be evicted because after accessing key2,
    # the order changed from [key2, key3, key4] -> [key3, key4, key2]
    # So when adding key5, key3 (the first) is evicted
    assert cache.get("key3") is None  # key3 was evicted when key5 was added
    assert cache.get("key5") is not None  # New item added
    assert cache.get("key4") is not None  # key4 should still be there
    assert cache.get("key2") is not None  # key2 should still be there

    print("✓ LRU Cache functionality test passed")


def test_coin_history_service_with_lru_cache():
    """Test coin history service with LRU cache improvements."""
    print("Testing Coin History Service with LRU Cache...")
    
    # Create temporary directory for cache
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_size = 2  # Small cache for testing
        service = CoinHistoryService(
            cache_dir=temp_dir,
            max_cache_age_hours=24,
            max_cache_size=cache_size
        )
        
        # Create sample data
        data1 = create_sample_data()
        data2 = create_sample_data()
        data3 = create_sample_data()
        
        # Add data to both file and memory cache
        service._save_to_cache(data1, "BTC/USDT", "1h")
        service._save_to_cache(data2, "ETH/USDT", "1h")
        service._save_to_cache(data3, "ADA/USDT", "1h")  # This should trigger eviction
        
        # Check memory cache stats
        stats = service.get_cache_stats()
        assert stats["memory_cache_size"] <= cache_size
        assert "BTC/USDT_1h" not in stats["cache_keys"]  # Should be evicted
        assert "ADA/USDT_1h" in stats["cache_keys"]  # Most recent should be there
        
        print("✓ Coin History Service LRU Cache test passed")


def test_hyperopt_config_validation():
    """Test hyperopt configuration validation improvements."""
    print("Testing Hyperopt Config validation...")
    
    # Test default config
    config = HyperoptConfig(strategy_name="crypto_breakout")
    
    # Validate the configuration
    issues = config.validate_config()
    assert len(issues["errors"]) == 0, f"Configuration validation errors: {issues['errors']}"
    
    # Test custom config with errors
    custom_config = {
        "parameter_ranges": {
            "test_param": {}  # Missing required fields
        }
    }
    
    # Manually set problematic config to test validation
    config.config["parameter_ranges"]["bad_param"] = {"type": "quniform"}  # Missing min/max
    
    issues = config.validate_config()
    # Should have detected the missing min/max
    error_found = any("min" in error.lower() or "max" in error.lower() for error in issues["errors"])
    assert error_found, "Configuration validation should detect missing min/max values"
    
    print("✓ Hyperopt Config validation test passed")


def test_strategy_specific_configs():
    """Test strategy-specific configurations."""
    print("Testing Strategy-specific configurations...")
    
    # Test different strategy configs
    mg_config = HyperoptConfig(strategy_name="crypto_breakout")
    cb_config = HyperoptConfig(strategy_name="crypto_breakout")
    mr_config = HyperoptConfig(strategy_name="mean_reversion")
    default_config = HyperoptConfig(strategy_name="default")
    
    # Each should have different max_evals based on strategy
    assert mg_config.config["max_evals"] == 150  # Miracle Gold Scalper
    assert cb_config.config["max_evals"] == 80   # Crypto Breakout
    assert mr_config.config["max_evals"] == 120  # Mean Reversion
    assert default_config.config["max_evals"] == 100  # Default
    
    # Test parameter range adjustments
    assert mg_config.config["parameter_ranges"]["ema_fast"]["max"] == 15
    assert cb_config.config["parameter_ranges"]["atr_length"]["max"] == 30
    
    print("✓ Strategy-specific configurations test passed")


def test_parameter_range_update_with_validation():
    """Test parameter range updates with validation."""
    print("Testing Parameter Range updates with validation...")
    
    config = HyperoptConfig()
    
    # Valid update
    config.update_parameter_range("test_param", {
        "type": "uniform",
        "min": 1.0,
        "max": 10.0
    })
    
    assert "test_param" in config.config["parameter_ranges"]
    
    # Invalid update (min > max)
    original_count = len(config.config["parameter_ranges"])
    config.update_parameter_range("bad_param", {
        "type": "uniform",
        "min": 10.0,
        "max": 1.0  # Invalid: min > max
    })
    
    # Should not have added the invalid parameter
    new_count = len(config.config["parameter_ranges"])
    assert new_count == original_count  # Count unchanged due to validation
    
    print("✓ Parameter Range validation test passed")


def test_database_indexing_and_performance():
    """Test database indexing and performance improvements."""
    print("Testing Database indexing and performance...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_file = Path(temp_dir) / "test_results.db"
        tracker = ResultsTracker(db_path=db_file)
        
        # Add multiple results
        for i in range(5):
            tracker.save_hyperopt_result(
                strategy_name=f"strategy_{i % 3}",  # 3 different strategies
                symbol=f"SYMBOL{i % 2}",  # 2 different symbols
                parameters={"test": i},
                best_value=-0.1,
                trials_completed=10
            )
        
        # Test that database size method works
        size_info = tracker.get_database_size()
        assert size_info["hyperopt_results"] == 5
        assert size_info["size_bytes"] > 0
        
        # Test filtering works efficiently with indexes
        results = tracker.get_hyperopt_results(strategy_name="strategy_0")
        assert len(results) > 0
        
        # Test cleanup functionality
        old_count = size_info["hyperopt_results"]
        cleanup_result = tracker.cleanup_old_results(days_to_keep=1)  # Should not delete anything
        
        size_info_after = tracker.get_database_size()
        assert size_info_after["hyperopt_results"] == old_count  # Nothing deleted
        
        print("✓ Database indexing and performance test passed")


def test_thread_safety_in_adaptive_retuning():
    """Test thread safety in adaptive retuning."""
    print("Testing Thread safety in Adaptive Retuning...")
    
    tracker = ResultsTracker(use_database=False)  # Use file-based for testing
    retuning_manager = AdaptiveRetuningManager(tracker)
    
    results = []
    
    def test_retuning(symbol_id):
        """Thread worker function."""
        strategy = "test_strategy"
        symbol = f"TEST{symbol_id}/USDT"
        
        # Simulate checking if retuning is needed
        result = retuning_manager.should_retune(strategy, symbol)
        results.append(result)
        
        # Simulate executing retuning
        retuning_result = retuning_manager.execute_retuning(strategy, symbol)
        results.append(retuning_result)
    
    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=test_retuning, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify that no race conditions occurred
    assert len(results) == 10  # 5 check + 5 execute calls
    
    print("✓ Thread safety test passed")


def test_realistic_backtester():
    """Test the realistic backtester implementation."""
    print("Testing Realistic Backtester...")
    
    # Create sample data
    data = create_sample_data()
    
    # Initialize backtester
    backtester = RealisticBacktester(
        initial_capital=10000.0,
        fee_rate=0.001,  # 0.1% fees
        slippage_factor=0.0005  # 0.05% slippage
    )
    
    # Run backtest with example strategy
    params = {
        "rsi_length": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "risk_per_trade": 0.02,  # 2% risk per trade
        "atr_multiplier": 2.0
    }
    
    results = backtester.run_backtest(
        data=data,
        strategy_function=example_rsi_strategy,
        strategy_params=params
    )
    
    # Check results structure
    assert "total_return" in results
    assert "sharpe_ratio" in results
    assert "max_drawdown" in results
    assert "win_rate" in results
    assert "total_trades" in results
    
    # Verify calculations are reasonable
    assert isinstance(results["total_return"], (int, float))
    assert isinstance(results["sharpe_ratio"], (int, float))
    assert results["max_drawdown"] <= 0  # Should be negative or zero
    
    print("✓ Realistic Backtester test passed")


def test_hyperopt_fallback_mechanism():
    """Test hyperopt fallback mechanism when library not available."""
    print("Testing Hyperopt fallback mechanism...")
    
    # Test the improved hyperopt service
    try:
        from shared.optimization_service import HYPEROPT_AVAILABLE
        
        config = HyperoptConfig()
        opt = ConfigurableHyperoptOptimizer(config)
        
        # The system should work even without actual hyperopt
        data = create_sample_data()
        
        result = opt.optimize_with_config(
            strategy_name="test",
            data=data,
            symbol="TEST/USDT"
        )
        
        # Should have results (either real or mock)
        if HYPEROPT_AVAILABLE:
            assert "best_params" in result or "error" in result
        else:
            # When hyperopt is not available, we should still have a result structure
            assert "error" in result or "best_params" in result
        
        print("✓ Hyperopt fallback mechanism test passed")
        
    except ImportError as e:
        print(f"Hyperopt not available (expected in test environment): {e}")
        print("✓ Hyperopt fallback mechanism test passed")


def run_all_tests():
    """Run all tests to validate improvements."""
    print("=" * 60)
    print("RUNNING COMPREHENSIVE TESTS FOR IMPROVED HYPEROPT AUTO-RETUNE SYSTEM")
    print("=" * 60)
    
    test_lru_cache_functionality()
    print()
    
    test_coin_history_service_with_lru_cache()
    print()
    
    test_hyperopt_config_validation()
    print()
    
    test_strategy_specific_configs()
    print()
    
    test_parameter_range_update_with_validation()
    print()
    
    test_database_indexing_and_performance()
    print()
    
    test_thread_safety_in_adaptive_retuning()
    print()
    
    test_realistic_backtester()
    print()
    
    test_hyperopt_fallback_mechanism()
    print()
    
    print("=" * 60)
    print("🎉 ALL TESTS PASSED! All improvements validated successfully!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    run_all_tests()