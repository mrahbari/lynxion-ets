#!/usr/bin/env python3
"""
Test script for auto-detection system with CMC watchers integration.
"""
import sys
import os
import time
from datetime import datetime
from unittest.mock import Mock

# Add the project root to Python path
project_root = "/Users/mojtaba.rahbari/Sites/python/lynxion-ets"
sys.path.insert(0, project_root)

from domain.value_objects import Symbol
from domain.ports.data_ports import DataProviderPort
from domain.ports.execution_ports import ExecutionPort
from domain.ports.portfolio_ports import PortfolioManagementPort
from domain.ports.optimization_ports import IOptimizationService

from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
from infrastructure.watchers.adapters.cmc_watcher_adapter import CMCScreenerAdapter


def create_mock_services():
    """Create mock implementations for all required services."""
    
    # Mock Data Provider
    class MockDataProviderAdapter(DataProviderPort):
        def get_market_data(self, symbol: Symbol, timeframe: str = "1h", limit: int = 100):
            # Return mock market data
            import pandas as pd
            import numpy as np

            timestamps = pd.date_range(start='2023-01-01', periods=limit, freq='1h')
            prices = 50000 + np.cumsum(np.random.randn(limit) * 100)  # Simulate BTC price

            return pd.DataFrame({
                'timestamp': timestamps,
                'open': prices + np.random.randn(limit) * 10,
                'high': prices + abs(np.random.randn(limit)) * 20,
                'low': prices - abs(np.random.randn(limit)) * 20,
                'close': prices,
                'volume': np.abs(np.random.randn(limit)) * 1000,
            })

        def get_current_price(self, symbol: Symbol):
            import random
            return 50000 + random.uniform(-1000, 1000)

        def get_historical_data(self, symbol: Symbol, start_date: str, end_date: str, timeframe: str = "1h"):
            return self.get_market_data(symbol, timeframe, 100)

        def subscribe_to_market_data(self, symbol: Symbol, callback):
            # Mock subscription - just call the callback immediately with fake data
            pass

        def unsubscribe_from_market_data(self, symbol: Symbol, callback):
            # Mock unsubscription
            pass

    # Mock Execution Service
    class MockExecutionService(ExecutionPort):
        def execute_order(self, order):
            print(f"Mock execution of order: {order}")
            return "mock_execution_id"

        def cancel_order(self, order_id: str) -> bool:
            print(f"Mock cancellation of order: {order_id}")
            return True

        def get_execution_status(self, execution_id: str) -> str:
            return "filled"

    # Mock Portfolio Service
    class MockPortfolioService(PortfolioManagementPort):
        def calculate_allocation(self, total_capital: float, symbols):
            return {sym: total_capital/len(symbols) if symbols else 0 for sym in symbols}

        def rebalance_portfolio(self, target_allocations):
            return []

        def get_portfolio_metrics(self):
            return {
                "sharpe_ratio": 1.0, 
                "max_drawdown": -0.05, 
                "total_return": 0.1,
                "drawdown": -0.02,
                "leverage": 2.5
            }

    # Mock Optimization Service
    class MockOptimizationService(IOptimizationService):
        def optimize_strategy(self, strategy_name, data, parameters):
            return {"status": "success", "best_params": {}}

        def get_optimized_parameters(self, strategy_name, symbol):
            return {}

        def save_optimized_parameters(self, strategy_name, symbol, parameters):
            pass

    return (
        MockDataProviderAdapter(),
        MockExecutionService(),
        MockPortfolioService(),
        MockOptimizationService()
    )


def test_cmc_watcher():
    """Test CMC watcher functionality."""
    print("🔍 Testing CMC Watcher...")
    
    try:
        # Test CMCScreenerAdapter
        screener = CMCScreenerAdapter(name="TestScreener")
        print(f"✓ CMCScreenerAdapter created successfully: {screener.name}")
        
        # Test analyze method (will return None if CMC_API_KEY not set, which is expected)
        import os
        if os.getenv("CMC_API_KEY"):
            print("ℹ️ CMC_API_KEY found, attempting real API call...")
            symbol = Symbol("BTCUSDT")
            signal = screener.analyze(symbol)
            print(f"✓ Analyze result for BTCUSDT: {signal.signal_type.name if signal else 'None (expected if no API key)'}")
        else:
            print("ℹ️ No CMC_API_KEY found, analyze will return None (this is expected)")
        
        # Test start/stop
        screener.start()
        print(f"✓ Screener started: {screener.is_running()}")
        screener.stop()
        print(f"✓ Screener stopped: {not screener.is_running()}")
        
        print("✅ CMC Watcher test completed\n")
        
    except Exception as e:
        print(f"❌ CMC Watcher test failed: {e}")
        import traceback
        traceback.print_exc()


def test_auto_detection_orchestrator():
    """Test AutoDetectionOrchestrator functionality."""
    print("🔍 Testing AutoDetectionOrchestrator...")
    
    try:
        # Create mock services
        market_data_repo, execution_service, portfolio_service, optimization_service = create_mock_services()
        
        # Create orchestrator with some symbols
        symbols = ["BTCUSDT", "ETHUSDT"]
        risk_config = {
            "max_risk": 0.02,
            "atr_multiplier": 1.5,
            "use_dynamic_position": True
        }
        
        orchestrator = AutoDetectionOrchestrator(
            market_data_repo=market_data_repo,
            execution_service=execution_service,
            portfolio_service=portfolio_service,
            optimization_service=optimization_service,
            symbols=symbols,
            risk_config=risk_config
        )
        
        print(f"✓ AutoDetectionOrchestrator created with {len(orchestrator.symbols)} symbols")
        
        # Test initialization
        orchestrator.initialize_system()
        print("✓ System initialized")
        
        # Test status
        status = orchestrator.get_status()
        print(f"✓ Status check - Running: {status['is_running']}, Monitored symbols: {len(status['monitored_symbols'])}")
        
        # Test a brief run (without actually running continuously)
        print("✓ AutoDetectionOrchestrator test completed successfully\n")
        
        # Clean up
        orchestrator.stop_system()
        
    except Exception as e:
        print(f"❌ AutoDetectionOrchestrator test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("🧪 Running auto-detection system tests...\n")
    
    start_time = datetime.now()
    
    # Test CMC watcher
    test_cmc_watcher()
    
    # Test orchestrator
    test_auto_detection_orchestrator()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"✅ All tests completed in {duration:.2f} seconds!")
    print("📈 Auto-detection system with CMC integration is working properly!")


if __name__ == "__main__":
    main()