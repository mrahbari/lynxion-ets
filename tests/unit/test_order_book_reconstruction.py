"""Unit and integration tests for the L2 Order Book Reconstruction Engine (Milestone 2)."""

import pytest
from decimal import Decimal

from domain.value_objects import Symbol, Price, Quantity, ExchangeTimestamp
from domain.entities import OrderBookLevel, OrderBookSnapshot
from domain.entities.order_book import OrderBookBuilder, OrderBookState, SequenceGapError


@pytest.fixture
def btc_symbol():
    return Symbol("BTC-USDT")


@pytest.fixture
def eth_symbol():
    return Symbol("ETH-USDT")


@pytest.fixture
def initial_snapshot(btc_symbol):
    ts = ExchangeTimestamp(1700000000000)
    # Bids descending: 45000.0, 44990.0, 44980.0
    bids = [
        OrderBookLevel(Price(Decimal("45000.0"), btc_symbol), Quantity(Decimal("1.5"), "BTC")),
        OrderBookLevel(Price(Decimal("44990.0"), btc_symbol), Quantity(Decimal("2.5"), "BTC")),
        OrderBookLevel(Price(Decimal("44980.0"), btc_symbol), Quantity(Decimal("4.0"), "BTC")),
    ]
    # Asks ascending: 45010.0, 45020.0, 45030.0
    asks = [
        OrderBookLevel(Price(Decimal("45010.0"), btc_symbol), Quantity(Decimal("1.0"), "BTC")),
        OrderBookLevel(Price(Decimal("45020.0"), btc_symbol), Quantity(Decimal("3.0"), "BTC")),
        OrderBookLevel(Price(Decimal("45030.0"), btc_symbol), Quantity(Decimal("5.0"), "BTC")),
    ]
    return OrderBookSnapshot(
        symbol=btc_symbol,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_id=100
    )


@pytest.mark.unit
def test_order_book_snapshot_initialization(btc_symbol, initial_snapshot):
    """Verify that applying a snapshot correctly initializes the state."""
    builder = OrderBookBuilder(btc_symbol)
    assert not builder.is_initialized

    builder.apply_snapshot(initial_snapshot)
    assert builder.is_initialized
    assert builder.state.last_update_id == 100
    assert builder.state.get_best_bid() == Decimal("45000.0")
    assert builder.state.get_best_ask() == Decimal("45010.0")
    assert builder.state.get_spread() == Decimal("10.0")
    assert builder.state.get_mid_price() == Decimal("45005.0")

    # Verify matching dict structures
    assert builder.state.bids[Decimal("45000.0")] == Decimal("1.5")
    assert builder.state.asks[Decimal("45030.0")] == Decimal("5.0")


@pytest.mark.unit
def test_order_book_incremental_updates(btc_symbol, initial_snapshot):
    """Verify that applying diff updates correctly inserts, updates, and deletes price levels."""
    builder = OrderBookBuilder(btc_symbol)
    builder.apply_snapshot(initial_snapshot)

    # 1. Apply contiguous update: U=101, u=102, pu=100
    diff_event = {
        "U": 101,
        "u": 102,
        "pu": 100,
        "E": 1700000000100,
        # Bids: insert 45005.0 (new best bid), update 44990.0 qty to 0.0 (delete)
        "b": [["45005.0", "0.5"], ["44990.0", "0.0"]],
        # Asks: update 45010.0 qty to 2.0, insert 45015.0
        "a": [["45010.0", "2.0"], ["45015.0", "1.5"]]
    }

    builder.apply_diff(diff_event)
    
    assert builder.state.last_update_id == 102
    assert builder.state.get_best_bid() == Decimal("45005.0")
    assert builder.state.bids[Decimal("45005.0")] == Decimal("0.5")
    assert Decimal("44990.0") not in builder.state.bids  # Deleted
    
    # Check asks
    assert builder.state.asks[Decimal("45010.0")] == Decimal("2.0")  # Updated
    assert builder.state.asks[Decimal("45015.0")] == Decimal("1.5")  # Inserted
    assert builder.state.get_best_ask() == Decimal("45010.0")


@pytest.mark.unit
def test_order_book_stale_event_rejection(btc_symbol, initial_snapshot):
    """Verify that stale events (with update ID <= last_update_id) are discarded without side effects."""
    builder = OrderBookBuilder(btc_symbol)
    builder.apply_snapshot(initial_snapshot)

    # Apply contiguous update to ID 105
    builder.apply_diff({
        "U": 101, "u": 105, "pu": 100,
        "b": [["45000.0", "9.9"]], "a": []
    })
    assert builder.state.bids[Decimal("45000.0")] == Decimal("9.9")
    assert builder.state.last_update_id == 105

    # Apply stale update: u = 104 <= 105
    builder.apply_diff({
        "U": 101, "u": 104, "pu": 100,
        "b": [["45000.0", "1.1"]], "a": []
    })
    
    # Bids should NOT be updated to 1.1 because update is stale
    assert builder.state.bids[Decimal("45000.0")] == Decimal("9.9")
    assert builder.state.last_update_id == 105


@pytest.mark.unit
def test_order_book_sequence_gap_detection(btc_symbol, initial_snapshot):
    """Verify that a sequence gap (first update ID > last_known_id + 1) raises SequenceGapError."""
    builder = OrderBookBuilder(btc_symbol)
    builder.apply_snapshot(initial_snapshot)

    # Gap: last_known = 100, first update ID in diff is 105
    diff_event = {
        "U": 105,
        "u": 110,
        "pu": 104,
        "b": [["45000.0", "2.0"]],
        "a": []
    }

    with pytest.raises(SequenceGapError, match="Sequence gap detected"):
        builder.apply_diff(diff_event)


@pytest.mark.unit
def test_order_book_crossed_book_prevention(btc_symbol, initial_snapshot):
    """Verify that applying an update that crosses the bids/asks raises ValueError."""
    builder = OrderBookBuilder(btc_symbol)
    builder.apply_snapshot(initial_snapshot)

    # Best ask is 45010.0. Insert a bid at 45015.0 -> crosses
    diff_event = {
        "U": 101,
        "u": 102,
        "pu": 100,
        "b": [["45015.0", "1.0"]],
        "a": []
    }

    with pytest.raises(ValueError, match="Crossed order book detected"):
        builder.apply_diff(diff_event)


@pytest.mark.unit
def test_order_book_validation_price_and_quantity(btc_symbol, initial_snapshot):
    """Verify that negative quantities or prices raise ValueError."""
    builder = OrderBookBuilder(btc_symbol)
    builder.apply_snapshot(initial_snapshot)

    # Negative price
    with pytest.raises(ValueError, match="Invalid price"):
        builder.apply_diff({
            "U": 101, "u": 102, "pu": 100,
            "b": [["-100.0", "1.0"]], "a": []
        })

    # Negative quantity
    with pytest.raises(ValueError, match="Invalid quantity"):
        builder.apply_diff({
            "U": 101, "u": 102, "pu": 100,
            "b": [["45000.0", "-1.0"]], "a": []
        })


@pytest.mark.unit
def test_deterministic_replay(btc_symbol, initial_snapshot):
    """Verify that replaying identical events to two separate builders yields identical outputs."""
    builder_a = OrderBookBuilder(btc_symbol)
    builder_b = OrderBookBuilder(btc_symbol)

    builder_a.apply_snapshot(initial_snapshot)
    builder_b.apply_snapshot(initial_snapshot)

    diff_stream = [
        {"U": 101, "u": 102, "pu": 100, "b": [["45005.0", "1.0"]], "a": [["45015.0", "2.0"]]},
        {"U": 103, "u": 104, "pu": 102, "b": [["45000.0", "0.0"]], "a": [["45030.0", "0.0"]]},
        {"U": 105, "u": 106, "pu": 104, "b": [["44990.0", "1.2"]], "a": [["45020.0", "2.5"]]}
    ]

    for event in diff_stream:
        builder_a.apply_diff(event)
        builder_b.apply_diff(event)

    # Strict state equality
    assert builder_a.state.bids == builder_b.state.bids
    assert builder_a.state.asks == builder_b.state.asks
    assert builder_a.state.last_update_id == builder_b.state.last_update_id

    # Checksum equality
    assert builder_a.state.calculate_checksum() == builder_b.state.calculate_checksum()

    # Serialized output equality
    snap_a = builder_a.state.to_snapshot()
    snap_b = builder_b.state.to_snapshot()
    assert snap_a.to_dict() == snap_b.to_dict()


@pytest.mark.unit
def test_multi_symbol_isolation(btc_symbol, eth_symbol, initial_snapshot):
    """Verify that multiple builders for different symbols operate independently."""
    btc_builder = OrderBookBuilder(btc_symbol)
    eth_builder = OrderBookBuilder(eth_symbol)

    btc_builder.apply_snapshot(initial_snapshot)

    # Initialize eth with different snapshot values
    eth_snapshot = OrderBookSnapshot(
        symbol=eth_symbol,
        timestamp=ExchangeTimestamp(1700000000000),
        bids=[OrderBookLevel(Price(Decimal("3000.0"), eth_symbol), Quantity(Decimal("10.0"), "ETH"))],
        asks=[OrderBookLevel(Price(Decimal("3005.0"), eth_symbol), Quantity(Decimal("12.0"), "ETH"))],
        sequence_id=200
    )
    eth_builder.apply_snapshot(eth_snapshot)

    # Check isolation
    assert btc_builder.state.get_best_bid() == Decimal("45000.0")
    assert eth_builder.state.get_best_bid() == Decimal("3000.0")

    # Apply diff to btc
    btc_builder.apply_diff({
        "U": 101, "u": 102, "pu": 100,
        "b": [["45000.0", "99.9"]], "a": []
    })

    # Eth should not be affected
    assert eth_builder.state.get_best_bid() == Decimal("3000.0")
    assert eth_builder.state.last_update_id == 200
    assert btc_builder.state.bids[Decimal("45000.0")] == Decimal("99.9")
