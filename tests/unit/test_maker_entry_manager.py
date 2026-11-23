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
    assert "L1" in svc.pending and not svc.sent              # still held right after the fill
    setup_clock = m.clock
    setup_clock.t = 181
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


class Wrapper:
    """Live shape: orchestrator holds BrokerExecutionService (scoped pending tracker) wrapping MultiBroker."""

    def __init__(self, router):
        self.broker, self.scoped, self.sent = router, set(), []

    def _pending_add(self, sym, side, oid):
        self.scoped.add(oid)

    def _pending_remove(self, sym, oid):
        self.scoped.discard(oid)

    def execute_order(self, order):
        self.sent.append(order)
        return "MKT1"


def test_wrapped_service_routes_lookup_and_uses_scoped_tracker(setup):
    make, clock = setup
    m, router = make([{"status": "NEW", "executed_qty": 0}, {"status": "CANCELLED", "executed_qty": 0}])
    w = Wrapper(router)
    m.register(w, _order(), "L1")
    assert w.scoped == {"L1"} and not router.pending          # duplicate check of the wrapper sees the hold
    clock.t = 901
    m.check_all()
    assert router.cancelled == ["L1"] and len(w.sent) == 1 and not w.scoped and not m._pending


def test_fill_journals_attached_protection_ids(setup, monkeypatch):
    import infrastructure.execution.live_order_journal as lj

    class FakeJournal:
        def __init__(self):
            self.calls = []

        def order_ref_for_exchange_order(self, oid):
            return "REF1"

        def record_submitted(self, ref, oid, exchange, protective_order_ids=None):
            self.calls.append((ref, oid, exchange, protective_order_ids))

    fj = FakeJournal()
    monkeypatch.setattr(lj, "live_order_journal", fj)
    make, _ = setup
    m, svc = make([{"status": "FILLED", "executed_qty": 1, "avg_price": 100}])
    svc.brokers["bingx"].get_pending_orders = lambda sym: [
        {"orderId": 11, "type": "STOP_MARKET", "side": "SELL", "stopPrice": "95.0"},
        {"orderId": 12, "type": "TAKE_PROFIT_MARKET", "side": "SELL", "stopPrice": "110.0"},
        {"orderId": 13, "type": "STOP_MARKET", "side": "BUY", "stopPrice": "95.0"}]
    m.register(svc, _order(), "L1")
    m.check_all()
    assert fj.calls == [("REF1", "L1", "bingx", {"STOP_MARKET": "11", "TAKE_PROFIT_MARKET": "12"})]


def test_fill_without_visible_protection_does_not_journal(setup, monkeypatch):
    import infrastructure.execution.live_order_journal as lj
    calls = []
    monkeypatch.setattr(lj, "live_order_journal", type("J", (), {
        "order_ref_for_exchange_order": lambda self, o: "REF1",
        "record_submitted": lambda self, *a, **k: calls.append(a)})())
    make, _ = setup
    m, svc = make([{"status": "FILLED", "executed_qty": 1, "avg_price": 100}])
    svc.brokers["bingx"].get_pending_orders = lambda sym: []
    m.register(svc, _order(), "L1")
    m.check_all()
    assert calls == [] and "L1" in svc.pending
