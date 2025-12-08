"""Basic import test for Hyperopt Auto-Retune system."""

def test_imports():
    """Test that all modules can be imported without errors."""
    
    # Domain ports
    from domain.ports.optimization_ports import IOptimizationService, IDataLoader, IMetricCalculator
    print("✓ Domain ports imported successfully")
    
    # Shared services
    from shared.optimization_service import OptimizationService, ParameterSpace
    print("✓ Optimization service imported successfully")
    
    # Auto drop system
    from shared.auto_drop_engine import AutoDropEngine
    print("✓ Auto drop engine imported successfully")
    
    # Application services
    from application.services.optimization_service_app import OptimizationAppService, AutoRetuneService
    print("✓ Application optimization services imported successfully")
    
    from application.services.multi_strategy_optimizer import MultiStrategyOptimizer, StrategyFusionEngine, AdaptiveStrategySelector
    print("✓ Multi-strategy optimizer imported successfully")
    
    from application.services.auto_retune_service import AutoRetuneScheduler, PerformanceBasedRetune, MarketRegimeBasedRetune, VolatilityBasedRetune, AutoRetuneManager
    print("✓ Auto-retune services imported successfully")
    
    # Infrastructure implementations
    from infrastructure.optimization import FileDataLoader, BacktestMetricCalculator, OptimizationRepository
    print("✓ Infrastructure components imported successfully")
    
    # Use cases
    from application.use_cases.optimization_use_cases import (
        RunStrategyOptimizationUseCase,
        CheckAutoRetuneUseCase, 
        RunAutoRetuneUseCase,
        FilterTradingAssetsUseCase
    )
    print("✓ Use cases imported successfully")
    
    # Test basic functionality
    # Parameter spaces
    space = ParameterSpace.crypto_breakout_space()
    assert isinstance(space, dict)
    assert len(space) > 0
    print("✓ Parameter spaces work correctly")
    
    # Auto drop engine
    auto_drop = AutoDropEngine()
    assert auto_drop is not None
    print("✓ Auto drop engine instantiated correctly")
    
    # Strategy fusion engine
    fusion_engine = StrategyFusionEngine()
    signals = {'strat1': 0.5, 'strat2': -0.3}
    fused = fusion_engine.calculate_fused_signal(signals)
    assert isinstance(fused, float)
    print("✓ Strategy fusion engine works correctly")
    
    print("\n🎉 All imports and basic functionality tests passed!")


if __name__ == "__main__":
    test_imports()