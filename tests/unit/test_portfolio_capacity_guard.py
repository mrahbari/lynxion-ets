import pytest
from decimal import Decimal
from datetime import datetime
from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager, PositionDirection
from domain.entities import Order, OrderSide
from domain.value_objects import Symbol, Money
from infrastructure.risk.risk_enforcement import RiskEnforcement


def test_single_position_rejection():
    # 1. Initialize risk manager with multi-position disabled
    rm = EnterpriseRiskManager(
        max_portfolio_exposure=100000.0,
        max_position_exposure=50000.0,
        enable_multi_position=False
    )
    
    # 2. Assert first position is allowed
    assert rm.validate_position_entry("BTCUSDT", 1.0, 10000.0) is True
    
    # 3. Enter first position
    rm.enter_position("BTCUSDT", 10000.0, 1.0, PositionDirection.LONG, 9000.0, 11000.0)
    assert len(rm.positions) == 1
    assert rm.get_total_exposure() == 10000.0
    
    # 4. Try entering second position - should be rejected
    assert rm.validate_position_entry("ETHUSDT", 1.0, 2000.0) is False
    # Rejection should NOT modify state
    assert len(rm.positions) == 1
    assert rm.get_total_exposure() == 10000.0


def test_max_concurrent_positions_rejection():
    # 1. Initialize risk manager with max capacity of 2
    rm = EnterpriseRiskManager(
        max_portfolio_exposure=100000.0,
        max_position_exposure=50000.0,
        enable_multi_position=True,
        max_concurrent_positions=2
    )
    
    # 2. Enter 2 positions
    rm.enter_position("BTCUSDT", 10000.0, 1.0, PositionDirection.LONG, 9000.0, 11000.0)
    rm.enter_position("ETHUSDT", 2000.0, 2.0, PositionDirection.LONG, 1800.0, 2200.0)
    assert len(rm.positions) == 2
    assert rm.get_total_exposure() == 14000.0
    
    # 3. Third position should be rejected due to capacity limit
    assert rm.validate_position_entry("SOLUSDT", 10.0, 100.0) is False
    assert len(rm.positions) == 2
    assert rm.get_total_exposure() == 14000.0
    
    # 4. Exit one position and verify capacity is released
    rm.exit_position("ETHUSDT", 2100.0, "TP")
    assert len(rm.positions) == 1
    assert rm.get_total_exposure() == 10000.0
    
    # Now third position is allowed
    assert rm.validate_position_entry("SOLUSDT", 10.0, 100.0) is True


def test_setup_attribution_remains_correct():
    rm = EnterpriseRiskManager(enable_multi_position=True, max_concurrent_positions=3)
    
    # Enter position with setup_type attribution
    rm.enter_position(
        symbol="BTCUSDT",
        entry_price=10000.0,
        size=1.0,
        direction=PositionDirection.LONG,
        stop_loss=9000.0,
        take_profit=11000.0,
        setup_type="mr_extreme"
    )
    
    pos = rm.positions["BTCUSDT"]
    assert pos.setup_type == "mr_extreme"
