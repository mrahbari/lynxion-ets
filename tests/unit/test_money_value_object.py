"""E4.T1 — unit tests for the value-object layer in domain/value_objects/money.py.

Pure, frozen domain value objects (no I/O). Focus is Money (arithmetic +
validation), with coverage of the sibling VOs in the same module (Symbol,
Percentage, Price, Volume, RiskValue, Correlation) since they share the file.
"""

from decimal import Decimal

import pytest

from domain.value_objects.money import (
    Money,
    Symbol,
    Percentage,
    Price,
    Volume,
    RiskValue,
    Correlation,
)


# --- Money: construction & validation -------------------------------------

@pytest.mark.unit
def test_money_coerces_amount_to_decimal_exactly():
    # Coercion goes through str(amount), so floats are captured exactly.
    m = Money(10.5, "USD")
    assert m.amount == Decimal("10.5")
    assert isinstance(m.amount, Decimal)


@pytest.mark.unit
def test_money_accepts_decimal_amount_unchanged():
    assert Money(Decimal("1.23"), "EUR").amount == Decimal("1.23")


@pytest.mark.unit
@pytest.mark.parametrize("currency", ["US", "U1D", "123", "U$D", ""])
def test_money_rejects_invalid_currency(currency):
    with pytest.raises(ValueError):
        Money(Decimal("1"), currency)


# --- Money: arithmetic -----------------------------------------------------

@pytest.mark.unit
def test_money_add_and_sub_same_currency_is_exact():
    assert Money(Decimal("1.1"), "USD") + Money(Decimal("2.2"), "USD") == Money(Decimal("3.3"), "USD")
    assert Money(Decimal("5"), "USD") - Money(Decimal("2"), "USD") == Money(Decimal("3"), "USD")


@pytest.mark.unit
def test_money_add_sub_reject_currency_mismatch_and_non_money():
    with pytest.raises(ValueError):
        Money(Decimal("1"), "USD") + Money(Decimal("1"), "EUR")
    with pytest.raises(ValueError):
        Money(Decimal("1"), "USD") - Money(Decimal("1"), "EUR")
    with pytest.raises(ValueError):
        Money(Decimal("1"), "USD") + 5


@pytest.mark.unit
def test_money_mul_by_numeric_only():
    assert Money(Decimal("2"), "USD") * 3 == Money(Decimal("6"), "USD")
    assert Money(Decimal("2"), "USD") * 1.5 == Money(Decimal("3.0"), "USD")
    with pytest.raises(ValueError):
        Money(Decimal("2"), "USD") * "3"


@pytest.mark.unit
def test_money_truediv_by_nonzero_numeric_only():
    assert Money(Decimal("6"), "USD") / 2 == Money(Decimal("3"), "USD")
    with pytest.raises(ValueError):
        Money(Decimal("6"), "USD") / 0
    with pytest.raises(ValueError):
        Money(Decimal("6"), "USD") / "2"


@pytest.mark.unit
def test_money_str_and_value_semantics():
    assert str(Money(Decimal("12.5"), "USD")) == "12.50 USD"
    # frozen dataclass -> value equality + hashable
    assert Money(Decimal("1"), "USD") == Money(Decimal("1"), "USD")
    assert len({Money(Decimal("1"), "USD"), Money(Decimal("1"), "USD")}) == 1


# --- Symbol ----------------------------------------------------------------

@pytest.mark.unit
def test_symbol_asset_extraction_dashed_and_plain():
    s = Symbol("BTC-USDT")
    assert s.base_asset() == "BTC"
    assert s.quote_asset() == "USDT"
    plain = Symbol("BTCUSDT")
    assert plain.base_asset() == "BTC"
    assert plain.quote_asset() == "USDT"


@pytest.mark.unit
def test_symbol_asset_extraction_unknown_quote_fallback():
    # No known quote asset -> length-based fallback branches (money.py:28,39).
    s = Symbol("ABCXYZ")          # 6 chars, no known quote suffix
    assert s.base_asset() == "ABCXYZ"
    assert s.quote_asset() == "ABCXYZ"


@pytest.mark.unit
def test_symbol_rejects_invalid_format():
    with pytest.raises(ValueError):
        Symbol("btcusdt")     # lowercase
    with pytest.raises(ValueError):
        Symbol("BTC/USDT")    # slash not allowed by the format regex


# --- Percentage ------------------------------------------------------------

@pytest.mark.unit
def test_percentage_conversions_and_str():
    p = Percentage(Decimal("0.05"))
    assert p.to_basis_points() == 500
    assert p.to_percentage() == 5.0
    assert str(p) == "5.00%"


@pytest.mark.unit
@pytest.mark.parametrize("bad", [Decimal("-0.01"), Decimal("1.5")])
def test_percentage_must_be_between_0_and_1(bad):
    with pytest.raises(ValueError):
        Percentage(bad)


# --- Price / Volume / RiskValue / Correlation: validation ------------------

@pytest.mark.unit
def test_price_and_volume_reject_negative():
    sym = Symbol("BTC-USDT")
    assert Price(Decimal("10"), sym).value == Decimal("10")
    with pytest.raises(ValueError):
        Price(Decimal("-1"), sym)
    with pytest.raises(ValueError):
        Volume(Decimal("-1"), sym)


@pytest.mark.unit
def test_risk_value_rejects_negative_and_overconfidence():
    assert RiskValue(Decimal("0.2"), "VAR").value == Decimal("0.2")
    with pytest.raises(ValueError):
        RiskValue(Decimal("-0.1"), "VAR")


@pytest.mark.unit
@pytest.mark.parametrize("bad", [Decimal("1.01"), Decimal("-1.5")])
def test_correlation_must_be_within_unit_interval(bad):
    sym1, sym2 = Symbol("BTC-USDT"), Symbol("ETH-USDT")
    with pytest.raises(ValueError):
        Correlation(bad, sym1, sym2)
    # valid boundary
    assert Correlation(Decimal("1"), sym1, sym2).value == Decimal("1")
