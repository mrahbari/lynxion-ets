from decimal import Decimal
from types import SimpleNamespace

import pytest

from scripts.run_investor_vst_demo import SYMBOL, sized_quantity, validate_preflight


def settings(*, paper=False, testnet=True, placement=True, brokers=None):
    return SimpleNamespace(
        broker=SimpleNamespace(
            paper_trading=paper,
            bingx_testnet=testnet,
            bingx_order_placement_enabled=placement,
            enabled_brokers=["bingx"] if brokers is None else brokers,
        ),
    )


def clear_coverage():
    return {"positions_missing_stop_loss": [], "positions_missing_take_profit": []}


def test_quantity_never_exceeds_twenty_usdt():
    quantity = sized_quantity(Decimal("0.2206"), 1)
    assert quantity == Decimal("90.6")
    assert quantity * Decimal("0.2206") <= Decimal("20")


@pytest.mark.parametrize("override", [
    {"paper": True}, {"testnet": False}, {"placement": False}, {"brokers": ["bingx", "binance"]}
])
def test_preflight_rejects_unsafe_runtime(override):
    with pytest.raises(RuntimeError):
        validate_preflight(settings(**override), [], clear_coverage())


def test_preflight_rejects_unprotected_existing_position():
    coverage = clear_coverage()
    coverage["positions_missing_stop_loss"] = ["XRPUSDT"]
    with pytest.raises(RuntimeError):
        validate_preflight(settings(), [], coverage)


def test_preflight_rejects_duplicate_symbol():
    position = SimpleNamespace(symbol=SimpleNamespace(value=SYMBOL))
    with pytest.raises(RuntimeError):
        validate_preflight(settings(), [position], clear_coverage())
