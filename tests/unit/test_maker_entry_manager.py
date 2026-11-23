"""E8-2: maker entry lifecycle — fill, timeout cancel + market fallback, post-only reject, partial, void setup."""
from decimal import Decimal

import pytest

from domain.entities import Order
from domain.enums.order_side import OrderSide
from domain.value_objects import Money
from infrastructure.execution.maker_entry_manager import MakerEntryManager, maker_mode


class FakeBroker:
    def __init__(self, fills):
        self.fills = fills                     # list of dicts returned in order (last one repeats)

    def get_order_fill(self, oid, sym):
        return self.fills.pop(0) if len(self.fills) > 1 else self.fills[0]


class FakeService:
    def __init__(self, fills, cancel_ok=True):
        self.brokers = {"bingx": FakeBroker(fills)}
        self.cancel_ok, self.cancelled, self.sent, self.pending = cancel_ok, [], [], set()

    def _lookup_order(self, oid):
        return "bingx", "BTCUSDT"

    def cancel_order(self, oid):
        self.cancelled.append(oid)
        return self.cancel_ok

    def execute_order(self, order):
        self.sent.append(order)
        return "MKT1"

    def _add_pending_order(self, sym, side, oid):
        self.pending.add(oid)

    def _remove_pending_order(self, sym, oid):
        self.pending.discard(oid)


def _order(side=OrderSide.BUY, sl=95.0, tp=110.0):
    return Order(symbol="BTCUSDT", side=side, quantity=Decimal("1"), order_type="LIMIT", time_in_force="POST_ONLY",
                 price=Money(amount=100.0, currency="USDT"), client_order_id="cid",
                 stop_loss_price=Money(amount=sl, currency="USDT"), take_profit_price=Money(amount=tp, currency="USDT"))


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("ENTRY_MAKER_TIMEOUT_S", "900")
    clock = Clock()

    def make(fills, quotes=(100.0, 100.1), **kw):
        svc = FakeService(fills, **kw)
        m = MakerEntryManager(quotes=lambda s: quotes, clock=clock)
        m._ensure_thread = lambda: None
        return m, svc
    return make, clock


def test_mode_flag(monkeypatch):
    monkeypatch.delenv("ENTRY_ORDER_MODE", raising=False)
    assert maker_mode() is False
    monkeypatch.setenv("ENTRY_ORDER_MODE", "maker")
    assert maker_mode() is True


def test_filled_releases_symbol_no_fallback(setup):
    make, _ = setup
    m, svc = make([{"status": "FILLED", "executed_qty": 1, "avg_price": 100}])
    m.register(svc, _order(), "L1")
    assert "L1" in svc.pending
    m.check_all()
    assert not svc.pending and not svc.sent and not m._pending


def test_resting_before_timeout_waits(setup):
    make, clock = setup
    m, svc = make([{"status": "NEW", "executed_qty": 0}])
    m.register(svc, _order(), "L1")
    clock.t = 899
    m.check_all()
    assert "L1" in m._pending and "L1" in svc.pending and not svc.cancelled


def test_timeout_cancels_then_market_fallback(setup):
    make, clock = setup
    m, svc = make([{"status": "NEW", "executed_qty": 0}, {"status": "CANCELLED", "executed_qty": 0}])
    m.register(svc, _order(), "L1")
    clock.t = 901
    m.check_all()
    assert svc.cancelled == ["L1"] and len(svc.sent) == 1
    mkt = svc.sent[0]
    assert mkt.order_type == "MARKET" and mkt.client_order_id is None
    assert float(mkt.price.amount) == pytest.approx(100.1)               # BUY at the ask
    assert float(mkt.stop_loss_price.amount) == 95.0 and not svc.pending and not m._pending


def test_post_only_reject_falls_back_immediately(setup):
    make, _ = setup
    m, svc = make([{"status": "CANCELED", "executed_qty": 0}])
    m.register(svc, _order(), "L1")
    m.check_all()
    assert not svc.cancelled and len(svc.sent) == 1


def test_partial_fill_at_timeout_no_fallback(setup):
    make, clock = setup
    m, svc = make([{"status": "PARTIALLY_FILLED", "executed_qty": 0.4},
                   {"status": "CANCELLED", "executed_qty": 0.4}])
    m.register(svc, _order(), "L1")
    clock.t = 901
    m.check_all()
    assert svc.cancelled == ["L1"] and not svc.sent and not m._pending


def test_cancel_failure_retries_next_pass(setup):
    make, clock = setup
    m, svc = make([{"status": "NEW", "executed_qty": 0}], cancel_ok=False)
    m.register(svc, _order(), "L1")
    clock.t = 901
    m.check_all()
    assert "L1" in m._pending and "L1" in svc.pending and not svc.sent


@pytest.mark.parametrize("quotes", [(94.0, 94.1), (110.5, 110.6)])
def test_fallback_skipped_when_price_beyond_sl_or_tp(setup, quotes):
    make, clock = setup
    m, svc = make([{"status": "NEW", "executed_qty": 0}, {"status": "CANCELLED", "executed_qty": 0}], quotes=quotes)
    m.register(svc, _order(), "L1")
    clock.t = 901
    m.check_all()
    assert svc.cancelled == ["L1"] and not svc.sent and not m._pending


def test_sell_fallback_uses_bid(setup):
    make, clock = setup
    m, svc = make([{"status": "EXPIRED", "executed_qty": 0}])
    m.register(svc, _order(OrderSide.SELL, sl=105.0, tp=90.0), "L1")
    m.check_all()
    assert float(svc.sent[0].price.amount) == pytest.approx(100.0)
