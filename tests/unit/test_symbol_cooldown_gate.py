"""Unit tests for SymbolCooldownGate and RiskEnforcement cooldown integration."""

import os
import tempfile
import time
from datetime import datetime
import pytest

from infrastructure.risk.symbol_cooldown_gate import SymbolCooldownGate
from infrastructure.risk.advanced_risk_management import AdvancedRiskManagementService


@pytest.mark.unit
def test_symbol_cooldown_gate_sl_exit():
    """Verify that Stop Loss exit activates 60-minute cooldown on all symbol format variants."""
    gate = SymbolCooldownGate()
    gate._sl_cooldowns.clear()

    # Record SL exit for BICOUSDT
    gate.record_stop_loss_exit("BICOUSDT")

    # Verify BICO-USDT, BICOUSDT, BICO/USDT are all blocked
    allowed1, reason1 = gate.is_symbol_allowed("BICOUSDT", cooldown_minutes=60)
    assert not allowed1
    assert "60m Stop Loss Cooldown ACTIVE" in reason1

    allowed2, reason2 = gate.is_symbol_allowed("BICO-USDT", cooldown_minutes=60)
    assert not allowed2

    allowed3, reason3 = gate.is_symbol_allowed("BICO/USDT", cooldown_minutes=60)
    assert not allowed3

    # Verify unrelated symbol is allowed
    allowed_other, _ = gate.is_symbol_allowed("BTCUSDT", cooldown_minutes=60)
    assert allowed_other


@pytest.mark.unit
def test_symbol_cooldown_gate_tp_bypass():
    """Verify that Take Profit exit clears the cooldown immediately."""
    gate = SymbolCooldownGate()
    gate._sl_cooldowns.clear()

    # Record SL exit then TP exit
    gate.record_stop_loss_exit("BICOUSDT")
    allowed_sl, _ = gate.is_symbol_allowed("BICOUSDT", cooldown_minutes=60)
    assert not allowed_sl

    # Take Profit exit clears cooldown
    gate.record_take_profit_exit("BICOUSDT")
    allowed_tp, reason_tp = gate.is_symbol_allowed("BICOUSDT", cooldown_minutes=60)
    assert allowed_tp
    assert reason_tp == "ALLOWED"


@pytest.mark.unit
def test_adaptive_trailing_stop():
    """Verify adaptive trailing stop calculation for Long and Short positions."""
    rm = AdvancedRiskManagementService()

    # Short position entry=0.04333, initial SL=0.0441966 (2% SL distance)
    # Price moves down to 0.04250 (in profit)
    new_sl_short = rm.update_trailing_stop(
        current_price=0.04250,
        entry_price=0.04333,
        position_side="SHORT",
        initial_stop_loss=0.0441966
    )

    # Trailing stop must move DOWN below initial SL
    assert new_sl_short < 0.0441966
    assert new_sl_short == pytest.approx(0.04335, abs=1e-4)

    # Long position entry=100.0, initial SL=98.0 (2% SL distance)
    # Price moves up to 105.0 (in profit)
    new_sl_long = rm.update_trailing_stop(
        current_price=105.0,
        entry_price=100.0,
        position_side="LONG",
        initial_stop_loss=98.0
    )

    # Trailing stop must move UP above initial SL
    assert new_sl_long > 98.0
    assert new_sl_long >= 102.0
