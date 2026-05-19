#!/usr/bin/env python3
"""
Test script to verify that the intent discipline features are working properly.
This script tests the new safeguards added to the BaseStrategyAdapter.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime
from decimal import Decimal
from domain.entities.signal_entities import FusedSignal, ExecutionIntent
from domain.value_objects import Symbol, Percentage, Money
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


def test_intent_discipline():
    """Test the intent discipline features of the BaseStrategyAdapter."""
    print("Testing Intent Discipline Features...")
    
    # Create a mock strategy adapter
    strategy = BaseStrategyAdapter("test_strategy")
    
    # Create a mock fused signal
    test_symbol = Symbol("BTCUSDT")
    fused_signal = FusedSignal(
        symbol=test_symbol,
        dominant_bias="BUY",
        direction=0.5,
        dominance_score=0.8,
        regime_context="trending",
        confidence=Percentage(Decimal('0.7')),
        timestamp=datetime.now(),
        metadata={
            'atr': 40.0,  # 40 USD ATR (which is 0.1% of 40000)
            'current_price': 40000.0,
            'market_regime': 'normal'
        }
    )
    
    print("\n1. Testing initial intent emission...")
    # First intent should be allowed
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   Should emit: {should_emit}, Reason: {reason}")
    assert should_emit, "First intent should be allowed"
    
    from domain.entities.signal_entities import OrderSide

    # Simulate intent emission
    mock_intent = ExecutionIntent(
        symbol=test_symbol,
        strategy_name="test_strategy",
        side=OrderSide.BUY,
        intent_confidence=Percentage(Decimal('0.7')),
        risk_parameters={'position_size': 0.01},
        timestamp=datetime.now()
    )
    strategy.record_intent_emission(fused_signal, mock_intent)
    
    print("\n2. Testing duplicate position prevention...")
    # Second intent should be blocked due to open position
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   Should emit: {should_emit}, Reason: {reason}")
    assert not should_emit, "Second intent should be blocked due to open position"
    assert "Position already open" in reason
    
    print("\n3. Testing position closure and reopening...")
    # Temporarily set cooldown to 0 for this test
    original_cooldown = strategy.config['cooldown_after_exit_minutes']
    strategy.config['cooldown_after_exit_minutes'] = 0

    # Close the position
    strategy.record_position_closed("BTCUSDT")

    # Increment bar counter enough times to satisfy the min_bars check (default is 5)
    for _ in range(5):
        strategy.increment_bar_counter("BTCUSDT")

    # Clear the signal conditions to avoid debouncing
    strategy.last_signal_conditions.clear()

    # Now intent should be allowed again
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   Should emit: {should_emit}, Reason: {reason}")
    assert should_emit, "Intent should be allowed after position closure"

    # Restore original cooldown
    strategy.config['cooldown_after_exit_minutes'] = original_cooldown
    
    print("\n4. Testing bar counter and minimum bars check...")
    # Record intent emission again
    strategy.record_intent_emission(fused_signal, mock_intent)

    # Temporarily set min_bars_between_entries to 2 for testing
    original_min_bars = strategy.config['min_bars_between_entries']
    strategy.config['min_bars_between_entries'] = 2

    # Also temporarily set cooldown to 0 for this test
    original_cooldown = strategy.config['cooldown_after_exit_minutes']
    strategy.config['cooldown_after_exit_minutes'] = 0

    # Close the position to allow further testing
    strategy.record_position_closed("BTCUSDT")

    # Increment bar counter once (still below threshold)
    strategy.increment_bar_counter("BTCUSDT")
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   Should emit (1 bar since entry): {should_emit}, Reason: {reason}")
    assert not should_emit, "Intent should be blocked - not enough bars since last entry"

    # Increment bar counter again (now above threshold)
    strategy.increment_bar_counter("BTCUSDT")

    # Clear the signal conditions to avoid debouncing
    strategy.last_signal_conditions.clear()

    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   Should emit (2 bars since entry): {should_emit}, Reason: {reason}")
    assert should_emit, "Intent should be allowed - enough bars since last entry"

    # Restore original values
    strategy.config['min_bars_between_entries'] = original_min_bars
    strategy.config['cooldown_after_exit_minutes'] = original_cooldown
    
    print("\n5. Testing daily trade limit...")
    # Temporarily set max_trades_per_day to 2 for testing
    original_max_trades = strategy.config['max_trades_per_day']
    strategy.config['max_trades_per_day'] = 2

    # Also temporarily set min_bars_between_entries to 0 for this test
    original_min_bars = strategy.config['min_bars_between_entries']
    strategy.config['min_bars_between_entries'] = 0

    # And set cooldown to 0
    original_cooldown = strategy.config['cooldown_after_exit_minutes']
    strategy.config['cooldown_after_exit_minutes'] = 0

    # Clear signal conditions to avoid debouncing
    strategy.last_signal_conditions.clear()

    # Reset daily count for this test
    from datetime import date
    strategy.intent_count_today.clear()

    # Close position first
    strategy.record_position_closed("BTCUSDT")

    # First trade should be allowed
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   First trade - Should emit: {should_emit}, Reason: {reason}")
    assert should_emit, "First trade should be allowed"
    strategy.record_intent_emission(fused_signal, mock_intent)

    # Second trade should be allowed
    strategy.record_position_closed("BTCUSDT")
    # Clear signal conditions again
    strategy.last_signal_conditions.clear()
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   Second trade - Should emit: {should_emit}, Reason: {reason}")
    assert should_emit, "Second trade should be allowed"
    strategy.record_intent_emission(fused_signal, mock_intent)

    # Third trade should be blocked due to daily limit
    strategy.record_position_closed("BTCUSDT")
    # Clear signal conditions again
    strategy.last_signal_conditions.clear()
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   Third trade - Should emit: {should_emit}, Reason: {reason}")
    assert not should_emit, "Third trade should be blocked due to daily limit"
    assert "Daily trade limit" in reason

    # Restore original values
    strategy.config['max_trades_per_day'] = original_max_trades
    strategy.config['min_bars_between_entries'] = original_min_bars
    strategy.config['cooldown_after_exit_minutes'] = original_cooldown
    
    print("\n6. Testing consecutive losses...")
    # Temporarily set max_consecutive_losses to 1 for testing
    original_max_losses = strategy.config['max_consecutive_losses']
    strategy.config['max_consecutive_losses'] = 1

    # Also temporarily set min_bars_between_entries to 0 for this test
    original_min_bars = strategy.config['min_bars_between_entries']
    strategy.config['min_bars_between_entries'] = 0

    # And set cooldown to 0
    original_cooldown = strategy.config['cooldown_after_exit_minutes']
    strategy.config['cooldown_after_exit_minutes'] = 0

    # Clear signal conditions to avoid debouncing
    strategy.last_signal_conditions.clear()

    # Close position and reset for clean test
    strategy.record_position_closed("BTCUSDT")

    # Record a loss
    strategy.record_trade_result("BTCUSDT", is_profitable=False)

    # Next trade should be blocked due to consecutive losses
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   After 1 loss - Should emit: {should_emit}, Reason: {reason}")
    assert not should_emit, "Trade should be blocked after reaching max consecutive losses"
    assert "consecutive losses" in reason or "Consecutive losses" in reason

    # Record a profit to reset the counter
    strategy.record_trade_result("BTCUSDT", is_profitable=True)

    # Now trade should be allowed again
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   After profit reset - Should emit: {should_emit}, Reason: {reason}")
    assert should_emit, "Trade should be allowed after profit resets loss counter"

    # Restore original value
    strategy.config['max_consecutive_losses'] = original_max_losses
    strategy.config['min_bars_between_entries'] = original_min_bars
    strategy.config['cooldown_after_exit_minutes'] = original_cooldown
    
    print("\n7. Testing market condition validation...")
    # Temporarily set very high ATR threshold for testing
    original_atr_threshold = strategy.config['min_atr_threshold']
    strategy.config['min_atr_threshold'] = 0.1  # 10% ATR threshold

    # Also temporarily set min_bars_between_entries to 0 for this test
    original_min_bars = strategy.config['min_bars_between_entries']
    strategy.config['min_bars_between_entries'] = 0

    # And set cooldown to 0
    original_cooldown = strategy.config['cooldown_after_exit_minutes']
    strategy.config['cooldown_after_exit_minutes'] = 0

    # Clear signal conditions to avoid debouncing
    strategy.last_signal_conditions.clear()

    # Create signal with low ATR
    low_atr_signal = FusedSignal(
        symbol=test_symbol,
        dominant_bias="BUY",
        direction=0.5,
        dominance_score=0.8,
        regime_context="trending",
        confidence=Percentage(Decimal('0.7')),
        timestamp=datetime.now(),
        metadata={
            'atr': 10.0,  # 10 USD ATR (which is 0.025% of 40000) - below threshold of 0.1%
            'current_price': 40000.0,
            'market_regime': 'normal'
        }
    )

    # Close position first
    strategy.record_position_closed("BTCUSDT")

    # Intent should be blocked due to low volatility
    should_emit, reason = strategy._should_emit_intent(low_atr_signal)
    print(f"   Low volatility signal - Should emit: {should_emit}, Reason: {reason}")
    assert not should_emit, "Intent should be blocked due to low volatility"
    assert "Market conditions not favorable" in reason

    # Restore original values
    strategy.config['min_atr_threshold'] = original_atr_threshold
    strategy.config['min_bars_between_entries'] = original_min_bars
    strategy.config['cooldown_after_exit_minutes'] = original_cooldown
    
    print("\n8. Testing signal debouncing...")
    # Temporarily set min_bars_between_entries to 0 for this test
    original_min_bars = strategy.config['min_bars_between_entries']
    strategy.config['min_bars_between_entries'] = 0

    # And set cooldown to 0
    original_cooldown = strategy.config['cooldown_after_exit_minutes']
    strategy.config['cooldown_after_exit_minutes'] = 0

    # Close position first
    strategy.record_position_closed("BTCUSDT")

    # Clear signal conditions to start fresh
    strategy.last_signal_conditions.clear()

    # First similar signal should be allowed
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   First similar signal - Should emit: {should_emit}, Reason: {reason}")
    assert should_emit, "First similar signal should be allowed"

    # Record this intent
    strategy.record_intent_emission(fused_signal, mock_intent)

    # Close position again
    strategy.record_position_closed("BTCUSDT")

    # Second identical signal should be blocked (debounced)
    should_emit, reason = strategy._should_emit_intent(fused_signal)
    print(f"   Second identical signal - Should emit: {should_emit}, Reason: {reason}")
    assert not should_emit, "Second identical signal should be blocked by debouncing"
    assert "Signal debounce" in reason or "Repeated signal" in reason

    # Restore original values
    strategy.config['min_bars_between_entries'] = original_min_bars
    strategy.config['cooldown_after_exit_minutes'] = original_cooldown

    print("\n✅ All intent discipline tests passed!")
    print("\nSummary of implemented features:")
    print("- Position exclusivity (no duplicate positions)")
    print("- Minimum bars between entries")
    print("- Daily trade limits")
    print("- Consecutive loss protection")
    print("- Market condition validation (volatility, flat markets)")
    print("- Signal debouncing to prevent repeated signals")
    print("- Cooldown periods after exits")


if __name__ == "__main__":
    test_intent_discipline()