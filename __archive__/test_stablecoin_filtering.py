#!/usr/bin/env python3
"""
Verification script to test the stablecoin filtering functionality
"""
import os
import sys
import numpy as np
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.watchers.market_opportunity_watcher import MarketOpportunityWatcher
from domain.value_objects import Symbol


def test_stablecoin_filtering():
    """Test that the stablecoin filtering is working properly"""
    print("🧪 Testing Stablecoin Pair Filtering")
    print("="*50)
    
    # Create watcher instance
    watcher = MarketOpportunityWatcher(auto_discover_symbols=True)
    
    # Test symbols including stablecoin pairs that should be filtered
    test_symbols = [
        "BTCUSDT",      # Should be kept (crypto to stable)
        "ETHUSDC",      # Should be kept (crypto to stable) 
        "SOLUSDT",      # Should be kept (crypto to stable)
        "USDTUSDT",     # Should be filtered out (stable to stable)
        "USDCUSDT",     # Should be filtered out (stable to stable)
        "BUSDUSDT",     # Should be filtered out (stable to stable)
        "USDTUSDC",     # Should be filtered out (stable to stable)
        "XRPUSDT",      # Should be kept (crypto to stable)
        "ADAUSDC",      # Should be kept (crypto to stable)
        "EURUSDT",      # Should be kept (fiat to stable)
        "TRXUSDT",      # Should be kept (crypto to stable)
        "DOGEUSDT",     # Should be kept (crypto to stable)
        "LTCUSDT",      # Should be kept (crypto to stable)
        "BNBUSDT",      # Should be kept (crypto to stable)
        "DOTUSDT",      # Should be kept (crypto to stable)
        "LINKUSDT",     # Should be kept (crypto to stable)
    ]
    
    print(f"Input symbols ({len(test_symbols)}):")
    for i, symbol in enumerate(test_symbols):
        print(f"  {i+1:2d}. {symbol}")
    
    # Apply filtering
    filtered_symbols = watcher._filter_stablecoin_pairs(test_symbols)
    
    print(f"\nFiltered symbols ({len(filtered_symbols)}):")
    for i, symbol in enumerate(filtered_symbols):
        print(f"  {i+1:2d}. {symbol}")
    
    # Identify which were filtered out
    filtered_out = [s for s in test_symbols if s not in filtered_symbols]
    
    print(f"\nFiltered out symbols ({len(filtered_out)}):")
    for i, symbol in enumerate(filtered_out):
        print(f"  {i+1:2d}. {symbol}")
    
    # Verification
    expected_filtered_out = {"USDTUSDT", "USDCUSDT", "BUSDUSDT", "USDTUSDC"}
    actual_filtered_out = set(filtered_out)
    
    print(f"\nVerification:")
    print(f"  Expected to filter out: {expected_filtered_out}")
    print(f"  Actually filtered out:  {actual_filtered_out}")
    
    if expected_filtered_out == actual_filtered_out:
        print("  ✅ PASS: All expected stablecoin pairs were filtered out")
        success = True
    else:
        print("  ❌ FAIL: Filtering didn't work as expected")
        success = False
    
    print("\n" + "="*50)
    return success


def test_auto_discovery_logic():
    """Test the auto-discovery with filtering applied"""
    print("\n🧪 Testing Auto-Discovery with Filtering")
    print("="*50)
    
    # Simulate discovery with stablecoin pairs
    discovered_with_stablecoins = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", 
        "USDTUSDT", "USDCUSDT", "BUSDUSDT", "USDTUSDC",  # Stablecoin pairs to be filtered
        "AVAXUSDT", "MATICUSDT", "DOTUSDT", "LINKUSDT"
    ]
    
    watcher = MarketOpportunityWatcher()
    filtered_discovered = watcher._filter_stablecoin_pairs(discovered_with_stablecoins)
    
    print(f"Discovered symbols before filtering: {len(discovered_with_stablecoins)}")
    print(f"Discovered symbols after filtering:  {len(filtered_discovered)}")
    
    stablecoin_pairs_found = [s for s in discovered_with_stablecoins if s in ["USDTUSDT", "USDCUSDT", "BUSDUSDT", "USDTUSDC"]]
    stablecoin_pairs_filtered = [s for s in discovered_with_stablecoins if s in ["USDTUSDT", "USDCUSDT", "BUSDUSDT", "USDTUSDC"] and s not in filtered_discovered]
    
    print(f"  Stablecoin pairs found: {len(stablecoin_pairs_found)}")
    print(f"  Stablecoin pairs filtered: {len(stablecoin_pairs_filtered)}")
    
    if len(stablecoin_pairs_found) == len(stablecoin_pairs_filtered):
        print("  ✅ PASS: All stablecoin pairs were properly filtered")
        success = True
    else:
        print("  ❌ FAIL: Some stablecoin pairs were not filtered")
        success = False
    
    print(f"  Final filtered symbols: {filtered_discovered}")
    
    print("\n" + "="*50)
    return success


def main():
    """Run all verification tests"""
    print("🚀 Starting Stablecoin Filtering Verification")
    print("="*60)
    
    test1_ok = test_stablecoin_filtering()
    test2_ok = test_auto_discovery_logic()
    
    print("\n📊 FINAL RESULTS")
    print("="*60)
    print(f"Stablecoin filtering test:     {'✅ PASS' if test1_ok else '❌ FAIL'}")
    print(f"Auto-discovery filtering test: {'✅ PASS' if test2_ok else '❌ FAIL'}")
    
    overall_success = test1_ok and test2_ok
    
    if overall_success:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ Stablecoin pairs are properly filtered out")
        print(f"✅ Auto-discovery respects filtering rules")
        print(f"✅ Only legitimate crypto-to-stable pairs are kept")
    else:
        print(f"\n❌ SOME TESTS FAILED")
        print(f"Please review the filtering implementation")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)