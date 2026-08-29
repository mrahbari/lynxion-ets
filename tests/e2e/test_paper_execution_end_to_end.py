"""End-to-end paper execution test (E11).

Drives the REAL MultiBrokerExecutionService.execute_order in paper mode with the
paper-trading engine wired into the guard, and an UNCONNECTED broker — proving:
  * paper orders are NOT dropped by the broker-connect gate (Phase-10 S1 fix),
  * the guard routes PAPER and the paper engine simulates the fill,
  * positions / realized PnL update, and zero real sends occur.
"""

import os
from types import SimpleNamespace

import pytest

from domain.entities import OrderSide, PositionSide
from domain.value_objects import Symbol


@pytest.fixture(autouse=True)
def _paper_env(monkeypatch):
    monkeypatch.setenv("BROKER_PAPER_TRADING", "true")
    monkeypatch.delenv("LIVE_TRADING", raising=False)
    from shared.circuit_breaker import circuit_breaker_manager
    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
    circuit_breaker_manager.circuit_breakers.clear()
    saved_cooldowns = dict(symbol_cooldown_gate._sl_cooldowns)
    saved_loss_history = {symbol: list(values) for symbol, values in symbol_cooldown_gate._symbol_loss_history.items()}
    symbol_cooldown_gate._sl_cooldowns.clear()
    symbol_cooldown_gate._symbol_loss_history.clear()
    yield
    circuit_breaker_manager.circuit_breakers.clear()
    symbol_cooldown_gate._sl_cooldowns = saved_cooldowns
    symbol_cooldown_gate._symbol_loss_history = saved_loss_history


def _make_service(engine, fake_broker):
    from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService
    from shared.logger import EnhancedLogger
    svc = object.__new__(MultiBrokerExecutionService)
    bcfg = SimpleNamespace(paper_trading=True, testnet=True, bingx_testnet=True,
                           bingx_order_placement_enabled=True, binance_order_placement_enabled=False,
                           mexc_order_placement_enabled=False, phemex_order_placement_enabled=False,
                           default_broker="bingx")
    svc._settings = SimpleNamespace(broker=bcfg,
                                    execution=SimpleNamespace(prevent_same_direction_trade_per_symbol=False))
    svc.brokers = {"bingx": fake_broker}
    svc.logger = EnhancedLogger("MultiBrokerExecutionService")
    svc._enhance_order_with_risk_parameters = lambda o: o
    svc._validate_order_risk = lambda o: True
    svc._validate_order_parameters_before_broker = lambda o: True
    svc._add_pending_order = lambda *a, **k: None
    svc._send_order_placed_notification = lambda *a, **k: None
    svc._has_pending_order_in_direction = lambda s, d: False
    return svc


def _order(side, qty, price):
    from domain.entities import Order
    from domain.value_objects import Money
    from decimal import Decimal
    from datetime import datetime, timezone
    stop_loss = price * (0.98 if side is OrderSide.BUY else 1.02)
    return Order(symbol=Symbol("BTCUSDT"), side=side, quantity=Decimal(str(qty)),
                 price=Money(Decimal(str(price)), "USDT"), order_type="MARKET",
                 strategy_name="trend_following", timestamp=datetime.now(timezone.utc),
                 stop_loss_price=Money(Decimal(str(stop_loss)), "USDT"))


def test_paper_order_fills_through_real_execution_path(tmp_path, monkeypatch):
    from shared.live_execution_guard import live_execution_guard
    from infrastructure.execution.paper_trading_engine import PaperTradingEngine
    from shared.execution_truth_ledger import execution_truth_ledger

    # Wire a fresh paper engine into the guard (the guard writes to the singleton ledger).
    engine = PaperTradingEngine(initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0005,
                                persist_path=str(tmp_path / "paper_state.json"))
    live_execution_guard.set_paper_fill_handler(engine.simulate_fill)
    try:
        class FakeBroker:
            connected = False               # deliberately NOT connected
            def __init__(self): self.sent = 0
            def place_order(self, order): self.sent += 1; return "SHOULD-NOT-SEND"
            def get_position(self, s): return None

        fake = FakeBroker()
        svc = _make_service(engine, fake)

        oid_buy = svc.execute_order(_order(OrderSide.BUY, 0.0003, 64000))
        assert oid_buy and oid_buy.startswith("PAPER-FILL-"), "paper order should fill, not drop at connect gate"
        assert fake.sent == 0, "no real send may occur in paper mode"
        pos = engine.positions["BTCUSDT"]
        assert pos.side == PositionSide.LONG and pos.quantity > 0

        # Close it -> realized PnL booked through the same real path.
        oid_sell = svc.execute_order(_order(OrderSide.SELL, 0.0003, 65000))
        assert oid_sell.startswith("PAPER-FILL-")
        assert engine.positions["BTCUSDT"].side == PositionSide.FLAT
        assert engine.realized_pnl != 0
        assert fake.sent == 0

        # The Execution Truth Ledger captured the paper fills (filter to our two order ids).
        recs = execution_truth_ledger.read_all()
        ours = [r for r in recs if r.get("event") == "result" and r.get("order_id") in {oid_buy, oid_sell}]
        assert len(ours) >= 2  # singleton ledger is append-only across runs; ids may recur
        assert all(r["route"] == "PAPER" and r["sent_to_exchange"] is False for r in ours)
        assert all(r.get("paper_fill") and r["paper_fill"].get("filled") for r in ours)
    finally:
        live_execution_guard.set_paper_fill_handler(None)
