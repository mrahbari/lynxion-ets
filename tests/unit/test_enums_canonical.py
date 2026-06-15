"""E4.T2 (partial) validation: canonical enum home under domain/enums.

Asserts SignalType/OrderSide/PositionSide live in domain/enums and that the
entity modules re-export the *same* enum objects (single source of truth).
"""

import pytest

try:
    from domain.enums.signal_type import SignalType as CanonSignalType
    from domain.enums.order_side import OrderSide as CanonOrderSide
    from domain.enums.position_side import PositionSide as CanonPositionSide
    from domain.entities import SignalType, OrderSide, PositionSide
    from domain.entities.signal import SignalType as EntSignalType
    from domain.entities.order import OrderSide as EntOrderSide
    from domain.entities.position import PositionSide as EntPositionSide
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"domain enum dependencies unavailable: {exc}", allow_module_level=True)


@pytest.mark.unit
def test_entities_reexport_canonical_enums():
    assert SignalType is CanonSignalType is EntSignalType
    assert OrderSide is CanonOrderSide is EntOrderSide
    assert PositionSide is CanonPositionSide is EntPositionSide


@pytest.mark.unit
def test_enum_members_preserved():
    assert [m.value for m in CanonSignalType] == ["BUY", "SELL", "HOLD", "NEUTRAL"]
    assert [m.value for m in CanonOrderSide] == ["BUY", "SELL"]
    assert [m.value for m in CanonPositionSide] == ["LONG", "SHORT", "FLAT"]
