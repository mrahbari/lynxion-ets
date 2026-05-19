#!/usr/bin/env python3
"""
Simple test to verify that discipline enforcement is working.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime, timedelta
from decimal import Decimal
from domain.entities.signal_entities import FusedSignal, SignalType
from domain.value_objects import Symbol, Percentage, Money
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter
from domain.entities.signal_entities import OrderSide


def test_discipline_working():
    """Test that discipline checks are reducing intent generation."""
    print("Testing Discipline Enforcement...")

    # Create a strategy with strict discipline parameters
    strategy = BaseStrategyAdapter("test_discipline_strategy")
    
    # Configure strict discipline parameters
    strategy.config['min_bars_between_entries'] = 5  # Require 5 bars between entries
    strategy.config['max_trades_per_day'] = 2       # Max 2 trades per day
    strategy.config['min_atr_threshold'] = 0.01     # Require higher volatility

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
        generated_count = 1
    else:
        print("   ✗ First intent was blocked unexpectedly")
        return False

    print("\n2. Testing signal with low volatility (should be blocked by market condition)...")
    strategy.increment_bar_counter("BTCUSDT")
    
    intent_low_vol = strategy.evaluate_fused_signal(low_vol_signal)
    if intent_low_vol is None:
        print("   ✓ Low volatility signal was properly blocked")
        filtered_count = 1
    else:
        print(f"   ✗ Low volatility signal was not blocked: {intent_low_vol.side.name}")
        return False

    print("\n3. Testing rapid successive signals (should be blocked by min bars check)...")
    # Don't increment bar counter - simulate rapid signals
    intent_rapid = strategy.evaluate_fused_signal(good_signal)
    if intent_rapid is None:
        print("   ✓ Rapid signal was properly blocked by min bars check")
        filtered_count += 1
    else:
        print(f"   ✗ Rapid signal was not blocked: {intent_rapid.side.name}")
        return False

    print("\n4. Testing signal after sufficient bars (should be allowed)...")
    # Close the previous position first
    strategy.record_position_closed("BTCUSDT")
    
    # Manually set the exit time far enough in the past to pass cooldown
    from datetime import timedelta
    strategy.last_exit_time["BTCUSDT"] = datetime.now() - timedelta(minutes=60)  # 60 minutes ago
    
    # Reset daily counter to allow more trades in this test
    from datetime import date
    strategy.intent_count_today[("BTCUSDT", date.today())] = 1  # Set to 1 to allow one more
    
    # Clear signal conditions to avoid debouncing with the same signal
    strategy.last_signal_conditions.clear()
    
    # Increment bar counter enough times to pass min_bars check
    for i in range(5):
        strategy.increment_bar_counter("BTCUSDT")
    
    intent_after_bars = strategy.evaluate_fused_signal(good_signal)
    if intent_after_bars:
        print(f"   ✓ Signal after sufficient bars was allowed: {intent_after_bars.side.name}")
        strategy.record_intent_emission(good_signal, intent_after_bars)
        generated_count += 1
    else:
        print("   ✗ Signal after sufficient bars was blocked unexpectedly")
        return False

    print(f"\n📊 RESULTS:")
    print(f"   Generated intents: {generated_count}")
    print(f"   Filtered intents: {filtered_count}")
    print(f"   Total attempted: {generated_count + filtered_count}")
    
    # The key test: discipline should have filtered some intents
    if filtered_count > 0:
        print(f"\n✅ SUCCESS: Discipline enforcement is working!")
        print(f"   - {filtered_count} intent(s) were properly filtered out")
        print(f"   - Only {generated_count}/{generated_count + filtered_count} intents were generated ({generated_count/(generated_count + filtered_count)*100:.1f}%)")
        return True
    else:
        print(f"\n❌ FAILURE: No intents were filtered - discipline not working!")
        return False


if __name__ == "__main__":
    success = test_discipline_working()
    if success:
        print("\n🎉 Discipline enforcement is working correctly!")
    else:
        print("\n❌ Discipline enforcement has issues!")
        sys.exit(1)