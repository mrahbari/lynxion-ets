"""Evidence-based verification that the portfolio risk engine is enforced on the order path (E11 P2)."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.risk.risk_enforcement import RiskEnforcement
from shared.live_execution_guard import LiveExecutionGuard, ExecutionMode


def _order(qty, price, side=OrderSide.BUY):
    return Order(symbol=Symbol("BTCUSDT"), side=side, quantity=Decimal(str(qty)),
                 price=Money(Decimal(str(price)), "USDT"), order_type="MARKET",
                 strategy_name="trend_following", timestamp=datetime.now(timezone.utc))


@pytest.fixture(autouse=True)
def _reset_breakers():
    from shared.circuit_breaker import circuit_breaker_manager
    circuit_breaker_manager.circuit_breakers.clear()
    yield
    circuit_breaker_manager.circuit_breakers.clear()


def test_enforce_approves_within_limits_and_counts():
    enf = RiskEnforcement(EnterpriseRiskManager())
    allowed, reason = enf.enforce(_order(0.002, 64000))   # ~$128 notional, within defaults
    assert allowed and "approved" in reason
    assert enf.checks == 1 and enf.denials == 0


def test_enforce_denies_when_position_too_large():
    enf = RiskEnforcement(EnterpriseRiskManager(max_position_exposure=100))
    allowed, reason = enf.enforce(_order(1, 64000))       # $64k notional > $100 limit
    assert not allowed and "risk engine" in reason
    assert enf.denials == 1


def test_enforce_denies_when_trading_halted():
    rm = EnterpriseRiskManager()
    rm.daily_pnl = -100000          # breach daily-loss limit -> is_trading_allowed False
    enf = RiskEnforcement(rm)
    allowed, reason = enf.enforce(_order(0.002, 64000))
    assert not allowed and "not allowed" in reason


def test_enforce_fails_closed_on_error():
    class Boom:
        def is_trading_allowed(self): raise RuntimeError("boom")
        def get_violations(self): return []
    enf = RiskEnforcement(Boom())
    allowed, reason = enf.enforce(_order(0.002, 64000))
    assert not allowed and "error" in reason


def test_guard_blocks_paper_order_on_risk_denial():
    """Risk denial blocks the order on EVERY path — even PAPER is not simulated."""
    guard = LiveExecutionGuard()
    enf = RiskEnforcement(EnterpriseRiskManager(max_position_exposure=100))
    guard.set_risk_enforcer(enf.enforce)
    settings = type("S", (), {"broker": type("B", (), {
        "paper_trading": True, "testnet": True, "bingx_testnet": True,
        "bingx_order_placement_enabled": True})()})()
    paper_called = {"v": False}
    guard.set_paper_fill_handler(lambda o: paper_called.__setitem__("v", True) or {"filled": True, "order_id": "X"})
    d, oid = guard.authorize_and_send("bingx", settings, _order(1, 64000),
                                      send_fn=lambda: "SENT")
    assert d.mode is ExecutionMode.BLOCKED and d.rule == "2b:risk_engine"
    assert oid is None and paper_called["v"] is False, "risk-denied order must not be paper-filled"


def test_exposure_accrues_via_register_fill_then_rejects():
    rm = EnterpriseRiskManager(max_portfolio_exposure=300, max_position_exposure=200)
    enf = RiskEnforcement(rm)
    # First order ($128) approved; register it -> exposure ~128.
    assert enf.enforce(_order(0.002, 64000))[0] is True
    enf.register_fill(_order(0.002, 64000), 64000.0)
    assert rm.get_total_exposure() > 0
    # A second $200 order would push portfolio exposure past the $300 cap -> rejected.
    allowed, reason = enf.enforce(_order(0.003125, 64000))   # ~$200
    assert not allowed
    st = enf.state()
    assert st["open_positions"] == 1 and st["enforce_denials"] >= 1
