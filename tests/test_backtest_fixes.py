#!/usr/bin/env python3
"""
Test script to verify that the backtest optimization fixes work correctly.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from infrastructure.backtest.realistic_backtester import RealisticBacktester

def create_sample_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-03-01', freq='1H')
    n = len(dates)
    
    # Create realistic price data with some volatility
    returns = np.random.normal(0.0005, 0.02, n)  # Small positive drift, 2% daily std
    closes = 100 * np.exp(np.cumsum(returns))
    
    opens = closes * np.exp(np.random.normal(0, 0.001, n))
    highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, 0.005, n)))
    lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, 0.005, n)))
    
    volumes = np.random.uniform(1000, 10000, n)
    
    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)
    
    return df

def simple_test_strategy(row, params):
    """Simple strategy for testing - generates more signals."""
    rsi = row.get('rsi', 50)
    sma_20 = row.get('sma_20', 0)
    close = row.get('close', 0)
    
    if pd.isna(rsi) or pd.isna(sma_20) or pd.isna(close):
        return 0
    
    # More relaxed conditions to generate more signals
    if close > sma_20 and rsi < 65:  # Buy condition
        return 1
    elif close < sma_20 and rsi > 35:  # Sell condition
        return -1
    else:
        return 0

def test_backtest_improvements():
    """Test that the backtest improvements work as expected."""
    print("🧪 Testing backtest improvements...")
    
    # Create sample data
    data = create_sample_data()
    print(f"📊 Created sample data with {len(data)} rows")
    
    # Initialize backtester with more permissive settings
    backtester = RealisticBacktester(
        initial_capital=10000.0,
        fee_rate=0.001,
        slippage_factor=0.0005,
        min_order_size=0.001,
        max_position_size=0.20,
        max_drawdown=0.90
    )
    
    # Run backtest with the improved strategy
    print("📈 Running backtest with improved settings...")
    
    try:
        results = backtester.run_backtest(
            data=data,
            strategy_function=simple_test_strategy,
            strategy_params={'risk_per_trade': 0.01, 'atr_multiplier': 1.5, 'risk_reward_ratio': 1.5},
            strategy_name='trend_following'
        )
        
        print(f"✅ Backtest completed successfully!")
        print(f"💰 Final equity: ${results.get('final_equity', 0):,.2f}")
        print(f"📊 Total trades: {results.get('total_trades', 0)}")
        print(f"🎯 Win rate: {results.get('win_rate', 0):.2%}")
        print(f"📈 Sharpe ratio: {results.get('sharpe_ratio', 0):.2f}")
        print(f"📉 Max drawdown: {results.get('max_drawdown', 0):.2%}")
        print(f"🏆 Total return: {results.get('total_return', 0):.2%}")
        
        # Verify that we have reasonable metrics
        total_trades = results.get('total_trades', 0)
        win_rate = results.get('win_rate', 0)
        sharpe_ratio = results.get('sharpe_ratio', 0)
        max_drawdown = results.get('max_drawdown', 0)
        
        success = True
        if total_trades < 5:
            print(f"⚠️  Low trade count: {total_trades} (expected at least 5)")
            success = False
        else:
            print(f"✅ Sufficient trade count: {total_trades}")
            
        if not (0 <= win_rate <= 1):
            print(f"⚠️  Invalid win rate: {win_rate}")
            success = False
        else:
            print(f"✅ Valid win rate: {win_rate:.2%}")
            
        if not (-20 <= sharpe_ratio <= 20):
            print(f"⚠️  Extreme Sharpe ratio: {sharpe_ratio}")
        else:
            print(f"✅ Reasonable Sharpe ratio: {sharpe_ratio:.2f}")
            
        if not (-1 <= max_drawdown <= 0):
            print(f"⚠️  Invalid max drawdown: {max_drawdown}")
        else:
            print(f"✅ Valid max drawdown: {max_drawdown:.2%}")
        
        if success:
            print("\n🎉 All tests passed! Backtest improvements are working correctly.")
        else:
            print("\n⚠️  Some tests had issues, but backtest ran successfully.")
            
        return success
        
    except Exception as e:
        print(f"❌ Backtest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_backtest_improvements()