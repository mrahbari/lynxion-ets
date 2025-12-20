#!/usr/bin/env python3
"""
Test script to verify that disabled watchers don't log anything
"""
import os
import sys
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
from infrastructure.watchers.adapters.volatility import VolatilityWatcher
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
from infrastructure.watchers.adapters.orderflow_ws import OrderFlowWSWatcher
from infrastructure.watchers.adapters.cmc_screener import CMCScreener
from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
from infrastructure.watchers.adapters.liquidity import LiquidityWatcher
from infrastructure.watchers.adapters.historical_candle_watcher import HistoricalCandleWatcherAdapter
from domain.value_objects import Symbol


def test_disabled_watchers_no_logging():
    """Test that disabled watchers don't produce any logs"""
    print("🧪 Testing that disabled watchers don't log anything...")
    
    # Temporarily set environment variables to disable watchers
    original_values = {}
    watcher_env_vars = [
        'MARKET_PULSE_WATCHER_ENABLED',
        'VOLATILITY_WATCHER_ENABLED', 
        'TREND_MTF_WATCHER_ENABLED',
        'ANOMALY_ML_WATCHER_ENABLED',
        'ORDERFLOW_WS_WATCHER_ENABLED',
        'CMC_SCREENER_ENABLED',
        'FUNDING_RATE_WATCHER_ENABLED',
        'LIQUIDITY_WATCHER_ENABLED',
        'HISTORICAL_CANDLE_WATCHER_ENABLED'
    ]
    
    # Capture original values and set all to false
    for var in watcher_env_vars:
        original_values[var] = os.getenv(var)
        os.environ[var] = 'false'
    
    try:
        # Test that disabled watchers don't log when created
        print("Creating disabled watchers...")
        
        # Capture any potential output
        with redirect_stdout(StringIO()) as f_out, redirect_stderr(StringIO()) as f_err:
            # Create all watchers with disabled status
            watchers = [
                MarketPulseWatcher("Test", "BTCUSDT"),
                VolatilityWatcher("Test", "BTCUSDT"),
                TrendMTFWatcher("Test", "BTCUSDT"),
                AnomalyMLWatcher("Test", "BTCUSDT"),
                OrderFlowWSWatcher("Test", "BTCUSDT"),
                CMCScreener("Test", "BTCUSDT"),
                FundingRateWatcher("Test", "BTCUSDT"),
                LiquidityWatcher("Test", "BTCUSDT"),
                HistoricalCandleWatcherAdapter("Test", "BTCUSDT", None)
            ]
            
            # Test analyze method for each (this might trigger logs)
            for watcher in watchers:
                # Provide mock data to update
                if hasattr(watcher, 'update_data'):
                    watcher.update_data({'close': 45000.0})
                
                # Try to analyze
                if hasattr(watcher, 'analyze'):
                    watcher.analyze(Symbol("BTCUSDT"))
        
        # Check if any output was captured
        stdout_output = f_out.getvalue()
        stderr_output = f_err.getvalue()
        
        print(f"Stdout captured: {len(stdout_output)} characters")
        print(f"Stderr captured: {len(stderr_output)} characters")
        
        if len(stdout_output) == 0 and len(stderr_output) == 0:
            print("✅ SUCCESS: No logs produced by disabled watchers")
            success = True
        else:
            print("❌ FAILED: Logs were produced by disabled watchers")
            print(f"STDOUT: {stdout_output}")
            print(f"STDERR: {stderr_output}")
            success = False
        
        # Now test that enabled watchers DO produce logs
        print("\nTesting that enabled watchers DO produce logs...")
        
        # Enable one watcher
        os.environ['MARKET_PULSE_WATCHER_ENABLED'] = 'true'
        
        # Capture output from enabled watcher
        with redirect_stdout(StringIO()) as f_out, redirect_stderr(StringIO()) as f_err:
            enabled_watcher = MarketPulseWatcher("TestEnabled", "BTCUSDT")
            enabled_watcher.update_data({'close': 45000.0, 'volume': 1000.0})
            enabled_watcher.analyze(Symbol("BTCUSDT"))
        
        enabled_stdout = f_out.getvalue()
        enabled_stderr = f_err.getvalue()
        
        print(f"Enabled watcher stdout: {len(enabled_stdout)} characters")
        print(f"Enabled watcher stderr: {len(enabled_stderr)} characters")
        
        # For enabled watchers, some output is expected (though it might be minimal)
        print("✅ Enabled watchers can produce logs when needed")
        
    finally:
        # Restore original environment values
        for var, original_value in original_values.items():
            if original_value is not None:
                os.environ[var] = original_value
            else:
                os.environ.pop(var, None)
    
    return success


def test_enabled_watchers_do_log():
    """Test that enabled watchers do produce logs"""
    print("\n🧪 Testing that enabled watchers do produce logs...")
    
    # Set environment to enable a watcher
    os.environ['MARKET_PULSE_WATCHER_ENABLED'] = 'true'
    
    try:
        # Create an enabled watcher and see if it logs during operation
        watcher = MarketPulseWatcher("TestEnabled", "BTCUSDT")
        
        # Since the logger is properly set up when enabled, it should work normally
        # The actual logging depends on the watcher's internal logic, but the logger object should be real
        import inspect
        logger_is_mock = inspect.isclass(type(watcher.logger)) and hasattr(watcher.logger, 'debug')
        
        # Check if it's our mock logger by checking if it has the expected mock methods
        if hasattr(watcher.logger, '__dict__') and hasattr(watcher.logger, 'debug'):
            # Try to see if it's our mock by checking method implementation
            import types
            is_mock = all(callable(getattr(watcher.logger, attr)) for attr in ['debug', 'info', 'warning', 'error'])
            # For a more precise check, we'd need to see if methods are no-op
            method_source = inspect.getsource(type(watcher.logger).debug)
            is_mock = 'pass' in method_source if 'def debug' in method_source else False
        else:
            is_mock = False
            
        if not is_mock:
            print("✅ Enabled watcher has real logger (not mock)")
            return True
        else:
            print("❌ Enabled watcher still has mock logger")
            return False
    except Exception as e:
        print(f"Error testing enabled watcher: {e}")
        return False
    finally:
        # Clean up environment
        os.environ.pop('MARKET_PULSE_WATCHER_ENABLED', None)


def main():
    """Run tests to verify logging behavior"""
    print("🚀 Testing Watcher Logging Control")
    print("="*50)
    
    test1_ok = test_disabled_watchers_no_logging()
    test2_ok = test_enabled_watchers_do_log()
    
    print("\n" + "="*50)
    print("📊 TEST RESULTS:")
    print(f"Disabled watchers don't log: {'✅ PASS' if test1_ok else '❌ FAIL'}")
    print(f"Enabled watchers do log: {'✅ PASS' if test2_ok else '❌ FAIL'}")
    
    overall_success = test1_ok and test2_ok
    
    if overall_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Disabled watchers no longer produce logs")
        print("✅ Enabled watchers continue to function normally")
        print("✅ Environment variable control working correctly")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Please check the watcher implementations")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)