"""E11-1: BingX VST empty position snapshots (code 0, []) must not look like a flat account."""
import pytest

from infrastructure.brokers.adapters import bingx_adapter as bx

OPEN = [{"symbol": "BTC-USDT", "positionAmt": "0.01", "positionSide": "LONG"}]


def test_empty_after_nonempty_is_unconfirmed_until_it_persists():
    bx.check_position_snapshot(OPEN, now=1000.0)
    with pytest.raises(bx.EmptySnapshotUnconfirmed):
        bx.check_position_snapshot([], now=1001.0)
    with pytest.raises(bx.EmptySnapshotUnconfirmed):
        bx.check_position_snapshot([], now=1001.0 + bx.EMPTY_CONFIRM_S - 1)
    bx.check_position_snapshot([], now=1001.0 + bx.EMPTY_CONFIRM_S)      # persisted: genuinely flat
    bx.check_position_snapshot([], now=1100.0)                           # and trusted afterwards


def test_blip_then_positions_back_resets():
    bx.check_position_snapshot(OPEN, now=0.0)
    with pytest.raises(bx.EmptySnapshotUnconfirmed):
        bx.check_position_snapshot([], now=5.0)
    bx.check_position_snapshot(OPEN, now=14.0)                           # blip over
    with pytest.raises(bx.EmptySnapshotUnconfirmed):                     # a new blip starts its own clock
        bx.check_position_snapshot([], now=50.0)


def test_empty_on_fresh_start_or_after_long_flat_is_trusted():
    bx.check_position_snapshot([], now=0.0)                              # never saw positions
    bx.check_position_snapshot(OPEN, now=0.0)
    bx.check_position_snapshot([], now=bx.NONEMPTY_MEMORY_S + 1)        # last positions long ago
    zero_rows = [{"symbol": "BTC-USDT", "positionAmt": "0"}]
    bx.check_position_snapshot(zero_rows, now=bx.NONEMPTY_MEMORY_S + 2)


def _broker(data):
    b = bx._BingXBroker.__new__(bx._BingXBroker)
    b._make_request = lambda *a, **k: {"code": 0, "data": data}
    return b


def test_get_open_positions_raises_on_blip_but_not_for_symbol_queries(monkeypatch):
    monkeypatch.setattr(bx, "v2_owned_symbols", lambda: frozenset())
    assert _broker(OPEN).get_open_positions() == OPEN
    with pytest.raises(bx.EmptySnapshotUnconfirmed):
        _broker([]).get_open_positions()
    assert _broker([]).get_open_positions(symbol="ETH-USDT") == []       # per-symbol empty is normal
