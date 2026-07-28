"""Unit tests verifying NGDP (Next Generation Dynamic Position) sizing logic."""

import pytest
from decimal import Decimal
from datetime import datetime
from domain.value_objects import Symbol, Money, Percentage
from domain.enums.order_side import OrderSide
from domain.enums.position_side import PositionSide
from domain.entities import ExecutionIntent
from domain.entities.position import Portfolio, Position as DomainPosition
from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager, PositionDirection
from infrastructure.risk.risk_engine_adapter import ConsolidatedRiskEngineAdapter


@pytest.fixture
def risk_setup():
    # Setup EnterpriseRiskManager with standard defaults
    risk_mgr = EnterpriseRiskManager(
        max_portfolio_exposure=100000.0,
        max_position_exposure=50000.0,
        max_risk_per_trade=0.02,  # 2%
        max_drawdown_pct=0.15,
        max_correlation=0.7
    )
    adapter = ConsolidatedRiskEngineAdapter(risk_mgr)
    return risk_mgr, adapter


def _create_intent(symbol_str, confidence_val):
    return ExecutionIntent(
        symbol=Symbol(symbol_str),
        strategy_name="OIFootprint",
        side=OrderSide.BUY,
        intent_confidence=Percentage(Decimal(str(confidence_val))),
        risk_parameters={
            "limit_price": 100.0,
            "stop_loss": 95.0
        },
        timestamp=datetime.now()
    )


def _create_portfolio(total_value, positions=None):
    return Portfolio(
        positions=positions or [],
        cash_balance=Money(Decimal(str(total_value)), "USDT"),
        total_value=Money(Decimal(str(total_value)), "USDT"),
        timestamp=datetime.now()
    )


@pytest.mark.unit
def test_ngdp_high_confidence_vs_low_confidence(risk_setup):
    risk_mgr, adapter = risk_setup
    portfolio = _create_portfolio(10000.0)

    # 1. High confidence setup (1.0)
    intent_high = _create_intent("BTCUSDT", 1.0)
    size_high = adapter.calculate_dynamic_size(intent_high, portfolio)

    # 2. Low confidence setup (0.5)
    intent_low = _create_intent("BTCUSDT", 0.5)
    size_low = adapter.calculate_dynamic_size(intent_low, portfolio)

    # High confidence must allocate larger position size
    assert size_high > 0.0
    assert size_low > 0.0
    assert size_high > size_low


@pytest.mark.unit
def test_ngdp_drawdown_reduces_size(risk_setup):
    risk_mgr, adapter = risk_setup
    portfolio = _create_portfolio(10000.0)
    intent = _create_intent("BTCUSDT", 1.0)

    # 1. Normal case: no drawdown
    risk_mgr.equity_curve = [10000.0, 10000.0]
    size_normal = adapter.calculate_dynamic_size(intent, portfolio)

    # 2. Drawdown case: 5% drawdown (peak 10500 to current 10000)
    risk_mgr.equity_curve = [10500.0, 10000.0]
    size_drawdown = adapter.calculate_dynamic_size(intent, portfolio)

    # Sizing under drawdown must be strictly smaller
    assert size_normal > 0.0
    assert size_drawdown > 0.0
    assert size_normal > size_drawdown


@pytest.mark.unit
def test_ngdp_correlation_reduces_size(risk_setup):
    risk_mgr, adapter = risk_setup
    intent = _create_intent("BTCUSDT", 1.0)

    # 1. Normal case: no other positions
    portfolio_empty = _create_portfolio(10000.0)
    size_normal = adapter.calculate_dynamic_size(intent, portfolio_empty)

    # 2. Correlation case: highly correlated position (correlation = 0.9 > max 0.7)
    risk_mgr.correlation_matrix = {
        "BTCUSDT": {"ETHUSDT": 0.9},
        "ETHUSDT": {"BTCUSDT": 0.9}
    }
    
    correlated_position = DomainPosition(
        symbol=Symbol("ETHUSDT"),
        side=PositionSide.LONG,
        quantity=Decimal("1.0"),
        entry_price=Money(Decimal("3000.0"), "USDT"),
        timestamp=datetime.now()
    )
    portfolio_corr = _create_portfolio(10000.0, [correlated_position])
    size_correlated = adapter.calculate_dynamic_size(intent, portfolio_corr)

    # Sizing with correlated asset in portfolio must be strictly smaller
    assert size_normal > 0.0
    assert size_correlated > 0.0
    assert size_normal > size_correlated


@pytest.mark.unit
def test_ngdp_high_volatility_reduces_size(risk_setup):
    risk_mgr, adapter = risk_setup
    portfolio = _create_portfolio(10000.0)
    intent = _create_intent("BTCUSDT", 1.0)

    # 1. Low volatility case (e.g. ATR = 2.0)
    size_low_vol = adapter.calculate_dynamic_size(intent, portfolio, volatility=2.0)

    # 2. High volatility case (e.g. ATR = 10.0)
    size_high_vol = adapter.calculate_dynamic_size(intent, portfolio, volatility=10.0)

    # Higher volatility (ATR) must result in smaller position size to keep unit risk constant
    assert size_low_vol > 0.0
    assert size_high_vol > 0.0
    assert size_low_vol > size_high_vol
