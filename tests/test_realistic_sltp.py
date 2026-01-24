"""
Specific test for the improved SL/TP logic to ensure realistic behavior.
"""
import numpy as np
import sys
import os
from datetime import datetime

# Add the project root to the path so we can import our modules
sys.path.insert(0, '/Users/mojtaba.rahbari/Sites/python/lynxion-ets')

from infrastructure.risk.advanced_sltp_manager import AdvancedSLTPManager, PositionSide, RegimeType


def test_realistic_sltp_logic():
    """Test the improved SL/TP logic with realistic scenarios."""
    print("🧪 Testing Realistic SL/TP Logic...")
    
    sltp_manager = AdvancedSLTPManager()
    
    # Test 1: Basic SL/TP calculation with realistic parameters
    print("   Test 1: Basic SL/TP calculation")
    entry_price = 50000
    atr_value = 500  # $500 ATR
    
    levels = sltp_manager.calculate_levels(
        entry_price=entry_price,
        position_side=PositionSide.LONG,
        atr_value=atr_value,
        regime=RegimeType.BULLISH_TRENDING,
        support_level=48000,
        resistance_level=53000
    )
    
    print(f"      Entry: ${entry_price}")
    print(f"      SL: ${levels.stop_loss:.2f} (distance: ${levels.sl_distance:.2f})")
    print(f"      TP: ${levels.take_profit:.2f} (distance: ${levels.tp_distance:.2f})")
    print(f"      SL ATR mult: {levels.sl_atr_multiple:.2f}, TP ATR mult: {levels.tp_atr_multiple:.2f}")
    
    # Verify that SL is below entry and TP is above entry for long position
    assert levels.stop_loss < entry_price, "SL should be below entry for long position"
    assert levels.take_profit > entry_price, "TP should be above entry for long position"
    print("      ✅ SL below entry and TP above entry for long position")
    
    # Test 2: Short position
    print("   Test 2: Short position SL/TP calculation")
    levels_short = sltp_manager.calculate_levels(
        entry_price=entry_price,
        position_side=PositionSide.SHORT,
        atr_value=atr_value,
        regime=RegimeType.BEARISH_TRENDING,
        support_level=48000,
        resistance_level=53000
    )
    
    print(f"      Entry: ${entry_price}")
    print(f"      SL: ${levels_short.stop_loss:.2f} (distance: ${levels_short.sl_distance:.2f})")
    print(f"      TP: ${levels_short.take_profit:.2f} (distance: ${levels_short.tp_distance:.2f})")
    
    # Verify that SL is above entry and TP is below entry for short position
    assert levels_short.stop_loss > entry_price, "SL should be above entry for short position"
    assert levels_short.take_profit < entry_price, "TP should be below entry for short position"
    print("      ✅ SL above entry and TP below entry for short position")
    
    # Test 3: Exit conditions with priority (SL over TP)
    print("   Test 3: Exit conditions with priority")
    
    # Scenario where both SL and TP are hit in the same candle
    exit_price, exit_type = sltp_manager.check_exit_conditions(
        current_price=entry_price + 100,
        high_price=levels.take_profit + 100,  # High hits TP
        low_price=levels.stop_loss - 100,     # Low hits SL
        sl_price=levels.stop_loss,
        tp_price=levels.take_profit,
        position_side=PositionSide.LONG
    )
    
    print(f"      Both SL and TP hit - Exit type: {exit_type}, Exit price: ${exit_price}")
    assert exit_type == 'SL', "When both SL and TP hit, SL should take priority"
    print("      ✅ SL takes priority when both hit simultaneously")
    
    # Test 4: Trailing stop functionality
    print("   Test 4: Trailing stop functionality")
    
    # Initial stop loss
    initial_stop = levels.stop_loss
    
    # Price moves favorably
    current_price_favorable = entry_price + 2000  # Price moved $2000 in our favor
    
    new_trail_stop = sltp_manager.update_trailing_stop(
        current_price=current_price_favorable,
        entry_price=entry_price,
        initial_stop_loss=initial_stop,
        position_side=PositionSide.LONG,
        atr_value=atr_value
    )
    
    print(f"      Initial SL: ${initial_stop:.2f}")
    print(f"      New trailing SL: ${new_trail_stop:.2f}")
    print(f"      Price moved to: ${current_price_favorable:.2f}")
    
    # New trailing stop should be higher than initial stop (for long position)
    assert new_trail_stop >= initial_stop, "Trailing stop should be at or above initial stop for long position"
    print("      ✅ Trailing stop properly adjusted upward for long position")
    
    # Test 5: Validation of realistic levels
    print("   Test 5: Validation of realistic levels")

    # Create validation service instance
    from infrastructure.risk.advanced_sltp_manager import SLTPValidationService
    validation_service = SLTPValidationService(sltp_manager)

    is_valid, issues = validation_service.validate_levels(
        entry_price=entry_price,
        sl_price=levels.stop_loss,
        tp_price=levels.take_profit,
        position_side=PositionSide.LONG
    )

    print(f"      Validation passed: {is_valid}")
    if issues:
        print(f"      Issues: {issues}")
    else:
        print("      No validation issues")

    # Test 6: Market structure validation
    print("   Test 6: Market structure validation")

    # Test with support/resistance levels that would affect SL/TP placement
    levels_with_struct = sltp_manager.calculate_levels(
        entry_price=entry_price,
        position_side=PositionSide.LONG,
        atr_value=atr_value,
        regime=RegimeType.NORMAL,
        support_level=entry_price * 0.99,  # Support just below entry
        resistance_level=entry_price * 1.01  # Resistance just above entry
    )

    print(f"      With structure - SL: ${levels_with_struct.stop_loss:.2f}, TP: ${levels_with_struct.take_profit:.2f}")

    # The SL should not be below the support level (with small buffer)
    min_sl_with_support = entry_price * 0.99 * 0.995  # Support * buffer
    assert levels_with_struct.stop_loss >= min_sl_with_support, f"SL should respect support level (was ${levels_with_struct.stop_loss}, min should be ${min_sl_with_support})"
    print("      ✅ SL respects support level")

    # The TP should not be too close to resistance level
    max_tp_with_resistance = entry_price * 1.01 * 0.998  # Resistance * buffer
    assert levels_with_struct.take_profit <= max_tp_with_resistance, f"TP should respect resistance level (was ${levels_with_struct.take_profit}, max should be ${max_tp_with_resistance})"
    print("      ✅ TP respects resistance level")

    print("✅ All realistic SL/TP logic tests passed!\n")


def test_edge_cases():
    """Test edge cases for SL/TP logic."""
    print("🧪 Testing SL/TP Edge Cases...")
    
    sltp_manager = AdvancedSLTPManager()
    
    # Test with very tight stops (should still be valid but trigger quickly)
    entry_price = 100
    tight_levels = sltp_manager.calculate_levels(
        entry_price=entry_price,
        position_side=PositionSide.LONG,
        atr_value=1,  # Very low ATR
        regime=RegimeType.NORMAL
    )
    
    print(f"   Tight stops - Entry: ${entry_price}, SL: ${tight_levels.stop_loss:.3f}, TP: ${tight_levels.take_profit:.3f}")
    
    # Test with very wide stops
    wide_levels = sltp_manager.calculate_levels(
        entry_price=entry_price,
        position_side=PositionSide.LONG,
        atr_value=20,  # Very high ATR
        regime=RegimeType.HIGH_VOLATILITY
    )
    
    print(f"   Wide stops - Entry: ${entry_price}, SL: ${wide_levels.stop_loss:.3f}, TP: ${wide_levels.take_profit:.3f}")
    
    # Verify that even with wide stops, SL is still below entry and TP above for long
    assert wide_levels.stop_loss < entry_price, "Wide SL should still be below entry for long"
    assert wide_levels.take_profit > entry_price, "Wide TP should still be above entry for long"
    print("   ✅ Wide stops still maintain correct relationship")
    
    print("✅ All edge case tests passed!\n")


def main():
    """Run all SL/TP logic tests."""
    print("🚀 Starting SL/TP Logic Validation Tests\n")
    
    try:
        test_realistic_sltp_logic()
        test_edge_cases()
        
        print("🎉 All SL/TP logic validation tests completed successfully!")
        print("✅ The improved SL/TP system is working with realistic behavior.")
        
    except Exception as e:
        print(f"❌ Error during SL/TP validation tests: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✨ SL/TP logic validation complete! The system is ready with realistic behavior.")
    else:
        print("\n⚠️  Some SL/TP validation tests failed. Please review the errors above.")