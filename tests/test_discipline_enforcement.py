#!/usr/bin/env python3
"""
Test script to verify that intent discipline is properly enforced.
This tests that discipline checks reduce the number of ExecutionIntents generated.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime, timedelta
from decimal import Decimal
from domain.entities.signal_entities import FusedSignal, ExecutionIntent, SignalType
from domain.value_objects import Symbol, Percentage, Money
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter
from domain.entities.signal_entities import OrderSide


def test_discipline_enforcement():
    """Test that discipline checks properly reduce intent generation."""
    print("Testing Discipline Enforcement...")

    # Create a strategy with strict discipline parameters
    strategy = BaseStrategyAdapter("test_discipline_strategy")
    
    # Configure strict discipline parameters
    strategy.config['min_bars_between_entries'] = 5  # Require 5 bars between entries
    strategy.config['max_trades_per_day'] = 2       # Max 2 trades per day
    strategy.config['max_consecutive_losses'] = 2   # Pause after 2 losses
    strategy.config['min_atr_threshold'] = 0.01     # Require higher volatility
    strategy.config['avoid_flat_markets'] = True    # Avoid flat markets
    strategy.config['cooldown_after_exit_minutes'] = 1  # 1 minute cooldown after exit

    # Create test signals
    test_symbol = Symbol("BTCUSDT")
    
    # Create a signal with good conditions
    good_signal = FusedSignal(
        symbol=test_symbol,
        dominant_bias=SignalType.BUY,
        direction=0.6,
        dominance_score=0.8,
        regime_context="trending",
        confidence=Percentage(Decimal('0.8')),
        timestamp=datetime.now(),
        metadata={
            'atr': 500.0,  # High ATR (about 1.25% of 40000)
            'current_price': 40000.0,
            'market_regime': 'trending'
        }
    )

    # Create a signal with low volatility (should be blocked by market condition check)
    low_vol_signal = FusedSignal(
        symbol=test_symbol,
        dominant_bias=SignalType.BUY,
        direction=0.6,
        dominance_score=0.8,
        regime_context="trending",
        confidence=Percentage(Decimal('0.8')),
        timestamp=datetime.now(),
        metadata={
            'atr': 10.0,  # Low ATR (about 0.025% of 40000) - below threshold of 0.01
            'current_price': 40000.0,
            'market_regime': 'trending'
        }
    )

    print("\n1. Testing first valid signal (should be allowed)...")
    # Increment bar counter to simulate progression
    strategy.increment_bar_counter("BTCUSDT")
    
    intent1 = strategy.evaluate_fused_signal(good_signal)
    if intent1:
        print(f"   ✓ First intent generated: {intent1.side.name} for {intent1.symbol.value}")
        strategy.record_intent_emission(good_signal, intent1)
    else:
        print("   ✗ First intent was blocked unexpectedly")
        return False

    print("\n2. Testing signal with low volatility (should be blocked by market condition)...")
    strategy.increment_bar_counter("BTCUSDT")
    
    intent_low_vol = strategy.evaluate_fused_signal(low_vol_signal)
    if intent_low_vol is None:
        print("   ✓ Low volatility signal was properly blocked")
    else:
        print(f"   ✗ Low volatility signal was not blocked: {intent_low_vol.side.name}")
        return False

    print("\n3. Testing rapid successive signals (should be blocked by min bars check)...")
    # Don't increment bar counter - simulate rapid signals
    intent_rapid = strategy.evaluate_fused_signal(good_signal)
    if intent_rapid is None:
        print("   ✓ Rapid signal was properly blocked by min bars check")
    else:
        print(f"   ✗ Rapid signal was not blocked: {intent_rapid.side.name}")
        return False

    print("\n4. Testing signal after sufficient bars (should be allowed)...")
    # Close the previous position first
    strategy.record_position_closed("BTCUSDT")

    # Manually set the exit time far enough in the past to pass cooldown
    from datetime import timedelta
    strategy.last_exit_time["BTCUSDT"] = datetime.now() - timedelta(minutes=2)  # 2 minutes ago

    # Reset daily counter to allow more trades in this test
    from datetime import date
    strategy.intent_count_today[("BTCUSDT", date.today())] = 1  # Set to 1 to allow one more

    # Clear the signal conditions to avoid debouncing with the same signal
    strategy.last_signal_conditions.clear()

    # Increment bar counter enough times to pass min_bars check
    for i in range(5):
        strategy.increment_bar_counter("BTCUSDT")

    intent_after_bars = strategy.evaluate_fused_signal(good_signal)
    if intent_after_bars:
        print(f"   ✓ Signal after sufficient bars was allowed: {intent_after_bars.side.name}")
        strategy.record_intent_emission(good_signal, intent_after_bars)
    else:
        print("   ✗ Signal after sufficient bars was blocked unexpectedly")
        return False

    print("\n5. Testing position exclusivity (after closing position)...")
    # Close the position
    strategy.record_position_closed("BTCUSDT")

    # Manually set the exit time far enough in the past to pass cooldown
    from datetime import timedelta
    strategy.last_exit_time["BTCUSDT"] = datetime.now() - timedelta(minutes=2)  # 2 minutes ago

    # Reset daily counter to allow one more trade
    from datetime import date
    strategy.intent_count_today[("BTCUSDT", date.today())] = 1  # Allow one more trade

    # Increment bar counter enough to pass min_bars check
    for i in range(5):
        strategy.increment_bar_counter("BTCUSDT")

    # Clear signal conditions to avoid debouncing
    strategy.last_signal_conditions.clear()

    # Now a new signal should be allowed
    intent_after_close = strategy.evaluate_fused_signal(good_signal)
    if intent_after_close:
        print(f"   ✓ Signal after position close was allowed: {intent_after_close.side.name}")
        strategy.record_intent_emission(good_signal, intent_after_close)
    else:
        print("   ✗ Signal after position close was blocked unexpectedly")
        return False

    print("\n6. Testing daily trade limit...")
    # Close position and reset for daily limit test
    strategy.record_position_closed("BTCUSDT")

    # Manually set the exit time far enough in the past to pass cooldown
    from datetime import timedelta
    strategy.last_exit_time["BTCUSDT"] = datetime.now() - timedelta(minutes=2)  # 2 minutes ago

    # Reset daily counter for this test - only reset today's counter
    from datetime import date
    today = date.today()
    strategy.intent_count_today.clear()  # Clear all dates
    # Initialize today's counter to 0
    strategy.intent_count_today[("BTCUSDT", today)] = 0

    # Generate 2 trades to reach the daily limit
    for i in range(2):
        # Increment bar counter
        for j in range(5):
            strategy.increment_bar_counter("BTCUSDT")

        # Clear signal conditions to avoid debouncing
        strategy.last_signal_conditions.clear()

        intent = strategy.evaluate_fused_signal(good_signal)
        if intent:
            strategy.record_intent_emission(good_signal, intent)
            print(f"   Trade {i+1}: Allowed (count: {strategy.intent_count_today.get(('BTCUSDT', date.today()), 0)})")
            strategy.record_position_closed("BTCUSDT")  # Close position after each trade
        else:
            print(f"   Trade {i+1}: Blocked unexpectedly")
            return False

    # Next trade should be blocked by daily limit
    for j in range(5):
        strategy.increment_bar_counter("BTCUSDT")

    # Clear signal conditions to avoid debouncing
    strategy.last_signal_conditions.clear()

    intent_daily_limit = strategy.evaluate_fused_signal(good_signal)
    if intent_daily_limit is None:
        print("   ✓ Trade blocked by daily limit (as expected)")
    else:
        print(f"   ✗ Trade was not blocked by daily limit: {intent_daily_limit.side.name}")
        return False

    print("\n✅ All discipline enforcement tests passed!")
    print("\nDiscipline features verified:")
    print("- Market condition validation (volatility threshold)")
    print("- Minimum bars between entries")
    print("- Position exclusivity")
    print("- Daily trade limits")
    print("- Proper state management (position open/close)")

    return True


if __name__ == "__main__":
    success = test_discipline_enforcement()
    if success:
        print("\n🎉 Discipline enforcement is working correctly!")
    else:
        print("\n❌ Discipline enforcement has issues!")
        sys.exit(1)