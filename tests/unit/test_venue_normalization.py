"""Unit tests for the Market Venue Normalization Layer (Milestone 2)."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from domain.value_objects import (
    Symbol,
    Price,
    Quantity,
    Side,
    ExchangeVenue,
    MarketType,
    ContractType,
    InstrumentSpecification,
    ExchangeTimestamp,
)
from domain.entities import (
    CanonicalInstrument,
    SymbolMapping,
    InstrumentMapping,
    TradeTick,
    OrderBookSnapshot,
)
from infrastructure.data.venue_normalizer import VenueMarketDataNormalizer


@pytest.mark.unit
def test_instrument_specification_validation():
    """Verify that InstrumentSpecification enforces positive values and correct types."""
    # Valid spec
    spec = InstrumentSpecification(
        contract_size=Decimal("1.0"),
        tick_size=Decimal("0.1"),
        lot_size=Decimal("0.001"),
        min_quantity=Decimal("0.001"),
        max_leverage=100,
        funding_interval_hours=8,
        price_precision=2,
        quantity_precision=3
    )
    assert spec.max_leverage == 100

    # Negative contract size
    with pytest.raises(ValueError, match="Contract size must be strictly positive"):
        InstrumentSpecification(
            contract_size=Decimal("-1.0"),
            tick_size=Decimal("0.1"),
            lot_size=Decimal("0.001"),
            min_quantity=Decimal("0.001"),
            max_leverage=100,
            funding_interval_hours=8,
            price_precision=2,
            quantity_precision=3
        )

    # Negative price precision
    with pytest.raises(ValueError, match="Price precision cannot be negative"):
        InstrumentSpecification(
            contract_size=Decimal("1.0"),
            tick_size=Decimal("0.1"),
            lot_size=Decimal("0.001"),
            min_quantity=Decimal("0.001"),
            max_leverage=100,
            funding_interval_hours=8,
            price_precision=-1,
            quantity_precision=3
        )


@pytest.mark.unit
def test_canonical_instrument_symbol_mismatch():
    """Verify that CanonicalInstrument detects asset mismatches with its Symbol constituents."""
    spec = InstrumentSpecification(
        contract_size=Decimal("1.0"),
        tick_size=Decimal("0.1"),
        lot_size=Decimal("0.001"),
        min_quantity=Decimal("0.001"),
        max_leverage=100,
        funding_interval_hours=8,
        price_precision=2,
        quantity_precision=3
    )

    symbol = Symbol("BTC-USDT")

    # Valid instrument
    inst = CanonicalInstrument(
        symbol=symbol,
        base_asset="BTC",
        quote_asset="USDT",
        venue=ExchangeVenue.BINANCE_FUTURES,
        market_type=MarketType.FUTURES,
        contract_type=ContractType.PERPETUAL,
        specification=spec
    )
    assert inst.base_asset == "BTC"

    # Base asset mismatch
    with pytest.raises(ValueError, match="Base asset mismatch"):
        CanonicalInstrument(
            symbol=symbol,
            base_asset="ETH",
            quote_asset="USDT",
            venue=ExchangeVenue.BINANCE_FUTURES,
            market_type=MarketType.FUTURES,
            contract_type=ContractType.PERPETUAL,
            specification=spec
        )

    # Quote asset mismatch
    with pytest.raises(ValueError, match="Quote asset mismatch"):
        CanonicalInstrument(
            symbol=symbol,
            base_asset="BTC",
            quote_asset="USD",
            venue=ExchangeVenue.BINANCE_FUTURES,
            market_type=MarketType.FUTURES,
            contract_type=ContractType.PERPETUAL,
            specification=spec
        )


@pytest.mark.unit
def test_instrument_mapping_asset_mismatch():
    """Verify that InstrumentMapping enforces base and quote asset matching between alpha and execution instruments."""
    spec = InstrumentSpecification(
        contract_size=Decimal("1.0"),
        tick_size=Decimal("0.1"),
        lot_size=Decimal("0.001"),
        min_quantity=Decimal("0.001"),
        max_leverage=100,
        funding_interval_hours=8,
        price_precision=2,
        quantity_precision=3
    )

    alpha_inst = CanonicalInstrument(
        symbol=Symbol("BTC-USDT"),
        base_asset="BTC",
        quote_asset="USDT",
        venue=ExchangeVenue.BINANCE_FUTURES,
        market_type=MarketType.FUTURES,
        contract_type=ContractType.PERPETUAL,
        specification=spec
    )

    # Valid matching execution instrument
    exec_inst = CanonicalInstrument(
        symbol=Symbol("BTC-USDT"),
        base_asset="BTC",
        quote_asset="USDT",
        venue=ExchangeVenue.BINGX_FUTURES,
        market_type=MarketType.FUTURES,
        contract_type=ContractType.PERPETUAL,
        specification=spec
    )

    mapping = InstrumentMapping(
        alpha_instrument=alpha_inst,
        execution_instrument=exec_inst,
        price_difference=Decimal("2.50"),
        latency_difference_ms=15
    )
    assert mapping.latency_difference_ms == 15

    # Base asset mismatch in mapping
    wrong_exec_inst = CanonicalInstrument(
        symbol=Symbol("ETH-USDT"),
        base_asset="ETH",
        quote_asset="USDT",
        venue=ExchangeVenue.BINGX_FUTURES,
        market_type=MarketType.FUTURES,
        contract_type=ContractType.PERPETUAL,
        specification=spec
    )

    with pytest.raises(ValueError, match="Base asset mismatch in instrument mapping"):
        InstrumentMapping(
            alpha_instrument=alpha_inst,
            execution_instrument=wrong_exec_inst,
            price_difference=Decimal("2.50"),
            latency_difference_ms=15
        )


@pytest.mark.unit
def test_symbol_mapping_validation():
    """Verify SymbolMapping validation constraints."""
    with pytest.raises(ValueError, match="Source symbol cannot be empty"):
        SymbolMapping("", ExchangeVenue.BINANCE_FUTURES, "BTC-USDT", ExchangeVenue.BINGX_FUTURES)


@pytest.mark.unit
def test_venue_normalization_binance():
    """Verify deterministic normalization of Binance Futures messages."""
    normalizer = VenueMarketDataNormalizer()

    # Raw Binance Trade Event
    raw_binance_trade = {
        "e": "trade",
        "E": 1700000000000,
        "s": "BTCUSDT",
        "t": 1234567,
        "p": "45000.50",
        "q": "0.150",
        "T": 1700000000000,
        "m": False  # Side.BUY
    }

    trade = normalizer.normalize_trade(raw_binance_trade, ExchangeVenue.BINANCE_FUTURES)
    assert isinstance(trade, TradeTick)
    assert trade.symbol.value == "BTC-USDT"
    assert trade.trade_id == 1234567
    assert trade.price.value == Decimal("45000.50")
    assert trade.quantity.value == Decimal("0.150")
    assert trade.side == Side.BUY
    assert trade.timestamp.to_millis() == 1700000000000

    # Raw Binance Book Depth snapshot
    raw_binance_book = {
        "s": "BTCUSDT",
        "E": 1700000000100,
        "lastUpdateId": 8888,
        "bids": [["44990.0", "1.5"], ["44980.0", "2.0"]],
        "asks": [["45010.0", "1.0"]]
    }

    ob = normalizer.normalize_order_book(raw_binance_book, ExchangeVenue.BINANCE_FUTURES)
    assert isinstance(ob, OrderBookSnapshot)
    assert ob.symbol.value == "BTC-USDT"
    assert ob.sequence_id == 8888
    assert len(ob.bids) == 2
    assert ob.bids[0].price.value == Decimal("44990.0")
    assert ob.asks[0].price.value == Decimal("45010.0")


@pytest.mark.unit
def test_venue_normalization_bingx():
    """Verify deterministic normalization of BingX Futures messages."""
    normalizer = VenueMarketDataNormalizer()

    # Raw BingX Trade Event
    raw_bingx_trade = {
        "symbol": "BTC-USDT",
        "tradeId": 987654,
        "price": "45005.20",
        "volume": "0.22",
        "time": 1700000000200,
        "side": "SELL"
    }

    trade = normalizer.normalize_trade(raw_bingx_trade, ExchangeVenue.BINGX_FUTURES)
    assert isinstance(trade, TradeTick)
    assert trade.symbol.value == "BTC-USDT"
    assert trade.trade_id == 987654
    assert trade.price.value == Decimal("45005.20")
    assert trade.quantity.value == Decimal("0.22")
    assert trade.side == Side.SELL

    # Raw BingX Order Book snapshot
    raw_bingx_book = {
        "symbol": "BTC-USDT",
        "ts": 1700000000300,
        "seq": 9999,
        "bids": [["45000.0", "3.0"]],
        "asks": [["45010.0", "4.0"]]
    }

    ob = normalizer.normalize_order_book(raw_bingx_book, ExchangeVenue.BINGX_FUTURES)
    assert isinstance(ob, OrderBookSnapshot)
    assert ob.symbol.value == "BTC-USDT"
    assert ob.sequence_id == 9999
    assert len(ob.bids) == 1


@pytest.mark.unit
def test_venue_normalization_with_explicit_mappings():
    """Verify that normalizer correctly translates symbols using explicit SymbolMapping entries."""
    mapping = SymbolMapping(
        source_symbol="BTCUSDT",
        source_venue=ExchangeVenue.BINANCE_FUTURES,
        execution_symbol="BTC-USDT",
        execution_venue=ExchangeVenue.BINGX_FUTURES
    )

    normalizer = VenueMarketDataNormalizer(mappings=[mapping])

    # Should translate source symbol
    sym1 = normalizer.normalize_symbol("BTCUSDT", ExchangeVenue.BINANCE_FUTURES)
    assert sym1.value == "BTCUSDT"

    # Test fallback conversion on unmapped symbol
    sym2 = normalizer.normalize_symbol("ETHUSDT", ExchangeVenue.BINANCE_FUTURES)
    assert sym2.value == "ETH-USDT"
