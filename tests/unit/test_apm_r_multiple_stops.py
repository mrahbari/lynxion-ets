"""Standard R-multiple stop management (default APM mode).

E7 replay (697 real platform entries, 1m paths, fees+slippage): the legacy ROE breakeven +
fixed 0.5% trail was the worst policy (-0.018R/trade, PF 0.93); breakeven at 1.5R and a 1.5R
trail after 2R was +0.039..+0.089R/trade better (paired). OKBUSDT live: the legacy trail
amended the exchange stop 18 times in 25 minutes in 0.01-0.1% steps.
"""
from types import SimpleNamespace as N

import pytest

from infrastructure.risk.active_position_manager import ActivePositionManager


class _Broker:
    def __init__(self, stop_price, side="LONG", entry=100.0):
        self.side, self.entry, self.mark = side, entry, entry
        self.stop_price = stop_price

    def get_all_positions(self):
        qty = 2.0 if self.side == "LONG" else -2.0
        return [N(symbol="OKBUSDT", quantity=qty, side=N(value=self.side), entry_price=self.entry,
                  leverage=10, mark_price=self.mark)]

    def get_pending_orders(self, sym):
        return self.get_pending_orders_evidence(sym)["orders"]

    def get_pending_orders_evidence(self, sym):
        close = "SELL" if self.side == "LONG" else "BUY"
        return {"status": "OK", "orders": [{"type": "STOP_MARKET", "side": close,
                                            "positionSide": self.side, "stopPrice": str(self.stop_price),
                                            "orderId": "SL-1"}]}


@pytest.fixture
def apm(monkeypatch):
    monkeypatch.setenv("APM_STOP_MODE", "r")
    monkeypatch.setenv("APM_MIN_AMEND_SECONDS", "0")
    m = ActivePositionManager(be_trigger_roe=7.0)
    m._resolve_target_broker = lambda broker, symbol=None: broker
    sent = []

    def sync(broker, sym, is_long, qty, price, observation_context=None):
        sent.append(round(price, 6))
        broker.stop_price = price
        return True

    m._sync_sl_to_exchange = sync
    return m, sent


def _walk(m, broker, prices):
    for p in prices:
        broker.mark = p
        m.evaluate_open_positions(broker)


def test_long_breakeven_at_1_5R_then_trail_1_5R_after_2R(apm):
    m, sent = apm
    b = _Broker(stop_price=98.0)                  # R = 2.0
    _walk(m, b, [100.5, 102.0, 102.9])            # < 1.5R: nothing
    assert sent == []
    _walk(m, b, [103.0])                          # 1.5R -> breakeven + 0.15%
    assert sent == [pytest.approx(100.15)]
    _walk(m, b, [104.0])                          # 2R -> trail 104 - 3 = 101
    assert sent[-1] == pytest.approx(101.0)
    _walk(m, b, [104.2, 104.4])                   # improvements < 0.25R are not sent
    assert len(sent) == 2
    _walk(m, b, [104.6])                          # 101.6: +0.6 >= 0.5 -> sent
    assert sent[-1] == pytest.approx(101.6)
    _walk(m, b, [103.0, 102.0])                   # pullback never loosens the stop
    assert sent[-1] == pytest.approx(101.6)


def test_short_is_mirrored(apm):
    m, sent = apm
    b = _Broker(stop_price=102.0, side="SHORT")   # R = 2.0
    _walk(m, b, [99.0, 97.0])
    assert sent == [pytest.approx(99.85)]
    _walk(m, b, [96.0])
    assert sent[-1] == pytest.approx(99.0)


def test_amend_rate_limit(apm, monkeypatch):
    m, sent = apm
    m.min_amend_seconds = 3600
    b = _Broker(stop_price=98.0)
    _walk(m, b, [103.0, 104.0, 106.0])            # only the first move inside the window
    assert sent == [pytest.approx(100.15)]


def test_stop_is_never_requested_through_the_market(apm):
    m, sent = apm
    b = _Broker(stop_price=98.0)
    _walk(m, b, [103.0])
    b.mark = 100.1                                # price fell back below breakeven target
    m._positions_state["OKBUSDT"]["current_sl_price"] = 98.0
    m._positions_state["OKBUSDT"]["last_stop_amend_ts"] = 0.0
    m.evaluate_open_positions(b)
    assert sent[-1] < 100.1
