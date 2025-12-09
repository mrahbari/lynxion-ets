#!/usr/bin/env python3
"""
Test script to verify the enhanced hyperopt system functionality.
"""

import sys
import os
from pathlib import Path

# Add the project directory to the Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def test_strategy_agnostic_framework():
    """Test that the strategy-agnostic framework works."""
    print("Testing strategy-agnostic framework...")

    # Import the optimization framework components
    from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
    from domain.ports.optimization_ports import IOptimizableStrategy

    # Test that we can create a parameter space without strategy-specific dependencies
    param_space = HyperoptParameterSpace()

    # Test with a generic strategy name
    space = param_space.get_space("generic_strategy")
    assert isinstance(space, dict), "Parameter space should be a dictionary"
    assert len(space) > 0, "Parameter space should contain parameters"

    print("✅ Strategy-agnostic framework test passed")
    return True

def test_risk_management_optimization():
    """Test that risk management parameters can be optimized."""
    print("Testing risk management optimization...")
    
    from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
    
    # Create risk manager
    risk_manager = EnterpriseRiskManager()
    
    # Test that it has optimization methods
    params = risk_manager.get_optimizable_params()
    assert isinstance(params, dict), "Optimizable params should return a dict"
    assert 'max_portfolio_exposure' in params, "Should have portfolio exposure param"
    assert 'max_risk_per_trade' in params, "Should have risk per trade param"
    
    # Test updating from params
    new_params = {
        'max_portfolio_exposure': 150000,
        'max_risk_per_trade': 0.02
    }
    risk_manager.update_from_params(new_params)
    updated_params = risk_manager.get_optimizable_params()
    
    assert updated_params['max_portfolio_exposure'] == 150000, "Parameter should be updated"
    assert updated_params['max_risk_per_trade'] == 0.02, "Parameter should be updated"
    
    print("✅ Risk management optimization test passed")
    return True

def test_multi_objective_optimization():
    """Test that multi-objective optimization is available."""
    print("Testing multi-objective optimization...")
    
    from infrastructure.optimization.hyperopt_objective import HyperoptObjective
    
    # Create objective handler
    objective_handler = HyperoptObjective()
    
    # Test creating objective function with multiple objectives
    import pandas as pd
    import numpy as np
    
    # Create mock data
    mock_data = {
        'BTCUSD': pd.DataFrame({
            'open': np.random.rand(100) * 100,
            'high': np.random.rand(100) * 100, 
            'low': np.random.rand(100) * 100,
            'close': np.random.rand(100) * 100,
            'volume': np.random.rand(100) * 1000,
        })
    }
    
    risk_config = {
        'initial_capital': 10000,
        'fee_rate': 0.001,
        'slippage_factor': 0.0005
    }
    
    # Test with multiple objectives
    objective_fn = objective_handler.create_objective_function(
        mock_data, 
        risk_config, 
        optimization_objectives=['sharpe_ratio', 'win_rate']
    )
    
    # Test that it creates a function
    assert callable(objective_fn), "Objective function should be callable"
    
    # Test with single objective as fallback
    single_obj_fn = objective_handler.create_objective_function(
        mock_data,
        risk_config,
        optimization_objectives=['sharpe_ratio']
    )
    
    assert callable(single_obj_fn), "Single objective function should be callable"
    
    print("✅ Multi-objective optimization test passed")
    return True

def test_auto_drop_optimization():
    """Test that auto-drop engine parameters can be optimized."""
    print("Testing auto-drop optimization...")
    
    from shared.auto_drop_engine import CoinQualityFilter
    
    # Create filter
    filter_instance = CoinQualityFilter()
    
    # Test optimization methods
    params = filter_instance.get_optimizable_params()
    assert isinstance(params, dict), "Optimizable params should return a dict"
    assert 'min_volume' in params, "Should have min_volume param"
    assert 'max_spread' in params, "Should have max_spread param"
    
    # Test updating from params
    new_params = {
        'min_volume': 200000,
        'max_spread': 0.004
    }
    filter_instance.update_from_params(new_params)
    updated_params = filter_instance.get_optimizable_params()
    
    assert updated_params['min_volume'] == 200000, "Filter parameter should be updated"
    assert updated_params['max_spread'] == 0.004, "Filter parameter should be updated"
    
    print("✅ Auto-drop optimization test passed")
    return True

def test_unified_optimization_service():
    """Test that unified optimization service works."""
    print("Testing unified optimization service...")
    
    from application.services.unified_optimization_service import UnifiedOptimizationService
    
    # Create the unified service
    service = UnifiedOptimizationService()
    
    # Test that it has all required methods
    assert hasattr(service, 'optimize_strategy_params'), "Should have strategy optimization"
    assert hasattr(service, 'optimize_risk_params'), "Should have risk optimization"
    assert hasattr(service, 'optimize_auto_drop_params'), "Should have auto-drop optimization"
    assert hasattr(service, 'optimize_retuning_params'), "Should have retuning optimization"
    assert hasattr(service, 'optimize_all_components'), "Should have unified optimization"
    
    print("✅ Unified optimization service test passed")
    return True

def test_interface_implementation():
    """Test that the optimization interfaces exist and work."""
    print("Testing interface implementation...")
    
    from domain.ports.optimization_ports import IOptimizableStrategy, IParameterSpace, IHyperoptObjective, IStrategyRegistry
    
    # Check that interfaces exist and have required methods
    assert hasattr(IOptimizableStrategy, 'get_parameter_space'), "Interface should have get_parameter_space method"
    assert hasattr(IOptimizableStrategy, 'get_constraint_functions'), "Interface should have get_constraint_functions method"
    assert hasattr(IOptimizableStrategy, 'get_optimization_objectives'), "Interface should have get_optimization_objectives method"
    
    print("✅ Interface implementation test passed")
    return True

def main():
    """Run all tests to verify system functionality."""
    print("🧪 Running tests to verify enhanced hyperopt system functionality...\n")
    
    tests = [
        test_interface_implementation,
        test_strategy_agnostic_framework,
        test_risk_management_optimization,
        test_multi_objective_optimization,
        test_auto_drop_optimization,
        test_unified_optimization_service,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The enhanced hyperopt system is working correctly.")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)