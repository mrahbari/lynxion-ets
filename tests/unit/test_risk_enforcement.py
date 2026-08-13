"""Evidence-based verification that the portfolio risk engine is enforced on the order path (E11 P2)."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.risk.risk_enforcement import RiskEnforcement
from shared.live_execution_guard import LiveExecutionGuard, ExecutionMode


def _order(qty, price, side=OrderSide.BUY, sl_price=None, include_sl=True):
    stop_loss = None
    if include_sl:
        stop_loss = Money(Decimal(str(sl_price if sl_price is not None else float(price) * 0.98)), "USDT")
    return Order(symbol=Symbol("BTCUSDT"), side=side, quantity=Decimal(str(qty)),
                 price=Money(Decimal(str(price)), "USDT"), order_type="MARKET",
                 strategy_name="trend_following", timestamp=datetime.now(timezone.utc),
                 stop_loss_price=stop_loss)


@pytest.fixture(autouse=True)
def _reset_breakers():
    from shared.circuit_breaker import circuit_breaker_manager
    import os
    from infrastructure.risk.risk_enforcement import COOLDOWN_JOURNAL_PATH
    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
    circuit_breaker_manager.circuit_breakers.clear()
    symbol_cooldown_gate._sl_cooldowns.clear()
    if os.path.exists(COOLDOWN_JOURNAL_PATH):
        try:
            os.remove(COOLDOWN_JOURNAL_PATH)
        except Exception:
            pass
    yield
    circuit_breaker_manager.circuit_breakers.clear()
    symbol_cooldown_gate._sl_cooldowns.clear()
    if os.path.exists(COOLDOWN_JOURNAL_PATH):
        try:
            os.remove(COOLDOWN_JOURNAL_PATH)
        except Exception:
            pass


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


def test_60m_stop_loss_cooldown_enforcement_and_persistence():
    """Verify that Stop Loss exit activates persistent 60m cooldown dynamically across any symbol (BTC, ETH, SOL, XRP, LTC, XMR)."""
    rm = EnterpriseRiskManager()
    enf = RiskEnforcement(rm)

    # Test dynamic multi-symbol enforcement
    test_symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "LTC-USDT", "XMR-USDT"]

    for sym in test_symbols:
        raw_sym = sym.replace("-", "")
        # 1. Record SL exit on symbol
        enf.record_stop_loss_exit(sym)

        # 2. Verify order enforcement denies order on symbol
        sym_order = Order(symbol=Symbol(raw_sym), side=OrderSide.BUY, quantity=Decimal("1.0"),
                          price=Money(Decimal("100.0"), "USDT"), order_type="MARKET",
                          strategy_name="trend_following", timestamp=datetime.now(timezone.utc),
                          stop_loss_price=Money(Decimal("98.0"), "USDT"))

        allowed, reason = enf.enforce(sym_order)
        assert not allowed
        assert "60m Stop Loss Cooldown ACTIVE" in reason

    # 3. Verify disk persistence across fresh RiskEnforcement instantiation for all symbols
    fresh_enf = RiskEnforcement(EnterpriseRiskManager())
    for sym in test_symbols:
        raw_sym = sym.replace("-", "")
        sym_order = Order(symbol=Symbol(raw_sym), side=OrderSide.BUY, quantity=Decimal("1.0"),
                          price=Money(Decimal("100.0"), "USDT"), order_type="MARKET",
                          strategy_name="trend_following", timestamp=datetime.now(timezone.utc),
                          stop_loss_price=Money(Decimal("98.0"), "USDT"))

        allowed_fresh, reason_fresh = fresh_enf.enforce(sym_order)
        assert not allowed_fresh
        assert "60m Stop Loss Cooldown ACTIVE" in reason_fresh


def test_mandatory_stop_loss_rejection():
    """Verify that any order missing a stop-loss is immediately rejected by RiskEnforcement."""
    enf = RiskEnforcement(EnterpriseRiskManager())
    no_sl_order = _order(0.002, 64000, include_sl=False)

    allowed, reason = enf.enforce(no_sl_order)
    assert not allowed
    assert "Mandatory Stop-Loss policy violation" in reason


def test_unrealistic_stop_loss_distance_rejection():
    """Verify that an order with stop-loss distance > 50% of entry price is rejected."""
    enf = RiskEnforcement(EnterpriseRiskManager())

    # Entry = 64000, SL = 30000 (distance = 53.125% > 50%)
    extreme_sl_order = _order(0.002, 64000, sl_price=30000)

    allowed, reason = enf.enforce(extreme_sl_order)
    assert not allowed
    assert "exceeds safety boundary (50%)" in reason


def test_stop_loss_side_validation_rejection():
    """Verify that an order with stop-loss on the wrong side of entry is rejected."""
    enf = RiskEnforcement(EnterpriseRiskManager())

    # BUY order with SL ABOVE entry (Entry = 64000, SL = 65000) -> Invalid
    wrong_buy_sl = _order(0.002, 64000, side=OrderSide.BUY, sl_price=65000)
    allowed_buy, reason_buy = enf.enforce(wrong_buy_sl)
    assert not allowed_buy
    assert "must be strictly below entry price" in reason_buy

    # SELL order with SL BELOW entry (Entry = 64000, SL = 63000) -> Invalid
    wrong_sell_sl = _order(0.002, 64000, side=OrderSide.SELL, sl_price=63000)
    allowed_sell, reason_sell = enf.enforce(wrong_sell_sl)
    assert not allowed_sell
    assert "must be strictly above entry price" in reason_sell


def test_stop_loss_minimum_distance_rejection():
    """Verify that an order with stop-loss distance < 0.1% of entry price is rejected."""
    enf = RiskEnforcement(EnterpriseRiskManager())

    # Entry = 64000, SL = 63980 (distance = 0.031% < 0.1%)
    tight_sl_order = _order(0.002, 64000, sl_price=63980)

    allowed, reason = enf.enforce(tight_sl_order)
    assert not allowed
    assert "below minimum safety boundary (0.1%)" in reason


def test_symbol_formatting_equivalence_cooldown():
    """Verify that 60m SL Cooldown matches COTI-USDT and COTIUSDT interchangeably."""
    enf = RiskEnforcement(EnterpriseRiskManager())

    # Record exit with broker symbol string 'COTI-USDT'
    enf.record_stop_loss_exit("COTI-USDT")

    # Order created with symbol 'COTIUSDT'
    sl_order_clean = Order(
        symbol=Symbol("COTIUSDT"),
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        price=Money(Decimal("0.0145"), "USDT"),
        order_type="MARKET",
        strategy_name="mean_reversion",
        timestamp=datetime.now(timezone.utc),
        stop_loss_price=Money(Decimal("0.0140"), "USDT")
    )

    allowed, reason = enf.enforce(sl_order_clean)
    assert not allowed
    assert "60m Stop Loss Cooldown ACTIVE" in reason


def test_p1_1_short_side_safety_gate(monkeypatch):
    """Verify that P1.1 Short-Side Safety Gate blocks SHORT entries on anomalous high-wick symbols while allowing LONG entries."""
    monkeypatch.setenv("RESTRICTED_SHORT_SYMBOLS", "SEIUSDT,UNIUSDT,SOLUSDT")
    enf = RiskEnforcement(EnterpriseRiskManager())

    # 1. SHORT order on restricted high-wick symbol SEIUSDT -> MUST BE BLOCKED
    short_sei_order = Order(
        symbol=Symbol("SEIUSDT"),
        side=OrderSide.SELL,
        quantity=Decimal("100"),
        price=Money(Decimal("0.35"), "USDT"),
        order_type="MARKET",
        strategy_name="trend_following",
        timestamp=datetime.now(timezone.utc),
        stop_loss_price=Money(Decimal("0.36"), "USDT")
    )

    allowed_short, reason_short = enf.enforce(short_sei_order)
    assert not allowed_short
    assert "P1.1 Short-side safety gate ACTIVE" in reason_short

    # 2. LONG order on SEIUSDT -> MUST BE ALLOWED
    long_sei_order = Order(
        symbol=Symbol("SEIUSDT"),
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        price=Money(Decimal("0.35"), "USDT"),
        order_type="MARKET",
        strategy_name="trend_following",
        timestamp=datetime.now(timezone.utc),
        stop_loss_price=Money(Decimal("0.34"), "USDT")
    )

    allowed_long, reason_long = enf.enforce(long_sei_order)
    assert allowed_long
    assert "P1.1 Short-side safety gate" not in reason_long

    # 3. SHORT order on normal symbol ETHUSDT -> MUST BE ALLOWED
    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
    symbol_cooldown_gate._sl_cooldowns.clear()

    short_eth_order = Order(
        symbol=Symbol("ETHUSDT"),
        side=OrderSide.SELL,
        quantity=Decimal("0.1"),
        price=Money(Decimal("3000"), "USDT"),
        order_type="MARKET",
        strategy_name="trend_following",
        timestamp=datetime.now(timezone.utc),
        stop_loss_price=Money(Decimal("3050"), "USDT")
    )

    allowed_eth, reason_eth = enf.enforce(short_eth_order)
    assert allowed_eth, f"ETHUSDT SHORT should be allowed, got: {reason_eth}"


def test_market_order_price_zero_cooldown_blocked():
    """Test Group A: Verify that market orders with price=0 or un-populated price are BLOCKED during active SL cooldown."""
    enf = RiskEnforcement(EnterpriseRiskManager())
    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
    symbol_cooldown_gate.record_stop_loss_exit("TUTUSDT")

    # Order with unpopulated price (price=0)
    market_zero_price_order = Order(
        symbol=Symbol("TUTUSDT"),
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        price=Money(Decimal("0"), "USDT"),
        order_type="MARKET",
        strategy_name="trend_following",
        timestamp=datetime.now(timezone.utc),
        stop_loss_price=Money(Decimal("0.10"), "USDT")
    )

    allowed, reason = enf.enforce(market_zero_price_order)
    assert not allowed
    assert "60m Stop Loss Cooldown ACTIVE" in reason


def test_reconciliation_active_positions_persistence_restart():
    """Test Group B: Verify that BrokerReconciliationService persists active symbols across restarts."""
    from infrastructure.execution.broker_reconciliation import BrokerReconciliationService, ACTIVE_POSITIONS_JOURNAL_PATH
    import os

    if os.path.exists(ACTIVE_POSITIONS_JOURNAL_PATH):
        try:
            os.remove(ACTIVE_POSITIONS_JOURNAL_PATH)
        except Exception:
            pass

    recon1 = BrokerReconciliationService()
    # Cycle 1: Position active on TUTUSDT
    recon1._process_position_closures(broker=None, current_active_symbols={"TUTUSDT"})
    assert os.path.exists(ACTIVE_POSITIONS_JOURNAL_PATH)

    # Process restart: Instantiate fresh BrokerReconciliationService
    recon2 = BrokerReconciliationService()
    assert "TUTUSDT" in recon2._previous_active_symbols

    # Cycle 2: Position closed on TUTUSDT with a mock broker returning a loss exit order
    class MockBroker:
        def get_order_history(self, sym, limit=20):
            return [{
                "orderId": "12345",
                "status": "FILLED",
                "type": "STOP_MARKET",
                "realizedProfit": "-1.50"
            }]

    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
    symbol_cooldown_gate._sl_cooldowns.clear()

    recon2._process_position_closures(broker=MockBroker(), current_active_symbols=set())
    # TUTUSDT close is detected, and SL cooldown registered
    assert "TUTUSDT" in symbol_cooldown_gate._sl_cooldowns

