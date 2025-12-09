#!/usr/bin/env python3
"""
Orchestration script to run all watcher tests
This combines all individual test scripts into one comprehensive test run
"""
import subprocess
import sys
import os

def run_test_script(script_name, description):
    """Run a single test script and return success status"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"SCRIPT: {script_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(['python', script_name], 
                              capture_output=True, 
                              text=True, 
                              timeout=60)  # 60 second timeout
        
        if result.returncode == 0:
            print(f"✅ SUCCESS: {script_name}")
            # Print the output if successful
            if result.stdout:
                print(result.stdout[-1000:])  # Last 1000 chars to avoid too much output
            return True
        else:
            print(f"❌ FAILED: {script_name}")
            print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT: {script_name}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {script_name} - {e}")
        return False

def main():
    """Run all watcher tests"""
    print("🧪 COMPREHENSIVE WATCHER TESTING SUITE")
    print("=" * 60)
    
    # Define test scripts and their descriptions
    test_scripts = [
        ("test_cmc_screener_watcher.py", "CMC Screener Watcher (CoinMarketCap Data)"),
        ("test_trend_mtf_watcher.py", "Trend MTF Watcher (Multi-Timeframe Analysis)"),
        ("test_volatility_watcher.py", "Volatility Watcher (ATR & Volatility Patterns)"),
        ("test_market_pulse_watcher.py", "Market Pulse Watcher (Sentiment & Momentum)"),
        ("test_anomaly_ml_watcher.py", "Anomaly ML Watcher (ML-based Anomaly Detection)"),
        ("test_funding_rate_watcher.py", "Funding Rate Watcher (Perpetual Futures)"),
        ("test_liquidity_watcher.py", "Liquidity Watcher (Order Book Analysis)")
    ]
    
    results = []
    for script, description in test_scripts:
        success = run_test_script(script, description)
        results.append((script, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("🏁 FINAL SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    print(f"\nDetailed Results:")
    for script, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {script}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED! All watchers are working correctly.")
        print("\n📋 Summary of watcher capabilities validated:")
        print("   • CMC Screener: Properly uses CoinMarketCap API with CMC_API_KEY")
        print("   • All other watchers: Support broker configuration (BingX default)")
        print("   • All watchers: Properly inherit from BaseWatcher")
        print("   • All watchers: Correctly implement analyze(symbol) method")
        print("   • All watchers: Process data and generate signals appropriately")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())