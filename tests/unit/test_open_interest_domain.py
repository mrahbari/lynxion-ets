"""Unit tests for OpenInterest domain entity updates."""

import pytest
from decimal import Decimal
from domain.value_objects import Symbol, Quantity, Money, ExchangeTimestamp
from domain.entities.market_data import OpenInterest


def test_open_interest_with_value_quote():
    symbol = Symbol("BTCUSDT")
    value = Quantity(Decimal("15000.5"), unit="BTCUSDT")
    quote = Money(Decimal("950000000.00"), "USDT")
    ts = ExchangeTimestamp(1700000000000)

    oi = OpenInterest(
        symbol=symbol,
        value=value,
        timestamp=ts,
        value_quote=quote
    )

    assert oi.symbol == symbol
    assert oi.value.value == Decimal("15000.5")
    assert oi.value_quote.amount == Decimal("950000000.00")
    assert oi.value_quote.currency == "USDT"
    assert oi.timestamp.millis == 1700000000000

    d = oi.to_dict()
    assert d["symbol"] == "BTCUSDT"
    assert d["timestamp"] == 1700000000000
    assert d["value_quote"]["amount"] == "950000000.00"
    assert d["value_quote"]["currency"] == "USDT"


def test_open_interest_negative_quote_raises_error():
    symbol = Symbol("ETHUSDT")
    value = Quantity(Decimal("500.0"), unit="ETHUSDT")
    quote = Money(Decimal("-10.0"), "USDT")
    ts = ExchangeTimestamp(1700000000000)

    with pytest.raises(ValueError, match="Open Interest quote value cannot be negative"):
        OpenInterest(
            symbol=symbol,
            value=value,
            timestamp=ts,
            value_quote=quote
        )
