"""2026-11-25: stop moves on coarse-tick coins (NOT, ADA, IMX, AUCTION) were never verified because the exchange
rounds the trigger to its tick (0.000285571 -> 0.0002856, 1.02e-4 relative > the 1e-4 tolerance). One tick of the
returned price's precision is now accepted; a genuinely different stop is still rejected."""
import pytest

from infrastructure.risk.active_position_manager import ActivePositionManager


class _Broker:
    def __init__(self, stop):
        self.stop = stop

    def get_pending_orders(self, symbol):
        return [{"symbol": symbol, "type": "STOP_MARKET", "side": "BUY", "positionSide": "SHORT",
                 "stopPrice": self.stop, "orderId": 7}]


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    import infrastructure.risk.active_position_manager as apm
    monkeypatch.setattr(apm.time, "sleep", lambda s: None)


def _verify(stop, expected):
    return ActivePositionManager._query_pending_stop_visibility(
        _Broker(stop), "NOT-USDT", "BUY", "SHORT", expected, expected_order_id=7)["verified"]


def test_tick_rounded_trigger_is_verified():
    assert _verify("0.0002856", 0.000285571)


def test_different_stop_is_still_rejected():
    assert not _verify("0.0002870", 0.000285571)          # 5 ticks away


def test_price_tick_parsing():
    assert ActivePositionManager._price_tick("0.0002856") == pytest.approx(1e-7)
    assert ActivePositionManager._price_tick("1.284") == pytest.approx(1e-3)
    assert ActivePositionManager._price_tick("1745") == 0.0 and ActivePositionManager._price_tick(None) == 0.0
