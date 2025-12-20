#!/usr/bin/env python3
"""
Final verification test with proper environment loading
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment_settings():
    """Test that environment variables are properly set"""
    print("🔍 Testing Environment Variable Settings")
    print("="*50)
    
    # Check all watcher environment variables
    watcher_vars = [
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
    
    print("ENVIRONMENT VARIABLE SETTINGS:")
    for var in watcher_vars:
        value = os.getenv(var, 'NOT_SET')
        expected = 'ENABLED' if var == 'MARKET_PULSE_WATCHER_ENABLED' else 'DISABLED'
        actual_status = 'ENABLED' if value.lower() == 'true' else 'DISABLED'
        status = '✅' if (actual_status == expected or var == 'MARKET_PULSE_WATCHER_ENABLED') else '❌'
        print(f"  {status} {var}: {value} ({actual_status})")
    
    # Verify only MarketPulse is enabled
    market_pulse_enabled = os.getenv('MARKET_PULSE_WATCHER_ENABLED', 'false').lower() == 'true'
    other_watchers_disabled = all(
        os.getenv(var, 'true').lower() == 'false' 
        for var in watcher_vars if var != 'MARKET_PULSE_WATCHER_ENABLED'
    )
    
    print(f"\nVERIFICATION RESULTS:")
    print(f"  MarketPulse enabled: {market_pulse_enabled} {'✅' if market_pulse_enabled else '❌'}")
    print(f"  Other watchers disabled: {other_watchers_disabled} {'✅' if other_watchers_disabled else '❌'}")
    
    if market_pulse_enabled and other_watchers_disabled:
        print(f"\n🎉 ENVIRONMENT CONFIGURATION IS CORRECT!")
        print(f"   - Only MarketPulseWatcher will produce logs")
        print(f"   - All other watchers will remain silent")
        print(f"   - System is optimized for production")
        return True
    else:
        print(f"\n❌ ENVIRONMENT CONFIGURATION NEEDS CORRECTION")
        return False

if __name__ == "__main__":
    success = test_environment_settings()
    sys.exit(0 if success else 1)