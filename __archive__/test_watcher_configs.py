#!/usr/bin/env python3
"""
Test script to verify all watcher configuration variables are properly set in environment
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_watcher_configs():
    """Test that all watcher configuration variables are available"""
    print("🧪 Testing Watcher Configuration Variables...")
    
    # List of all watcher configuration variables
    watcher_configs = [
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
    
    all_found = True
    for config in watcher_configs:
        value = os.getenv(config)
        if value is not None:
            enabled = value.lower() == 'true'
            print(f"✅ {config} = {value} ({'enabled' if enabled else 'disabled'})")
        else:
            print(f"❌ {config} = NOT FOUND")
            all_found = False
    
    # Also test the base watcher config
    base_configs = [
        'WATCHER_POLLING_INTERVAL_SECONDS',
        'WATCHER_MAX_SYMBOLS_TO_MONITOR',
        'WATCHER_DATA_REFRESH_INTERVAL_MINUTES',
        'WATCHER_RISK_THRESHOLD'
    ]
    
    print("\n📊 Testing Base Watcher Configuration...")
    for config in base_configs:
        value = os.getenv(config)
        if value is not None:
            print(f"✅ {config} = {value}")
        else:
            print(f"❌ {config} = NOT FOUND")
            all_found = False
    
    return all_found

def test_watcher_functionality():
    """Test that watchers properly read their configuration"""
    print("\n🔍 Testing Watcher Configuration Reading...")
    
    try:
        from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
        from infrastructure.watchers.adapters.volatility import VolatilityWatcher
        from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
        from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
        from infrastructure.watchers.adapters.orderflow_ws import OrderFlowWSWatcher
        from infrastructure.watchers.adapters.cmc_screener import CMCScreener
        from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
        from infrastructure.watchers.adapters.liquidity import LiquidityWatcher
        from infrastructure.watchers.adapters.historical_candle_watcher import HistoricalCandleWatcherAdapter
        
        # Test that each watcher can read its environment configuration
        watchers = [
            ("MarketPulseWatcher", MarketPulseWatcher("Test", "BTCUSDT")),
            ("VolatilityWatcher", VolatilityWatcher("Test", "BTCUSDT")),
            ("TrendMTFWatcher", TrendMTFWatcher("Test", "BTCUSDT")),
            ("AnomalyMLWatcher", AnomalyMLWatcher("Test", "BTCUSDT")),
            ("OrderFlowWSWatcher", OrderFlowWSWatcher("Test", "BTCUSDT")),
            ("CMCScreener", CMCScreener("Test", "BTCUSDT")),
            ("FundingRateWatcher", FundingRateWatcher("Test", "BTCUSDT")),
            ("LiquidityWatcher", LiquidityWatcher("Test", "BTCUSDT")),
            ("HistoricalCandleWatcher", HistoricalCandleWatcherAdapter("Test", "BTCUSDT", None))
        ]
        
        all_working = True
        for name, watcher in watchers:
            if hasattr(watcher, 'enabled'):
                status = "enabled" if watcher.enabled else "disabled"
                print(f"✅ {name} - Configuration read successfully: {status}")
            else:
                print(f"❌ {name} - No 'enabled' attribute found")
                all_working = False
        
        return all_working
        
    except Exception as e:
        print(f"❌ Error testing watcher functionality: {e}")
        return False

def main():
    print("🚀 Testing Watcher Configuration Environment Variables")
    print("="*60)
    
    config_ok = test_watcher_configs()
    functionality_ok = test_watcher_functionality()
    
    print("\n" + "="*60)
    print("📊 FINAL RESULTS")
    print("="*60)
    print(f"Environment Variables: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Watcher Functionality: {'✅ PASS' if functionality_ok else '❌ FAIL'}")
    
    overall_success = config_ok and functionality_ok
    
    if overall_success:
        print("\n🎉 ALL WATCHER CONFIGURATIONS VERIFIED SUCCESSFULLY!")
        print("✅ All environment variables are properly set")
        print("✅ All watchers can read their configuration")
        print("✅ System is ready for production with configurable watchers")
    else:
        print("\n❌ Some configurations failed - please check the output above")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)