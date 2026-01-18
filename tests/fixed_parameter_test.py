"""
Test module to verify that strategies work with fixed parameters without hyperopt.
This ensures strategies are functional before enabling dynamic parameter systems.
"""
import sys
import os
# Add the project root to Python path to enable imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from infrastructure.strategies.technical_strategies import (
    TrendFollowingStrategyAdapter,
    MeanReversionStrategyAdapter,
    ScalpingStrategyAdapter,
    BreakoutStrategyAdapter
)
from infrastructure.strategies.readiness_gate import ReadinessGateService
from shared.logger import logger


def generate_test_market_data(start_price: float = 100.0,
                            num_points: int = 200,
                            volatility: float = 0.02) -> List[Dict[str, Any]]:
    """
    Generate realistic test market data with trends, cycles, and volatility.
    """
    # Set a seed for reproducible results
    np.random.seed(42)

    prices = [start_price]
    dates = [datetime.now() - timedelta(hours=num_points)]

    # Create a price series with some trends and patterns
    for i in range(1, num_points):
        # Add some trend patterns and mean reversion
        if i % 50 < 10:  # Create upward trends periodically
            drift = 0.002
        elif i % 50 < 20:  # Create downward trends periodically
            drift = -0.001
        else:  # Mean reversion around a trend
            drift = 0.0005 - (prices[-1] - start_price) * 0.0001  # Gentle mean reversion

        # Add random volatility
        random_change = np.random.normal(drift, volatility)
        new_price = max(0.01, prices[-1] * (1 + random_change))  # Ensure positive prices

        prices.append(new_price)
        dates.append(dates[-1] + timedelta(hours=1))

    # Create OHLCV data
    market_data = []
    for i, price in enumerate(prices):
        # Add some variation between open, high, low
        variation = abs(np.random.normal(0, 0.005))
        high = price * (1 + variation)
        low = price * (1 - variation)
        open_price = prices[i-1] if i > 0 else price
        volume = max(100, np.random.exponential(1000))  # Volume data

        market_data.append({
            'timestamp': dates[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume
        })

    return market_data


def test_strategy_basic_functionality():
    """
    Test that each strategy can generate signals with fixed parameters.
    """
    print("Testing strategy basic functionality with fixed parameters...")

    # Generate test market data
    market_data = generate_test_market_data()
    symbol = Symbol("TESTUSDT")

    strategies = [
        TrendFollowingStrategyAdapter(),
        MeanReversionStrategyAdapter(),
        ScalpingStrategyAdapter(),
        BreakoutStrategyAdapter()
    ]

    results = {}

    for strategy in strategies:
        strategy_name = strategy.get_strategy_name()
        print(f"\nTesting {strategy_name}...")

        # Update strategy with market data
        strategy.update_with_market_data(market_data)

        # Generate signals throughout the data
        signals = []
        # For this test, create a temporary readiness service just for recording signals
        from infrastructure.strategies.readiness_gate import ReadinessGateService
        temp_readiness_service = ReadinessGateService()
        temp_readiness_service.start_services()

        for i, data_point in enumerate(market_data):
            # Update strategy with individual data point
            strategy.update_with_market_data([data_point])

            # Generate signal
            signal = strategy.generate_signal(symbol)
            if signal and signal.signal_type.name != 'HOLD':
                signals.append({
                    'index': i,
                    'timestamp': data_point['timestamp'],
                    'signal_type': signal.signal_type.name,
                    'confidence': float(signal.confidence.value),
                    'score': signal.score
                })
                # Record the signal for explainability
                temp_readiness_service.record_signal(strategy, symbol, signal)

        temp_readiness_service.stop_services()

        # Calculate activity statistics
        total_signals = len(signals)
        buy_signals = len([s for s in signals if s['signal_type'] == 'BUY'])
        sell_signals = len([s for s in signals if s['signal_type'] == 'SELL'])

        # Calculate signal rate (signals per 100 data points)
        signal_rate = (total_signals / len(market_data)) * 100 if market_data else 0

        results[strategy_name] = {
            'total_signals': total_signals,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'signal_rate': signal_rate,
            'sample_signals': signals[:5],  # First 5 signals as sample
            'all_signals': signals
        }

        print(f"  Total signals: {total_signals}")
        print(f"  Buy signals: {buy_signals}")
        print(f"  Sell signals: {sell_signals}")
        print(f"  Signal rate: {signal_rate:.2f}% ({total_signals}/{len(market_data)})")
        if signals:
            print(f"  Sample signals: {signals[:3]}")

    return results


def test_strategy_with_readiness_gate():
    """
    Test strategies through the readiness gate system to ensure they meet requirements.
    """
    print("\n" + "="*60)
    print("Testing strategies through readiness gate system...")

    # Generate test market data
    market_data = generate_test_market_data()
    symbol = Symbol("TESTUSDT")

    readiness_service = ReadinessGateService()
    readiness_service.start_services()

    strategies = [
        TrendFollowingStrategyAdapter(),
        MeanReversionStrategyAdapter(),
        ScalpingStrategyAdapter(),
        BreakoutStrategyAdapter()
    ]

    gate_results = {}

    for strategy in strategies:
        strategy_name = strategy.get_strategy_name()
        print(f"\nEvaluating {strategy_name} through readiness gate...")

        # Evaluate readiness
        evaluation = readiness_service.evaluate_strategy(
            strategy, symbol, market_data
        )

        gate_results[strategy_name] = evaluation

        print(f"  Readiness Category: {evaluation['readiness_category']}")
        print(f"  Overall Score: {evaluation['overall_readiness_score']:.3f}")
        print(f"  Activity Score: {evaluation['activity_score']:.3f}")
        print(f"  Robustness Score: {evaluation['robustness_score']:.3f}")
        print(f"  Explainability Score: {evaluation['explainability_score']:.3f}")

        if evaluation['readiness_category'] == '[OPTIMIZATION-ELIGIBLE]':
            print(f"  ✅ {strategy_name} is ready for optimization!")
        else:
            print(f"  ❌ {strategy_name} needs improvements: {evaluation['reason']}")
            for rec in evaluation['stress_recommendations']:
                print(f"    - {rec}")

    readiness_service.stop_services()
    return gate_results


def run_comprehensive_fixed_parameter_test():
    """
    Run comprehensive tests to ensure strategies work without hyperparameter optimization.
    """
    print("="*70)
    print("COMPREHENSIVE FIXED PARAMETER STRATEGY TEST")
    print("="*70)
    print("Testing strategies with FIXED parameters to ensure they are functional")
    print("before enabling dynamic parameter systems (hyperopt/retune)")
    print("="*70)

    # Test basic functionality
    basic_results = test_strategy_basic_functionality()

    print("\n" + "="*60)
    print("BASIC FUNCTIONALITY RESULTS:")
    print("="*60)
    for strategy_name, result in basic_results.items():
        print(f"{strategy_name}:")
        print(f"  - Total signals: {result['total_signals']}")
        print(f"  - Signal rate: {result['signal_rate']:.2f}%")
        print(f"  - Activity: {'Good' if result['signal_rate'] > 1.0 else 'Low' if result['signal_rate'] < 0.5 else 'Moderate'}")

    # Test through readiness gate
    gate_results = test_strategy_with_readiness_gate()

    print("\n" + "="*60)
    print("READINESS GATE SUMMARY:")
    print("="*60)

    eligible_count = 0
    needs_revision_count = 0
    rejected_count = 0

    for strategy_name, result in gate_results.items():
        category = result['readiness_category']
        if category == '[OPTIMIZATION-ELIGIBLE]':
            eligible_count += 1
            print(f"✅ {strategy_name}: OPTIMIZATION-ELIGIBLE ({result['overall_readiness_score']:.3f})")
        elif category == '[NEEDS_REVISION]':
            needs_revision_count += 1
            print(f"⚠️  {strategy_name}: NEEDS_REVISION ({result['overall_readiness_score']:.3f})")
        else:
            rejected_count += 1
            print(f"❌ {strategy_name}: REJECTED ({result['overall_readiness_score']:.3f})")

    print(f"\nSUMMARY:")
    print(f"  - Optimization Eligible: {eligible_count}")
    print(f"  - Needs Revision: {needs_revision_count}")
    print(f"  - Rejected: {rejected_count}")
    print(f"  - Total Strategies: {len(gate_results)}")

    # Final verification
    print(f"\n" + "="*60)
    print("VERIFICATION RESULTS:")
    print("="*60)

    all_strategies_active = all(
        result['total_signals'] > 0 for result in basic_results.values()
    )

    all_strategies_robust = all(
        result['robustness_score'] > 0.3 for result in gate_results.values()
    )

    print(f"✅ All strategies generate signals: {'YES' if all_strategies_active else 'NO'}")
    print(f"✅ All strategies show basic robustness: {'YES' if all_strategies_robust else 'NO'}")

    overall_success = all_strategies_active and all_strategies_robust
    print(f"🎯 FIXED PARAMETER SYSTEM VERIFICATION: {'PASSED' if overall_success else 'FAILED'}")

    if overall_success:
        print("\n✅ CONFIRMATION: All strategies work with fixed parameters")
        print("   Proceeding to dynamic systems is now SAFE")
    else:
        print("\n❌ WARNING: Some strategies don't work with fixed parameters")
        print("   Fix these issues before enabling dynamic parameter systems!")

    return {
        'basic_results': basic_results,
        'gate_results': gate_results,
        'verification_passed': overall_success
    }


if __name__ == "__main__":
    # Run the comprehensive test
    test_results = run_comprehensive_fixed_parameter_test()

    # Exit with appropriate code
    import sys
    sys.exit(0 if test_results['verification_passed'] else 1)