"""Unit tests for the quantitative market data platform domain layer (Milestone 0)."""

import pytest
import json
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError

from domain.value_objects import (
    Symbol,
    Price,
    Side,
    OrderType,
    LiquidityType,
    ExchangeTimestamp,
    Quantity,
)
from domain.entities import (
    OrderBookLevel,
    OrderBookSnapshot,
    TradeTick,
    OpenInterest,
    FundingRate,
    LiquidationEvent,
    MarkPrice,
    IndexPrice,
    PremiumIndex,
    MarketState,
    VolumeProfile,
    SessionStatistics,
)
from domain.events import (
    OrderBookUpdatedEvent,
    TradeReceivedEvent,
    OpenInterestUpdatedEvent,
    FundingUpdatedEvent,
    LiquidationDetectedEvent,
    FeatureGeneratedEvent,
    EventType,
)
from domain.ports.data_ports import (
    MarketDataCollectorPort,
    MarketDataStoragePort,
    FeatureGeneratorPort,
    ReplayEnginePort,
    DataValidationPort,
)


@pytest.mark.unit
def test_value_objects_validations():
    """Verify value objects enforce constraints and properties."""
    # Symbol validations
    sym = Symbol("BTC-USDT")
    assert sym.value == "BTC-USDT"
    assert sym.base_asset() == "BTC"
    assert sym.quote_asset() == "USDT"

    with pytest.raises(ValueError, match="Invalid symbol format"):
        Symbol("INVALID_SYMBOL_12345")

    # ExchangeTimestamp validations
    ts = ExchangeTimestamp(1700000000000)
    assert ts.to_millis() == 1700000000000
    assert isinstance(ts.to_datetime(), datetime)
    assert ts.to_datetime().tzinfo == timezone.utc

    with pytest.raises(ValueError, match="Exchange timestamp must be a positive integer"):
        ExchangeTimestamp(-100)
    with pytest.raises(ValueError, match="Exchange timestamp must be a positive integer"):
        ExchangeTimestamp(0)

    # Quantity validations
    qty = Quantity(Decimal("1.5"), "BTC")
    assert qty.value == Decimal("1.5")
    assert qty.unit == "BTC"

    with pytest.raises(ValueError, match="Quantity value cannot be negative"):
        Quantity(Decimal("-0.1"), "BTC")
    with pytest.raises(ValueError, match="Quantity unit cannot be empty"):
        Quantity(Decimal("1.0"), "")

    # Compare timestamps
    ts2 = ExchangeTimestamp(1700000000001)
    assert ts < ts2
    assert ts2 > ts
    assert ts <= ts2
    assert ts2 >= ts


@pytest.mark.unit
def test_value_objects_immutability():
    """Verify value objects are immutable (frozen)."""
    ts = ExchangeTimestamp(1700000000000)
    qty = Quantity(Decimal("1.5"), "BTC")

    with pytest.raises(FrozenInstanceError):
        ts.millis = 1700000000001  # type: ignore

    with pytest.raises(FrozenInstanceError):
        qty.value = Decimal("2.0")  # type: ignore


@pytest.mark.unit
def test_order_book_invariants():
    """Verify OrderBookSnapshot invariants: bids descending, asks ascending, non-crossing."""
    symbol = Symbol("BTC-USDT")
    ts = ExchangeTimestamp(1700000000000)

    # Valid levels
    bid1 = OrderBookLevel(Price(Decimal("99.0"), symbol), Quantity(Decimal("1.0"), "BTC"))
    bid2 = OrderBookLevel(Price(Decimal("98.0"), symbol), Quantity(Decimal("2.0"), "BTC"))
    ask1 = OrderBookLevel(Price(Decimal("101.0"), symbol), Quantity(Decimal("1.0"), "BTC"))
    ask2 = OrderBookLevel(Price(Decimal("102.0"), symbol), Quantity(Decimal("2.0"), "BTC"))

    # Valid snapshot
    snapshot = OrderBookSnapshot(
        symbol=symbol,
        timestamp=ts,
        bids=[bid1, bid2],
        asks=[ask1, ask2],
        sequence_id=12345
    )
    assert snapshot.sequence_id == 12345

    # Check immutability
    with pytest.raises(FrozenInstanceError):
        snapshot.sequence_id = 999  # type: ignore

    # Test crossed order book (best bid >= best ask)
    crossed_bid = OrderBookLevel(Price(Decimal("101.5"), symbol), Quantity(Decimal("1.0"), "BTC"))
    with pytest.raises(ValueError, match="Order book is crossed"):
        OrderBookSnapshot(
            symbol=symbol,
            timestamp=ts,
            bids=[crossed_bid],
            asks=[ask1],
            sequence_id=12345
        )

    # Test bids sorting (must be descending)
    with pytest.raises(ValueError, match="Bids must be ordered in descending price order"):
        OrderBookSnapshot(
            symbol=symbol,
            timestamp=ts,
            bids=[bid2, bid1],
            asks=[ask1, ask2],
            sequence_id=12345
        )

    # Test asks sorting (must be ascending)
    with pytest.raises(ValueError, match="Asks must be ordered in ascending price order"):
        OrderBookSnapshot(
            symbol=symbol,
            timestamp=ts,
            bids=[bid1, bid2],
            asks=[ask2, ask1],
            sequence_id=12345
        )

    # Test level symbol mismatch
    wrong_symbol = Symbol("ETH-USDT")
    wrong_bid = OrderBookLevel(Price(Decimal("99.0"), wrong_symbol), Quantity(Decimal("1.0"), "BTC"))
    with pytest.raises(ValueError, match="Level symbol mismatch"):
        OrderBookSnapshot(
            symbol=symbol,
            timestamp=ts,
            bids=[wrong_bid],
            asks=[ask1],
            sequence_id=12345
        )


@pytest.mark.unit
def test_trade_tick_validations():
    """Verify TradeTick invariants and properties."""
    symbol = Symbol("BTC-USDT")
    ts = ExchangeTimestamp(1700000000000)
    price = Price(Decimal("100.0"), symbol)
    qty = Quantity(Decimal("0.5"), "BTC")

    # Valid tick
    tick = TradeTick(
        symbol=symbol,
        trade_id=98765,
        price=price,
        quantity=qty,
        timestamp=ts,
        side=Side.BUY
    )
    assert tick.side == Side.BUY

    # Invalid trade ID
    with pytest.raises(ValueError, match="Trade ID cannot be negative"):
        TradeTick(symbol=symbol, trade_id=-1, price=price, quantity=qty, timestamp=ts, side=Side.BUY)

    # Symbol mismatch
    wrong_price = Price(Decimal("100.0"), Symbol("ETH-USDT"))
    with pytest.raises(ValueError, match="Price symbol mismatch"):
        TradeTick(symbol=symbol, trade_id=98765, price=wrong_price, quantity=qty, timestamp=ts, side=Side.BUY)


@pytest.mark.unit
def test_market_state_and_constituent_models():
    """Verify composite MarketState and component entities."""
    symbol = Symbol("BTC-USDT")
    ts = ExchangeTimestamp(1700000000000)

    oi = OpenInterest(symbol, Quantity(Decimal("1000.0"), "BTC"), ts)
    funding = FundingRate(symbol, Decimal("0.0001"), ts, ExchangeTimestamp(1700000000000 + 8 * 3600000))
    mark = MarkPrice(symbol, Price(Decimal("45000.0"), symbol), ts)
    idx = IndexPrice(symbol, Price(Decimal("45010.0"), symbol), ts)
    prem = PremiumIndex(symbol, Decimal("0.0002"), ts)

    state = MarketState(
        symbol=symbol,
        timestamp=ts,
        mark_price=mark,
        index_price=idx,
        premium_index=prem,
        open_interest=oi,
        funding_rate=funding
    )
    assert state.symbol == symbol

    # Invalid funding rate (implausible value)
    with pytest.raises(ValueError, match="Funding rate value .* is implausible"):
        FundingRate(symbol, Decimal("0.06"), ts, ts)

    # Constituent symbol mismatch
    wrong_symbol = Symbol("ETH-USDT")
    wrong_oi = OpenInterest(wrong_symbol, Quantity(Decimal("1000.0"), "ETH"), ts)
    with pytest.raises(ValueError, match="MarketState constituent symbol mismatch"):
        MarketState(
            symbol=symbol,
            timestamp=ts,
            mark_price=mark,
            index_price=idx,
            premium_index=prem,
            open_interest=wrong_oi,
            funding_rate=funding
        )


@pytest.mark.unit
def test_liquidation_event():
    """Verify LiquidationEvent validations."""
    symbol = Symbol("BTC-USDT")
    ts = ExchangeTimestamp(1700000000000)
    
    liq = LiquidationEvent(
        symbol=symbol,
        side=Side.SELL,
        price=Price(Decimal("45000.0"), symbol),
        quantity=Quantity(Decimal("10.0"), "BTC"),
        timestamp=ts
    )
    assert liq.side == Side.SELL


@pytest.mark.unit
def test_volume_profile_invariants():
    """Verify VolumeProfile bounds check and sorting."""
    symbol = Symbol("BTC-USDT")
    ts = ExchangeTimestamp(1700000000000)
    
    bins = {
        Decimal("45000.0"): Quantity(Decimal("100.0"), "BTC"),
        Decimal("45100.0"): Quantity(Decimal("200.0"), "BTC")
    }
    
    vp = VolumeProfile(
        symbol=symbol,
        timestamp=ts,
        bins=bins,
        value_area_high=Price(Decimal("45200.0"), symbol),
        value_area_low=Price(Decimal("44800.0"), symbol),
        point_of_control=Price(Decimal("45100.0"), symbol)
    )
    assert vp.point_of_control.value == Decimal("45100.0")

    # Value area low exceeds high
    with pytest.raises(ValueError, match="Value area low .* cannot exceed high"):
        VolumeProfile(
            symbol=symbol,
            timestamp=ts,
            bins=bins,
            value_area_high=Price(Decimal("44700.0"), symbol),
            value_area_low=Price(Decimal("44800.0"), symbol),
            point_of_control=Price(Decimal("45100.0"), symbol)
        )

    # POC outside value area
    with pytest.raises(ValueError, match="Point of control .* must fall within value area"):
        VolumeProfile(
            symbol=symbol,
            timestamp=ts,
            bins=bins,
            value_area_high=Price(Decimal("45200.0"), symbol),
            value_area_low=Price(Decimal("44800.0"), symbol),
            point_of_control=Price(Decimal("45300.0"), symbol)
        )


@pytest.mark.unit
def test_session_statistics_invariants():
    """Verify SessionStatistics bounds and price sanity check."""
    symbol = Symbol("BTC-USDT")
    ts = ExchangeTimestamp(1700000000000)

    stats = SessionStatistics(
        symbol=symbol,
        timestamp=ts,
        open=Price(Decimal("45000.0"), symbol),
        high=Price(Decimal("45500.0"), symbol),
        low=Price(Decimal("44500.0"), symbol),
        close=Price(Decimal("45200.0"), symbol),
        volume=Quantity(Decimal("5000.0"), "BTC"),
        vwap=Price(Decimal("45100.0"), symbol)
    )
    assert stats.high.value == Decimal("45500.0")

    # Low exceeds high
    with pytest.raises(ValueError, match="Session low .* cannot exceed high"):
        SessionStatistics(
            symbol=symbol,
            timestamp=ts,
            open=Price(Decimal("45000.0"), symbol),
            high=Price(Decimal("44000.0"), symbol),
            low=Price(Decimal("44500.0"), symbol),
            close=Price(Decimal("44200.0"), symbol),
            volume=Quantity(Decimal("5000.0"), "BTC"),
            vwap=Price(Decimal("44100.0"), symbol)
        )

    # Open price outside high/low bounds
    with pytest.raises(ValueError, match="Price .* is outside session range"):
        SessionStatistics(
            symbol=symbol,
            timestamp=ts,
            open=Price(Decimal("45600.0"), symbol),
            high=Price(Decimal("45500.0"), symbol),
            low=Price(Decimal("44500.0"), symbol),
            close=Price(Decimal("45200.0"), symbol),
            volume=Quantity(Decimal("5000.0"), "BTC"),
            vwap=Price(Decimal("45100.0"), symbol)
        )


@pytest.mark.unit
def test_deterministic_serialization():
    """Verify that all models serialize cleanly and deterministically."""
    symbol = Symbol("BTC-USDT")
    ts = ExchangeTimestamp(1700000000000)

    # Level dict
    level = OrderBookLevel(Price(Decimal("99.0"), symbol), Quantity(Decimal("1.5"), "BTC"))
    level_dict = level.to_dict()
    assert level_dict == {"price": "99.0", "quantity": "1.5"}
    assert json.dumps(level_dict) == '{"price": "99.0", "quantity": "1.5"}'

    # Snapshot serialization
    snapshot = OrderBookSnapshot(
        symbol=symbol,
        timestamp=ts,
        bids=[level],
        asks=[OrderBookLevel(Price(Decimal("101.0"), symbol), Quantity(Decimal("2.5"), "BTC"))],
        sequence_id=12345
    )
    snap_dict = snapshot.to_dict()
    assert snap_dict["symbol"] == "BTC-USDT"
    assert snap_dict["timestamp"] == 1700000000000
    assert snap_dict["bids"] == [{"price": "99.0", "quantity": "1.5"}]
    assert snap_dict["asks"] == [{"price": "101.0", "quantity": "2.5"}]
    assert snap_dict["sequence_id"] == 12345

    # Check stability (JSON output byte-identical)
    assert json.dumps(snap_dict) == json.dumps(snapshot.to_dict())

    # TradeTick serialization
    tick = TradeTick(
        symbol=symbol,
        trade_id=98765,
        price=Price(Decimal("100.0"), symbol),
        quantity=Quantity(Decimal("0.5"), "BTC"),
        timestamp=ts,
        side=Side.BUY
    )
    assert tick.to_dict() == {
        "symbol": "BTC-USDT",
        "trade_id": 98765,
        "price": "100.0",
        "quantity": "0.5",
        "timestamp": 1700000000000,
        "side": "BUY"
    }


@pytest.mark.unit
def test_deterministic_equality():
    """Verify deterministic value object and entity equality."""
    sym1 = Symbol("BTC-USDT")
    sym2 = Symbol("BTC-USDT")
    assert sym1 == sym2

    ts1 = ExchangeTimestamp(1700000000000)
    ts2 = ExchangeTimestamp(1700000000000)
    assert ts1 == ts2

    level1 = OrderBookLevel(Price(Decimal("99.0"), sym1), Quantity(Decimal("1.5"), "BTC"))
    level2 = OrderBookLevel(Price(Decimal("99.0"), sym2), Quantity(Decimal("1.5"), "BTC"))
    assert level1 == level2


@pytest.mark.unit
def test_domain_events_instantiation():
    """Verify all domain event subclasses and event types."""
    symbol = Symbol("BTC-USDT")
    ts = ExchangeTimestamp(1700000000000)

    # 1. OrderBookUpdatedEvent
    snapshot = OrderBookSnapshot(
        symbol=symbol,
        timestamp=ts,
        bids=[],
        asks=[],
        sequence_id=123
    )
    event_ob = OrderBookUpdatedEvent(
        event_type=EventType.ORDER_BOOK_UPDATED,
        timestamp=datetime.now(timezone.utc),
        source="test_collector",
        snapshot=snapshot
    )
    assert event_ob.event_type == EventType.ORDER_BOOK_UPDATED
    assert event_ob.snapshot == snapshot

    # 2. TradeReceivedEvent
    tick = TradeTick(
        symbol=symbol,
        trade_id=1,
        price=Price(Decimal("100.0"), symbol),
        quantity=Quantity(Decimal("1.0"), "BTC"),
        timestamp=ts,
        side=Side.BUY
    )
    event_trade = TradeReceivedEvent(
        event_type=EventType.TRADE_RECEIVED,
        timestamp=datetime.now(timezone.utc),
        source="test_collector",
        tick=tick
    )
    assert event_trade.event_type == EventType.TRADE_RECEIVED
    assert event_trade.tick == tick

    # 3. OpenInterestUpdatedEvent
    oi = OpenInterest(symbol, Quantity(Decimal("500.0"), "BTC"), ts)
    event_oi = OpenInterestUpdatedEvent(
        event_type=EventType.OPEN_INTEREST_UPDATED,
        timestamp=datetime.now(timezone.utc),
        source="test_collector",
        open_interest=oi
    )
    assert event_oi.event_type == EventType.OPEN_INTEREST_UPDATED
    assert event_oi.open_interest == oi

    # 4. FundingUpdatedEvent
    funding = FundingRate(symbol, Decimal("0.0001"), ts, ts)
    event_funding = FundingUpdatedEvent(
        event_type=EventType.FUNDING_UPDATED,
        timestamp=datetime.now(timezone.utc),
        source="test_collector",
        funding_rate=funding
    )
    assert event_funding.event_type == EventType.FUNDING_UPDATED

    # 5. LiquidationDetectedEvent
    liq = LiquidationEvent(
        symbol=symbol,
        side=Side.BUY,
        price=Price(Decimal("100.0"), symbol),
        quantity=Quantity(Decimal("10.0"), "BTC"),
        timestamp=ts
    )
    event_liq = LiquidationDetectedEvent(
        event_type=EventType.LIQUIDATION_DETECTED,
        timestamp=datetime.now(timezone.utc),
        source="test_collector",
        event=liq
    )
    assert event_liq.event_type == EventType.LIQUIDATION_DETECTED

    # 6. FeatureGeneratedEvent
    event_feat = FeatureGeneratedEvent(
        event_type=EventType.FEATURE_GENERATED,
        timestamp=datetime.now(timezone.utc),
        source="test_engine",
        feature_name="CVD",
        feature_value=1250.5,
        symbol=symbol
    )
    assert event_feat.event_type == EventType.FEATURE_GENERATED
    assert event_feat.feature_name == "CVD"
    assert event_feat.feature_value == 1250.5


class DummyCollector(MarketDataCollectorPort):
    """Dummy class to prove MarketDataCollectorPort interface compatibility."""
    def start_collecting(self, symbols, callbacks):
        pass
    def stop_collecting(self):
        pass
    def is_connected(self):
        return True


class DummyStorage(MarketDataStoragePort):
    """Dummy class to prove MarketDataStoragePort interface compatibility."""
    def store_trade_tick(self, tick):
        pass
    def store_order_book_snapshot(self, snapshot):
        pass
    def store_market_state(self, state):
        pass
    def retrieve_trade_ticks(self, symbol, start, end):
        return []
    def retrieve_order_book_snapshots(self, symbol, start, end):
        return []


@pytest.mark.unit
def test_ports_conformance():
    """Verify that port interfaces are correctly defined and subclassable."""
    coll = DummyCollector()
    assert coll.is_connected() is True

    store = DummyStorage()
    assert store.retrieve_trade_ticks(Symbol("BTC-USDT"), datetime.now(), datetime.now()) == []
