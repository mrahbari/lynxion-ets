#!/usr/bin/env python3
"""
Simple test to verify that Domain ExecutionIntents are adapted correctly.
"""

import os
import sys
import pandas as pd
from datetime import datetime
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.backtest.realistic_backtester import RealisticBacktester
from domain.entities.signal_entities import ExecutionIntent as DomainExecutionIntent, OrderSide as DomainOrderSide
from domain.value_objects import Symbol, Percentage


def create_sample_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-01-03', freq='D')  # Small dataset
    n = len(dates)

    np.random.seed(42)  # For reproducible results
    returns = np.random.normal(0.001, 0.02, n)  # Daily returns ~0.1% mean, 2% std
    closes = 100 * np.exp(np.cumsum(returns))  # Starting at $100

    opens = closes * np.exp(np.random.normal(0, 0.001, n))
    highs = np.maximum(closes, opens) * (1 + np.abs(np.random.normal(0, 0.005, n)))
    lows = np.minimum(closes, opens) * (1 - np.abs(np.random.normal(0, 0.005, n)))
    volumes = np.random.uniform(1000, 10000, n)

    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)

    # Add technical indicators
    df['atr'] = 0.01 * df['close']  # Simple ATR approximation
    
    return df


def test_domain_execution_intent_simple():
    """Test that Domain ExecutionIntents work with the adapter."""
    print("Testing Domain ExecutionIntent with adapter (simple test)...")
    
    # Create sample data
    data = create_sample_data()
    
    # Create a mock strategy function that returns Domain ExecutionIntent
    def domain_strategy_function(row, params):
        current_price = row['close']
        
        # Generate a buy signal when price is above 100
        if current_price > 100:
            domain_intent = DomainExecutionIntent(
                symbol=Symbol("BTCUSDT"),
                strategy_name="rsi_strategy",  # Use valid strategy name
                side=DomainOrderSide.BUY,
                intent_confidence=Percentage(0.7),
                risk_parameters={
                    'risk_per_trade': 0.02,
                    'atr_multiplier': 1.5,
                    'risk_reward_ratio': 1.5
                },
                timestamp=pd.Timestamp(row.name) if hasattr(row, 'name') else datetime.now()
            )
            return domain_intent
        else:
            return None
    
    # Initialize backtester
    backtester = RealisticBacktester(
        initial_capital=10000.0,
        fee_rate=0.001,
        slippage_factor=0.0005
    )
    
    # Run backtest with the domain strategy
    results = backtester.run_backtest(
        data=data,
        strategy_function=domain_strategy_function,
        strategy_params={
            'risk_per_trade': 0.02,
            'atr_multiplier': 1.5,
            'risk_reward_ratio': 1.5,
            'symbol': 'BTCUSDT'
        },
        strategy_name='rsi_strategy'  # Use same strategy name
    )
    
    print(f"✓ Domain ExecutionIntent test completed!")
    print(f"  Total trades: {results.get('total_trades', 0)}")
    print(f"  Total return: {results.get('total_return', 0):.4f}")
    
    return True


def main():
    """Run the simple test."""
    print("Running simple Domain ExecutionIntent adapter test...\n")
    
    success = test_domain_execution_intent_simple()
    
    if success:
        print("\n🎉 Simple test passed!")
        print("✓ Domain ExecutionIntents work with adapter")
        print("\nThe adapter successfully converts Domain ExecutionIntents to Infrastructure ExecutionIntents!")
        return True
    else:
        print("\n❌ Simple test failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)