"""Unit tests for the Deterministic Replay & Reconstruction Validation Layer (Milestone 2.5)."""

import pytest
from decimal import Decimal

from domain.value_objects import Symbol, ExchangeTimestamp
from domain.entities import ReplayEvent, ReplayCheckpoint, OrderBookSnapshot, OrderBookLevel
from domain.entities.order_book import OrderBookBuilder
from infrastructure.data.replay_engine import DeterministicReplayEngine


@pytest.fixture
def btc_symbol():
    return Symbol("BTC-USDT")


@pytest.fixture
def eth_symbol():
    return Symbol("ETH-USDT")


@pytest.fixture
def initial_snapshot(btc_symbol):
    from domain.value_objects import Price, Quantity
    return OrderBookSnapshot(
        symbol=btc_symbol,
        timestamp=ExchangeTimestamp(1700000000000),
        bids=[OrderBookLevel(Price(Decimal("45000.0"), btc_symbol), Quantity(Decimal("1.0"), "BTC"))],
        asks=[OrderBookLevel(Price(Decimal("45010.0"), btc_symbol), Quantity(Decimal("1.0"), "BTC"))],
        sequence_id=100
    )


@pytest.fixture
def mock_events(btc_symbol):
    # Out of order events to test sorting: T=1700000000200, T=1700000000100, T=1700000000300
    return [
        ReplayEvent(
            event_id="evt-2",
            timestamp=ExchangeTimestamp(1700000000200),
            event_type="depth_diff",
            payload={"s": "BTC-USDT", "U": 103, "u": 104, "pu": 102, "b": [["45002.0", "1.5"]], "a": []},
            sequence_number=104
        ),
        ReplayEvent(
            event_id="evt-1",
            timestamp=ExchangeTimestamp(1700000000100),
            event_type="depth_diff",
            payload={"s": "BTC-USDT", "U": 101, "u": 102, "pu": 100, "b": [["45001.0", "2.0"]], "a": []},
            sequence_number=102
        ),
        ReplayEvent(
            event_id="evt-3",
            timestamp=ExchangeTimestamp(1700000000300),
            event_type="depth_diff",
            payload={"s": "BTC-USDT", "U": 105, "u": 106, "pu": 104, "b": [], "a": [["45008.0", "0.5"]]},
            sequence_number=106
        )
    ]


@pytest.mark.unit
def test_replay_event_ordering(btc_symbol, mock_events):
    """Verify that ReplayEvents are sorted chronologically upon loading."""
    builder = OrderBookBuilder(btc_symbol)
    engine = DeterministicReplayEngine(builders={btc_symbol: builder})

    engine.load_events(mock_events)

    # Check chronological ordering: evt-1 (100100) -> evt-2 (100200) -> evt-3 (100300)
    assert len(engine.events) == 3
    assert engine.events[0].event_id == "evt-1"
    assert engine.events[1].event_id == "evt-2"
    assert engine.events[2].event_id == "evt-3"


@pytest.mark.unit
def test_replay_duplicate_filtering(btc_symbol):
    """Verify that duplicate events (identical event_id or sequence) are filtered out."""
    events = [
        ReplayEvent(
            event_id="evt-1",
            timestamp=ExchangeTimestamp(100),
            event_type="depth_diff",
            payload={"s": "BTC-USDT", "U": 101, "u": 102, "pu": 100},
            sequence_number=102
        ),
        # Duplicate event_id
        ReplayEvent(
            event_id="evt-1",
            timestamp=ExchangeTimestamp(200),
            event_type="depth_diff",
            payload={"s": "BTC-USDT", "U": 103, "u": 104, "pu": 102},
            sequence_number=104
        ),
        # Duplicate sequence number
        ReplayEvent(
            event_id="evt-2",
            timestamp=ExchangeTimestamp(300),
            event_type="depth_diff",
            payload={"s": "BTC-USDT", "U": 101, "u": 102, "pu": 100},
            sequence_number=102
        )
    ]

    builder = OrderBookBuilder(btc_symbol)
    engine = DeterministicReplayEngine(builders={btc_symbol: builder})

    engine.load_events(events)

    # Only the first unique event should remain
    assert len(engine.events) == 1
    assert engine.metrics["duplicates_filtered"] == 2


@pytest.mark.unit
def test_replay_corrupted_payload_handling(btc_symbol):
    """Verify that corrupted events are discarded and don't halt loading."""
    events = [
        # Missing event_id
        ReplayEvent(
            event_id="",
            timestamp=ExchangeTimestamp(100),
            event_type="depth_diff",
            payload={"s": "BTC-USDT"},
            sequence_number=102
        ),
        # Payload is not a dictionary
        ReplayEvent(
            event_id="evt-good",
            timestamp=ExchangeTimestamp(200),
            event_type="depth_diff",
            payload=None, # type: ignore
            sequence_number=104
        )
    ]

    builder = OrderBookBuilder(btc_symbol)
    engine = DeterministicReplayEngine(builders={btc_symbol: builder})

    engine.load_events(events)
    assert len(engine.events) == 0
    assert engine.metrics["corrupted_events"] == 2


@pytest.mark.unit
def test_deterministic_execution_runs(btc_symbol, initial_snapshot, mock_events):
    """Verify that repeated runs of the same event stream produce identical states and checksums."""
    
    # Run A
    builder_a = OrderBookBuilder(btc_symbol)
    builder_a.apply_snapshot(initial_snapshot)
    engine_a = DeterministicReplayEngine(builders={btc_symbol: builder_a})
    engine_a.load_events(mock_events)
    while engine_a.current_index < len(engine_a.events):
        engine_a.process_next_event()

    # Run B
    builder_b = OrderBookBuilder(btc_symbol)
    builder_b.apply_snapshot(initial_snapshot)
    engine_b = DeterministicReplayEngine(builders={btc_symbol: builder_b})
    engine_b.load_events(mock_events)
    while engine_b.current_index < len(engine_b.events):
        engine_b.process_next_event()

    # Verification
    assert builder_a.state.bids == builder_b.state.bids
    assert builder_a.state.asks == builder_b.state.asks
    assert builder_a.state.get_best_bid() == builder_b.state.get_best_bid()
    assert builder_a.state.get_best_ask() == builder_b.state.get_best_ask()
    assert builder_a.state.calculate_checksum() == builder_b.state.calculate_checksum()
    assert builder_a.state.to_snapshot().to_dict() == builder_b.state.to_snapshot().to_dict()


@pytest.mark.unit
def test_replay_checkpoint_and_restore(btc_symbol, initial_snapshot, mock_events):
    """Verify that checkpointing and restoring state recreates identical final outputs."""
    builder = OrderBookBuilder(btc_symbol)
    builder.apply_snapshot(initial_snapshot)
    engine = DeterministicReplayEngine(builders={btc_symbol: builder})
    engine.load_events(mock_events)

    # 1. Replay 2 events
    engine.process_next_event()
    engine.process_next_event()

    # Create checkpoint at index 2
    checkpoint = engine.create_checkpoint()
    assert checkpoint.event_position == 2

    # Save state before modification
    bids_checkpoint = dict(builder.state.bids)
    checksum_checkpoint = builder.state.calculate_checksum()

    # 2. Replay remaining events
    engine.process_next_event()
    assert engine.current_index == 3

    # State has changed
    assert builder.state.calculate_checksum() != checksum_checkpoint

    # 3. Restore checkpoint
    engine.restore_checkpoint(checkpoint)
    assert engine.current_index == 2
    assert builder.state.bids == bids_checkpoint
    assert builder.state.calculate_checksum() == checksum_checkpoint

    # 4. Resume to end
    engine.process_next_event()
    assert engine.current_index == 3


@pytest.mark.unit
def test_replay_pause_resume_and_speed(btc_symbol):
    """Verify pause/resume mechanics and replay speed factor settings."""
    builder = OrderBookBuilder(btc_symbol)
    engine = DeterministicReplayEngine(builders={btc_symbol: builder})
    
    engine.set_replay_speed(2.5)
    assert engine.replay_speed == 2.5

    assert not engine.is_paused()
    engine.pause()
    assert engine.is_paused()
    
    engine.resume()
    assert not engine.is_paused()


@pytest.mark.unit
def test_replay_multi_symbol_isolation(btc_symbol, eth_symbol, initial_snapshot):
    """Verify that events are routed to appropriate symbol builders during replay."""
    from domain.value_objects import Price, Quantity
    btc_builder = OrderBookBuilder(btc_symbol)
    eth_builder = OrderBookBuilder(eth_symbol)
    
    btc_builder.apply_snapshot(initial_snapshot)
    
    eth_snapshot = OrderBookSnapshot(
        symbol=eth_symbol,
        timestamp=ExchangeTimestamp(1700000000000),
        bids=[OrderBookLevel(Price(Decimal("3000.0"), eth_symbol), Quantity(Decimal("10.0"), "ETH"))],
        asks=[OrderBookLevel(Price(Decimal("3005.0"), eth_symbol), Quantity(Decimal("12.0"), "ETH"))],
        sequence_id=200
    )
    eth_builder.apply_snapshot(eth_snapshot)

    engine = DeterministicReplayEngine(builders={btc_symbol: btc_builder, eth_symbol: eth_builder})

    events = [
        # BTC event
        ReplayEvent(
            event_id="btc-1",
            timestamp=ExchangeTimestamp(1700000000100),
            event_type="depth_diff",
            payload={"s": "BTC-USDT", "U": 101, "u": 102, "pu": 100, "b": [["45005.0", "5.0"]], "a": []},
            sequence_number=102
        ),
        # ETH event
        ReplayEvent(
            event_id="eth-1",
            timestamp=ExchangeTimestamp(1700000000200),
            event_type="depth_diff",
            payload={"s": "ETH-USDT", "U": 201, "u": 202, "pu": 200, "b": [["3002.0", "8.0"]], "a": []},
            sequence_number=202
        )
    ]

    engine.load_events(events)
    
    # Process BTC
    engine.process_next_event()
    assert btc_builder.state.get_best_bid() == Decimal("45005.0")
    assert eth_builder.state.get_best_bid() == Decimal("3000.0")  # Eth unaffected

    # Process ETH
    engine.process_next_event()
    assert eth_builder.state.get_best_bid() == Decimal("3002.0")
    assert btc_builder.state.get_best_bid() == Decimal("45005.0")
