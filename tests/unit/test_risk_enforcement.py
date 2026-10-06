"""Evidence-based verification that the portfolio risk engine is enforced on the order path (E11 P2)."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest


def _broker_admission_order(symbol="NEWUSDT"):
    from decimal import Decimal
    from domain.entities import Order, OrderSide
    from domain.value_objects import Money, Symbol

    return Order(
        symbol=Symbol(symbol),
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
        price=Money(Decimal("100"), "USDT"),
        stop_loss_price=Money(Decimal("98"), "USDT"),
        take_profit_price=Money(Decimal("104"), "USDT"),
        requested_leverage=Decimal("5"),
    )


def test_configured_vst_order_cap_and_initial_stop_roe_are_enforced(monkeypatch):
    from types import SimpleNamespace
    from infrastructure.risk.risk_enforcement import build_vst_risk_enforcement
    from domain.value_objects import Money

    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(risk=SimpleNamespace(
            max_order_notional_amount=201.0,
            max_initial_stop_roe_pct=35.0,
            max_leverage=10.0,
        )),
    )
    enforcer = build_vst_risk_enforcement()
    assert enforcer._rm.max_position_exposure == 201.0
    order = _broker_admission_order("CAPUSDT")
    order.requested_leverage = Decimal("10")
    order.stop_loss_price = Money(Decimal("94"), "USDT")
    allowed, reason = enforcer.enforce(order)
    assert allowed, reason
    assert order.stop_loss_price.amount == Decimal("96.500")


def test_vst_portfolio_notional_cap_is_shared_by_risk_engine_and_broker_gate(monkeypatch):
    import logging
    from types import SimpleNamespace
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    risk = SimpleNamespace(
        max_order_notional_amount=201.0,
        max_initial_stop_roe_pct=35.0,
        max_leverage=5.0,
        max_leverage_limit=5.0,
        vst_max_portfolio_notional_usdt=3200.0,
    )
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(
            risk=risk,
            safety=SimpleNamespace(max_open_positions=14, max_long_positions=7, max_short_positions=7),
        ),
    )
    risk_manager = build_vst_risk_enforcement()._rm
    assert risk_manager.max_portfolio_exposure == 3200.0
    assert risk_manager.starting_equity == 1000.0
    risk_manager.daily_pnl = -51.0
    assert not risk_manager.is_trading_allowed()  # existing 5% / $50 daily-loss gate
    risk_manager.daily_pnl = 0.0
    risk_manager.equity_curve = [1000.0, 840.0]
    assert not risk_manager.is_trading_allowed()  # existing 15% drawdown gate

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("test_shared_vst_portfolio_cap")
    broker._establish_and_verify_leverage = lambda *args: (True, "verified")
    calls = []
    position = {
        "symbol": "OLD-USDT", "positionAmt": "31.89", "positionSide": "LONG",
        "markPrice": "100", "avgPrice": "100", "leverage": "5",
    }

    def request(method, endpoint, **kwargs):
        calls.append(method)
        return {"code": 0, "data": [position]}

    broker._make_request = request
    allowed, reason = broker._assert_entry_admission(_broker_admission_order())
    assert allowed, reason  # 3189 + 10 = 3199

    position["positionAmt"] = "31.95"
    allowed, reason = broker._assert_entry_admission(_broker_admission_order())
    assert not allowed  # 3195 + 10 = 3205
    assert "portfolio exposure limit exceeded" in reason
    assert calls == ["GET", "GET"]


@pytest.mark.parametrize("cap", [0, -1, float("nan"), float("inf")])
def test_invalid_vst_portfolio_notional_cap_fails_closed(cap):
    from types import SimpleNamespace
    from infrastructure.risk.risk_enforcement import configured_vst_portfolio_exposure

    with pytest.raises(ValueError, match="invalid configured VST portfolio notional cap"):
        configured_vst_portfolio_exposure(SimpleNamespace(vst_max_portfolio_notional_usdt=cap))


def test_initial_stop_roe_cap_is_symmetric_for_short(monkeypatch):
    from types import SimpleNamespace
    from domain.entities import OrderSide
    from domain.value_objects import Money
    from infrastructure.risk.risk_enforcement import build_vst_risk_enforcement

    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(risk=SimpleNamespace(
            max_order_notional_amount=201.0,
            max_initial_stop_roe_pct=35.0,
            max_leverage=10.0,
        )),
    )
    order = _broker_admission_order("SHORTUSDT")
    order.side = OrderSide.SELL
    order.requested_leverage = Decimal("10")
    order.stop_loss_price = Money(Decimal("106"), "USDT")
    allowed, reason = build_vst_risk_enforcement().enforce(order)
    assert allowed, reason
    assert order.stop_loss_price.amount == Decimal("103.500")


def test_bingx_final_boundary_rejects_outward_rounded_stop_without_network(monkeypatch):
    import logging
    from types import SimpleNamespace
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
    from infrastructure.services.symbol_validator import symbol_validator
    from domain.value_objects import Money

    monkeypatch.setattr(symbol_validator, "get_approved_symbols", lambda: ["NEWUSDT"])
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(risk=SimpleNamespace(
            max_leverage=10.0,
            max_leverage_limit=10.0,
            max_initial_stop_roe_pct=35.0,
        )),
    )
    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("networkless_stop_boundary")
    broker._format_quantity = lambda symbol, qty: str(qty)
    broker._format_price = lambda symbol, price: str(price - 0.1)
    broker._make_request = lambda *args, **kwargs: pytest.fail("authenticated request attempted")
    order = _broker_admission_order()
    order.requested_leverage = Decimal("10")
    order.stop_loss_price = Money(Decimal("96.5"), "USDT")

    result = broker._execute_order_after_admission(order)

    assert result["success"] is False
    assert "maximum initial stop ROE" in result["error"]


def test_bingx_final_admission_blocks_at_real_broker_position_capacity(monkeypatch):
    """Internal risk state cannot permit entries beyond the exchange's real position count."""
    import logging
    from types import SimpleNamespace
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("test_capacity_admission")
    positions = [
        {"symbol": "BTC-USDT", "positionAmt": "0.01", "positionSide": "LONG", "avgPrice": "100", "markPrice": "100", "leverage": "5"},
        {"symbol": "ETH-USDT", "positionAmt": "0.01", "positionSide": "LONG", "avgPrice": "100", "markPrice": "100", "leverage": "5"},
    ]
    monkeypatch.setattr(
        broker, "_make_request", lambda *args, **kwargs: {"code": 0, "data": positions}
    )
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(
            safety=SimpleNamespace(max_open_positions=2),
            risk=SimpleNamespace(max_leverage=5, max_leverage_limit=5),
        ),
    )

    allowed, reason = broker._assert_entry_admission(_broker_admission_order())

    assert allowed is False
    assert "capacity reached" in reason


@pytest.mark.parametrize(
    ("existing_side", "entry_side", "blocked"),
    [
        ("LONG", "BUY", True),
        ("LONG", "SELL", False),
        ("SHORT", "SELL", True),
        ("SHORT", "BUY", False),
    ],
)
def test_bingx_final_admission_applies_directional_capacity(
    monkeypatch, existing_side, entry_side, blocked
):
    import logging
    from types import SimpleNamespace
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("test_directional_capacity")
    calls = []
    positions = [
        {"symbol": f"OLD{i}-USDT", "positionAmt": "0.1", "positionSide": existing_side,
         "avgPrice": "100", "markPrice": "100", "leverage": "5"}
        for i in range(7)
    ]

    def request(method, endpoint, **kwargs):
        calls.append((method, endpoint))
        return {"code": 0, "data": positions}

    broker._make_request = request
    broker._establish_and_verify_leverage = lambda *args: (True, "verified")
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(
            safety=SimpleNamespace(
                max_open_positions=14, max_long_positions=7, max_short_positions=7
            ),
            risk=SimpleNamespace(max_leverage=5, max_leverage_limit=5),
        ),
    )
    order = _broker_admission_order()
    order.side = OrderSide(entry_side)
    if entry_side == "SELL":
        order.stop_loss_price = Money(Decimal("102"), "USDT")
        order.take_profit_price = Money(Decimal("96"), "USDT")

    allowed, reason = broker._assert_entry_admission(order)

    assert allowed is not blocked, reason
    if blocked:
        assert f"{existing_side.lower()} capacity reached" in reason
    assert all(method == "GET" for method, _ in calls)


@pytest.mark.parametrize("position_side", [None, "UNKNOWN"])
def test_bingx_final_admission_fails_closed_on_unknown_position_side(monkeypatch, position_side):
    import logging
    from types import SimpleNamespace
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("test_unknown_position_side")
    broker._make_request = lambda *args, **kwargs: {
        "code": 0,
        "data": [{"symbol": "OLD-USDT", "positionAmt": "1", "positionSide": position_side}],
    }
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(
            safety=SimpleNamespace(max_open_positions=10),
            risk=SimpleNamespace(max_leverage=5, max_leverage_limit=5),
        ),
    )

    allowed, reason = broker._assert_entry_admission(_broker_admission_order())

    assert not allowed
    assert "unknown side" in reason


def test_bingx_final_admission_blocks_duplicate_from_real_broker_snapshot(monkeypatch):
    import logging
    from types import SimpleNamespace
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("test_duplicate_admission")
    monkeypatch.setattr(
        broker,
        "_make_request",
        lambda *args, **kwargs: {
            "code": 0,
                "data": [{"symbol": "NEW-USDT", "positionAmt": "1", "positionSide": "LONG", "avgPrice": "100", "markPrice": "100", "leverage": "5"}],
        },
    )
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(
            safety=SimpleNamespace(max_open_positions=5),
            risk=SimpleNamespace(max_leverage=5, max_leverage_limit=5),
        ),
    )

    allowed, reason = broker._assert_entry_admission(_broker_admission_order())

    assert allowed is False
    assert "duplicate position blocked" in reason


def test_bingx_final_admission_fails_closed_when_position_snapshot_is_unavailable(monkeypatch):
    import logging
    from types import SimpleNamespace
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("test_snapshot_admission")
    monkeypatch.setattr(
        broker, "_make_request", lambda *args, **kwargs: {"code": 100001, "msg": "timestamp invalid"}
    )
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(
            safety=SimpleNamespace(max_open_positions=5),
            risk=SimpleNamespace(max_leverage=5, max_leverage_limit=5),
        ),
    )

    allowed, reason = broker._assert_entry_admission(_broker_admission_order())

    assert allowed is False
    assert "snapshot unavailable" in reason


@pytest.mark.parametrize(
    ("position", "expected_reason"),
    [
        (
            {"symbol": "BTC-USDT", "positionAmt": "nan", "avgPrice": "100", "markPrice": "100", "leverage": "5"},
            "non-finite quantity",
        ),
        (
            {"symbol": "BTC-USDT", "positionAmt": "1", "positionSide": "LONG", "avgPrice": "100", "markPrice": "nan", "leverage": "5"},
            "non-finite mark price",
        ),
        (
            {"symbol": "BTC-USDT", "positionAmt": "1", "positionSide": "LONG", "avgPrice": "0", "markPrice": "0", "leverage": "5"},
            "positive finite reference price",
        ),
    ],
)
def test_bingx_final_admission_rejects_non_finite_or_unpriced_open_positions(
    monkeypatch, position, expected_reason
):
    import logging
    from types import SimpleNamespace
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("test_malformed_exposure_admission")
    calls = []

    def request(method, endpoint, **kwargs):
        calls.append((method, endpoint))
        return {"code": 0, "data": [position]}

    monkeypatch.setattr(broker, "_make_request", request)
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(
            safety=SimpleNamespace(max_open_positions=5),
            risk=SimpleNamespace(max_leverage=5, max_leverage_limit=5),
        ),
    )

    allowed, reason = broker._assert_entry_admission(_broker_admission_order())

    assert allowed is False
    assert expected_reason in reason
    assert not any(method == "POST" for method, _ in calls)

from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager, Position, PositionDirection
from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.risk.risk_enforcement import (
    RiskEnforcement,
    VST_MAX_ORDER_NOTIONAL,
    VST_MAX_PORTFOLIO_EXPOSURE,
    build_vst_risk_enforcement,
)
from shared.live_execution_guard import LiveExecutionGuard, ExecutionMode


def _order(qty, price, side=OrderSide.BUY, sl_price=None, include_sl=True):
    stop_loss = None
    if include_sl:
        stop_loss = Money(Decimal(str(sl_price if sl_price is not None else float(price) * 0.98)), "USDT")
    return Order(symbol=Symbol("BTCUSDT"), side=side, quantity=Decimal(str(qty)),
                 price=Money(Decimal(str(price)), "USDT"), order_type="MARKET",
                 strategy_name="trend_following", timestamp=datetime.now(timezone.utc),
                 stop_loss_price=stop_loss)


@pytest.mark.parametrize(
    ("quantity", "price"),
    [
        ("NaN", "100"),
        ("Infinity", "100"),
        ("1", "NaN"),
        ("1", "Infinity"),
    ],
)
def test_order_path_risk_gate_rejects_non_finite_size_or_price(quantity, price):
    order = _order(quantity, price, sl_price="98")
    enforcement = build_vst_risk_enforcement()

    allowed, reason = enforcement.enforce(order)

    assert allowed is False
    assert "positive and finite" in reason


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


def test_vst_execution_risk_enforcer_rejects_notional_above_hard_cap():
    enf = build_vst_risk_enforcement()

    assert enf._rm.max_portfolio_exposure == VST_MAX_PORTFOLIO_EXPOSURE
    assert enf._rm.max_position_exposure == VST_MAX_ORDER_NOTIONAL
    allowed, reason = enf.enforce(_order(0.00032828125, 64000))  # $21.01

    assert not allowed
    assert "exceeds max position limit" in reason


def test_vst_execution_risk_enforcer_accepts_decimal_exact_cap_without_float_drift():
    order = _order(Decimal("300"), Decimal("0.07"))
    assert float(order.quantity) * float(order.price.amount) > VST_MAX_ORDER_NOTIONAL
    assert order.quantity * order.price.amount == Decimal("21")

    allowed, reason = build_vst_risk_enforcement().enforce(order)

    assert allowed, reason
    assert float(order.quantity) * float(order.price.amount) <= VST_MAX_ORDER_NOTIONAL


def test_vst_execution_risk_enforcer_rejects_portfolio_exposure_above_hard_cap():
    enf = build_vst_risk_enforcement()
    enf._rm.positions["ETHUSDT"] = Position(
        symbol="ETHUSDT",
        entry_price=1.0,
        size=990.0,
        direction=PositionDirection.LONG,
        stop_loss=0.98,
        take_profit=1.02,
        entry_time=datetime.now(timezone.utc),
    )

    allowed, reason = enf.enforce(_order(0.0003125, 64000))  # $20; total would be $1,010

    assert not allowed
    assert "Portfolio exposure would exceed limit" in reason


def test_guard_fallback_uses_vst_hard_cap():
    guard = LiveExecutionGuard()
    settings = type("S", (), {"broker": type("B", (), {
        "paper_trading": True,
        "testnet": True,
        "bingx_testnet": True,
        "bingx_order_placement_enabled": True,
    })()})()

    decision = guard.evaluate("bingx", settings, _order(0.00032828125, 64000))  # $21.01

    assert decision.mode is ExecutionMode.BLOCKED
    assert decision.rule == "2b:risk_engine"


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
    """Verify that Stop Loss exit activates persistent 60m cooldown dynamically across any allowed symbol (BTC, ETH, SOL, XRP, LTC, ADA)."""
    rm = EnterpriseRiskManager()
    enf = RiskEnforcement(rm)

    # Test dynamic multi-symbol enforcement
    test_symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "LTC-USDT", "ADA-USDT"]

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


def test_blacklisted_symbol_rejection():
    """Verify that blacklisted symbols like XMRUSDT are rejected fail-closed at the risk barrier."""
    enf = RiskEnforcement(EnterpriseRiskManager())
    xmr_order = Order(symbol=Symbol("XMRUSDT"), side=OrderSide.BUY, quantity=Decimal("1.0"),
                      price=Money(Decimal("100.0"), "USDT"), order_type="MARKET",
                      strategy_name="trend_following", timestamp=datetime.now(timezone.utc),
                      stop_loss_price=Money(Decimal("98.0"), "USDT"))
    allowed, reason = enf.enforce(xmr_order)
    assert not allowed
    assert "PERMANENT_BLACKLIST" in reason


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
