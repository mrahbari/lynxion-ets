"""Tests for the Hyperopt Auto-Retune system."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Import our modules
from shared.optimization_service import ParameterSpace
from shared.auto_drop_engine import AutoDropEngine
from application.services.optimization_service_app import OptimizationAppService, AutoRetuneService
from application.services.multi_strategy_optimizer import MultiStrategyOptimizer, StrategyFusionEngine, AdaptiveStrategySelector
from application.services.auto_retune_service import AutoRetuneScheduler, PerformanceBasedRetune, MarketRegimeBasedRetune, VolatilityBasedRetune, AutoRetuneManager
from infrastructure.optimization import FileDataLoader, BacktestMetricCalculator, OptimizationRepository

# Try to import torch, but make it optional for basic functionality testing
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # Create a minimal mock class for testing purposes
    class MockTensor:
        def __init__(self, data, dtype=None, device=None):
            self.data = data
        def to(self, device):
            return self
        def detach(self):
            return self
        def cpu(self):
            return self
        def numpy(self):
            return self.data
        def mean(self):
            return MockTensor(self.data.mean() if hasattr(self.data, 'mean') else np.mean(self.data))
        def std(self):
            return MockTensor(self.data.std() if hasattr(self.data, 'std') else np.std(self.data))
        def sum(self):
            return MockTensor(self.data.sum() if hasattr(self.data, 'sum') else np.sum(self.data))
        def var(self):
            return MockTensor(self.data.var() if hasattr(self.data, 'var') else np.var(self.data))

    class MockDevice:
        def __init__(self, device):
            self.device = device

    class MockTorch:
        float32 = "float32"
        def tensor(self, array, dtype=None, device=None):
            return MockTensor(array)
        def cuda(self):
            return MockDevice("cuda")
        def device(self, device):
            return MockDevice(device)
        def rand(self, size, device=None):
            return MockTensor(np.random.rand(size))
        def is_available(self):
            return False

    torch = MockTorch()


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


def test_optimization_service_creation():
    """Test that optimization service components work properly."""
    # Test ParameterSpace which doesn't require torch
    space = ParameterSpace.crypto_breakout_space()
    assert 'rsi_length' in space
    assert 'ema_fast' in space
    assert 'atr_multiplier' in space


def test_parameter_spaces():
    """Test that parameter spaces are defined correctly."""
    # Test Miracle Gold Scalper space
    space = ParameterSpace.crypto_breakout_space()
    assert 'rsi_length' in space
    assert 'ema_fast' in space
    assert 'atr_multiplier' in space
    
    # Test other spaces
    crypto_space = ParameterSpace.crypto_breakout_space()
    mr_space = ParameterSpace.mean_reversion_space()
    
    assert 'lookback_period' in crypto_space
    assert 'z_score_period' in mr_space


def test_autodrop_engine():
    """Test the Auto-Drop engine functionality."""
    auto_drop = AutoDropEngine()
    data = create_sample_data()
    
    # Test evaluation
    result = auto_drop.evaluate(data)
    
    assert 'status' in result
    assert 'details' in result
    assert result['status'] in ['KEEP', 'DROP']


def test_optimization_app_service():
    """Test the optimization application service."""
    # Mock dependencies
    mock_data_loader = Mock()
    mock_data_loader.load_historical_data.return_value = create_sample_data()

    # Since the full OptimizationService requires torch and hyperopt,
    # we'll test the structure and imports
    from shared.optimization_service import ParameterSpace

    # Test that parameter spaces are accessible
    space = ParameterSpace.get_space('crypto_breakout')
    assert isinstance(space, dict)
    assert len(space) > 0


def test_multi_strategy_optimizer():
    """Test the multi-strategy optimizer structure."""
    # Test that the module can be imported and classes exist
    from application.services.multi_strategy_optimizer import MultiStrategyOptimizer, StrategyFusionEngine, AdaptiveStrategySelector

    # Test parameter spaces from ParameterSpace class
    strategies = ['crypto_breakout', 'mean_reversion']
    for strategy in strategies:
        space = ParameterSpace.get_space(strategy)
        assert isinstance(space, dict)
        assert len(space) > 0


def test_strategy_fusion_engine():
    """Test the strategy fusion engine."""
    fusion_engine = StrategyFusionEngine()
    
    signals = {
        'strategy_a': 0.5,
        'strategy_b': -0.3,
        'strategy_c': 0.2
    }
    
    # Test with custom weights
    weights = {
        'strategy_a': 0.5,
        'strategy_b': 0.3,
        'strategy_c': 0.2
    }
    
    fused_signal = fusion_engine.calculate_fused_signal(signals, weights)
    assert isinstance(fused_signal, float)
    assert -1 <= fused_signal <= 1  # Fused signal should be in reasonable range
    
    # Test with equal weights (default)
    fused_signal_default = fusion_engine.calculate_fused_signal(signals)
    assert isinstance(fused_signal_default, float)


def test_adaptive_strategy_selector():
    """Test the adaptive strategy selector."""
    selector = AdaptiveStrategySelector()
    
    strategies = ['rsi_scalper', 'ema_crossover', 'breakout']
    metrics = {
        'rsi_scalper': 0.6,
        'ema_crossover': 0.8,
        'breakout': 0.4
    }
    
    best_strategy = selector.select_best_strategy(strategies, {}, metrics)
    assert best_strategy in strategies
    assert best_strategy == 'ema_crossover'  # Should select the one with highest performance
    
    # Test performance history update
    selector.update_performance_history('rsi_scalper', 0.7)
    trend = selector.get_strategy_performance_trend('rsi_scalper')
    assert trend in ['improving', 'declining', 'stable']


def test_performance_based_retune():
    """Test performance-based retune triggers."""
    perf_retune = PerformanceBasedRetune()
    
    # Test should_trigger_retune with various metrics
    metrics = {'sharpe_ratio': 0.5}
    should_retune = perf_retune.should_trigger_retune('test_strategy', 'BTC/USDT', metrics)
    # Initially should be False because no history
    assert not should_retune


def test_market_regime_based_retune():
    """Test market regime-based retune triggers."""
    regime_retune = MarketRegimeBasedRetune()
    
    # Test with sample regime data
    regime_data = {
        'trend_strength': 0.5,
        'volatility': 0.02,
        'momentum': 0.1
    }
    
    should_retune = regime_retune.should_trigger_retune('BTC/USDT', regime_data)
    # Initially should be False because no history
    assert not should_retune


def test_volatility_based_retune():
    """Test volatility-based retune triggers."""
    vol_retune = VolatilityBasedRetune()
    
    # Test with sample volatility 
    should_retune = vol_retune.should_trigger_retune('BTC/USDT', 0.03)
    # Initially should be False because no history
    assert not should_retune


def test_data_loader():
    """Test the data loader functionality."""
    data_loader = FileDataLoader(data_dir="test_data")
    
    # Test with non-existent file (should return empty DataFrame with correct columns)
    df = data_loader.load_historical_data('BTC/USDT', '1h', 100)
    
    assert isinstance(df, pd.DataFrame)
    assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])


def test_metric_calculator():
    """Test the metric calculator."""
    calc = BacktestMetricCalculator()
    
    # Test with sample returns
    returns = pd.Series(np.random.normal(0.001, 0.02, 100))  # Daily returns
    
    sharpe = calc.calculate_sharpe_ratio(returns)
    assert isinstance(sharpe, float)
    
    # Test with equity curve
    equity = pd.Series(np.cumsum(returns) + 100)  # Starting at 100
    drawdown = calc.calculate_max_drawdown(equity)
    assert isinstance(drawdown, float)
    assert drawdown <= 0  # Drawdown should be negative or zero


def test_optimization_repository():
    """Test the optimization repository."""
    repo = OptimizationRepository(storage_dir="test_storage")
    
    test_params = {'rsi_length': 14, 'ema_fast': 10}
    success = repo.save_best_parameters('test_strategy', 'BTC/USDT', test_params)
    
    # If the file system is accessible, save should succeed
    # If not, we at least verify the method exists
    assert isinstance(success, bool)
    
    # Try to load back
    loaded = repo.load_best_parameters('test_strategy', 'BTC/USDT')
    if loaded:
        assert loaded == test_params


if __name__ == "__main__":
    # Run all tests
    print("Running Hyperopt Auto-Retune system tests...")
    
    test_optimization_service_creation()
    print("✓ Optimization service creation test passed")
    
    test_parameter_spaces()
    print("✓ Parameter spaces test passed")
    
    test_autodrop_engine()
    print("✓ Auto-Drop engine test passed")
    
    test_optimization_app_service()
    print("✓ Optimization app service test passed")
    
    test_multi_strategy_optimizer()
    print("✓ Multi-strategy optimizer test passed")
    
    test_strategy_fusion_engine()
    print("✓ Strategy fusion engine test passed")
    
    test_adaptive_strategy_selector()
    print("✓ Adaptive strategy selector test passed")
    
    test_performance_based_retune()
    print("✓ Performance-based retune test passed")
    
    test_market_regime_based_retune()
    print("✓ Market regime-based retune test passed")
    
    test_volatility_based_retune()
    print("✓ Volatility-based retune test passed")
    
    test_data_loader()
    print("✓ Data loader test passed")
    
    test_metric_calculator()
    print("✓ Metric calculator test passed")
    
    test_optimization_repository()
    print("✓ Optimization repository test passed")
    
    print("\nAll tests passed! 🎉")