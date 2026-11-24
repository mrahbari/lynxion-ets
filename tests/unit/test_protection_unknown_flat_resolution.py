"""2026-11-24: a stop update racing the position's exit must not leave PROTECTION_UNKNOWN blocking all orders."""
from types import SimpleNamespace

import pytest

import infrastructure.execution.live_order_journal as jm
from infrastructure.risk.active_position_manager import ActivePositionManager


class Broker:
    def __init__(self, positions):
        self.positions = list(positions)

    def get_position(self, symbol):
        return self.positions.pop(0) if self.positions else None


@pytest.fixture
def journal():
    return jm.live_order_journal


def _apm():
    m = ActivePositionManager.__new__(ActivePositionManager)
    m.FLAT_CONFIRM_DELAY_S = 0.0
    return m


def test_flat_twice_resolves_and_unblocks_new_orders(journal):
    ref = journal.record_protection_unknown("NATGASUSDT", "SELL", 56.13, "bingx", stop_price=3.59)
    with pytest.raises(RuntimeError):
        journal.record_intent("BTCUSDT", "BUY", 1, "bingx", "x1")
    assert _apm()._resolve_protection_if_flat(Broker([None, None]), "NATGASUSDT", ref) is True
    assert journal.record_intent("BTCUSDT", "BUY", 1, "bingx", "x2")


def test_open_position_keeps_the_record(journal):
    ref = journal.record_protection_unknown("ZECUSDT", "BUY", 0.266, "bingx", stop_price=738.9)
    open_pos = SimpleNamespace(quantity=0.266)
    assert _apm()._resolve_protection_if_flat(Broker([None, open_pos]), "ZECUSDT", ref) is False   # blip then open
    assert any(o["order_ref"] == ref for o in journal.in_flight())
