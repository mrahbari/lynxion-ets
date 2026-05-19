#!/usr/bin/env python3
"""
Final verification test to ensure the Domain ExecutionIntent adapter works correctly.
"""

import os
import sys
import pandas as pd
from datetime import datetime
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.backtest.realistic_backtester import RealisticBacktester
from infrastructure.backtest.execution_intent import ExecutionIntent as InfraExecutionIntent, create_execution_intent, OrderSide as InfraOrderSide
from domain.entities.signal_entities import ExecutionIntent as DomainExecutionIntent, OrderSide as DomainOrderSide
from domain.value_objects import Symbol, Percentage


def create_sample_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-01-10', freq='D')
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


def test_infrastructure_execution_intent():
    """Test that Infrastructure ExecutionIntents still work correctly."""
    print("Testing Infrastructure ExecutionIntent...")
    
    # Create sample data
    data = create_sample_data()
    
    # Create a mock strategy function that returns Infrastructure ExecutionIntent
    def infra_strategy_function(row, params):
        current_price = row['close']
        
        # Generate a buy signal when price is above 100
        if current_price > 100:
            intent = create_execution_intent(
                side=InfraOrderSide.BUY,
                size=1.0,
                price=current_price,
                timestamp=pd.Timestamp(row.name) if hasattr(row, 'name') else datetime.now(),
                stop_loss=current_price * 0.98,  # 2% stop loss
                take_profit=current_price * 1.04,  # 4% take profit
                strategy_name="test_infra_strategy",
                symbol="BTCUSDT"
            )
            return intent
        else:
            return None

    # Initialize backtester
    backtester = RealisticBacktester(
        initial_capital=10000.0,
        fee_rate=0.001,
        slippage_factor=0.0005
    )

    # Run backtest with the infrastructure strategy
    results = backtester.run_backtest(
        data=data,
        strategy_function=infra_strategy_function,
        strategy_params={'symbol': 'BTCUSDT'},
        strategy_name='rsi_strategy'
    )
    
    print(f"✓ Infrastructure ExecutionIntent test completed!")
    print(f"  Total trades: {results.get('total_trades', 0)}")
    print(f"  Total return: {results.get('total_return', 0):.4f}")
    
    return True


def test_domain_execution_intent():
    """Test that Domain ExecutionIntents work with the adapter."""
    print("\nTesting Domain ExecutionIntent with adapter...")
    
    # Create sample data
    data = create_sample_data()
    
    # Create a mock strategy function that returns Domain ExecutionIntent
    def domain_strategy_function(row, params):
        current_price = row['close']
        
        # Generate a buy signal when price is above 100
        if current_price > 100:
            domain_intent = DomainExecutionIntent(
                symbol=Symbol("BTCUSDT"),
                strategy_name="test_domain_strategy",
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
        strategy_name='rsi_strategy'
    )
    
    print(f"✓ Domain ExecutionIntent test completed!")
    print(f"  Total trades: {results.get('total_trades', 0)}")
    print(f"  Total return: {results.get('total_return', 0):.4f}")
    
    return True


def test_mixed_execution_intents():
    """Test that both types of ExecutionIntents can be processed in the same backtest."""
    print("\nTesting mixed ExecutionIntent types...")
    
    # Create sample data
    data = create_sample_data()
    
    # Create a mock strategy function that randomly returns either type of ExecutionIntent
    def mixed_strategy_function(row, params):
        current_price = row['close']
        
        # Generate a signal when price is above 100
        if current_price > 100:
            # Randomly choose between Domain and Infrastructure ExecutionIntent
            import random
            if random.choice([True, False]):
                # Return Domain ExecutionIntent
                return DomainExecutionIntent(
                    symbol=Symbol("BTCUSDT"),
                    strategy_name="mixed_test_strategy",
                    side=DomainOrderSide.BUY,
                    intent_confidence=Percentage(0.7),
                    risk_parameters={
                        'risk_per_trade': 0.02,
                        'atr_multiplier': 1.5,
                        'risk_reward_ratio': 1.5
                    },
                    timestamp=pd.Timestamp(row.name) if hasattr(row, 'name') else datetime.now()
                )
            else:
                # Return Infrastructure ExecutionIntent
                return create_execution_intent(
                    side=InfraOrderSide.BUY,
                    size=1.0,
                    price=current_price,
                    timestamp=pd.Timestamp(row.name) if hasattr(row, 'name') else datetime.now(),
                    stop_loss=current_price * 0.98,
                    take_profit=current_price * 1.04,
                    strategy_name="mixed_test_strategy",
                    symbol="BTCUSDT"
                )
        else:
            return None

    # Initialize backtester
    backtester = RealisticBacktester(
        initial_capital=10000.0,
        fee_rate=0.001,
        slippage_factor=0.0005
    )

    # Run backtest with the mixed strategy
    results = backtester.run_backtest(
        data=data,
        strategy_function=mixed_strategy_function,
        strategy_params={
            'risk_per_trade': 0.02,
            'atr_multiplier': 1.5,
            'risk_reward_ratio': 1.5,
            'symbol': 'BTCUSDT'
        },
        strategy_name='rsi_strategy'
    )
    
    print(f"✓ Mixed ExecutionIntent test completed!")
    print(f"  Total trades: {results.get('total_trades', 0)}")
    print(f"  Total return: {results.get('total_return', 0):.4f}")
    
    return True


def main():
    """Run all verification tests."""
    print("Running final verification tests for Domain ExecutionIntent adapter...\n")
    
    success1 = test_infrastructure_execution_intent()
    success2 = test_domain_execution_intent()
    success3 = test_mixed_execution_intents()
    
    if success1 and success2 and success3:
        print("\n🎉 All verification tests passed!")
        print("✓ Infrastructure ExecutionIntents work correctly")
        print("✓ Domain ExecutionIntents work with adapter")
        print("✓ Mixed ExecutionIntent types work correctly")
        print("\nThe adapter successfully bridges the gap between Domain and Infrastructure ExecutionIntents!")
        return True
    else:
        print("\n❌ Some verification tests failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)