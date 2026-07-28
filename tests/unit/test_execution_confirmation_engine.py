"""Unit tests for the 5m Execution Confirmation Engine (Phase 4)."""

import pytest
from decimal import Decimal
from domain.value_objects import Symbol, ExchangeTimestamp
from domain.entities.research import CandidateSetup
from infrastructure.execution.execution_confirmation_engine import ExecutionConfirmationEngine


@pytest.mark.unit
def test_execution_confirmation_rules():
    engine = ExecutionConfirmationEngine(obi_threshold=0.1)
    
    symbol = Symbol("BTC-USDT")
    ts = ExchangeTimestamp(1700000000000)
    
    buy_setup = CandidateSetup(
        symbol=symbol,
        timestamp=ts,
        setup_type="NGLS_SWEEP",
        direction="BUY",
        trigger_price=Decimal("100.0"),
        stop_loss_level=Decimal("99.0"),
        take_profit_level=Decimal("105.0")
    )
    
    # Valid buy confirmation (positive OBI, positive CVD)
    assert engine.confirm_execution(buy_setup, obi_ratio=0.15, cvd=10.0) is True
    
    # Invalid buy confirmation (negative OBI)
    assert engine.confirm_execution(buy_setup, obi_ratio=-0.05, cvd=10.0) is False
    
    # Invalid buy confirmation (negative CVD)
    assert engine.confirm_execution(buy_setup, obi_ratio=0.2, cvd=-1.0) is False

    sell_setup = CandidateSetup(
        symbol=symbol,
        timestamp=ts,
        setup_type="NGLS_SWEEP",
        direction="SELL",
        trigger_price=Decimal("100.0"),
        stop_loss_level=Decimal("101.0"),
        take_profit_level=Decimal("95.0")
    )
    
    # Valid sell confirmation (negative OBI, negative CVD)
    assert engine.confirm_execution(sell_setup, obi_ratio=-0.15, cvd=-5.0) is True
    
    # Invalid sell confirmation (positive OBI)
    assert engine.confirm_execution(sell_setup, obi_ratio=0.05, cvd=-5.0) is False
