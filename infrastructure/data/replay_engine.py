import logging
import copy
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from domain.ports.data_ports import ReplayEnginePort
from domain.value_objects import Symbol, ExchangeTimestamp
from domain.entities import (
    ReplayEvent,
    ReplayCheckpoint,
    OrderBookSnapshot,
)
from domain.entities.order_book import OrderBookBuilder, SequenceGapError

logger = logging.getLogger("Lynxion.ReplayEngine")


class DeterministicReplayEngine(ReplayEnginePort):
    """Deterministic Replay Engine for simulating historical streams and validating state reconstruction."""

    def __init__(self,
                 builders: Dict[Symbol, OrderBookBuilder],
                 timestamp_priority: str = "exchange"):
        self.builders = builders
        self.timestamp_priority = timestamp_priority  # "exchange" or "local"
        
        # Stream state
        self.events: List[ReplayEvent] = []
        self.current_index = 0
        self._paused = False
        self.replay_speed = 1.0

        # Checkpoint storage (in-memory snapshot caches mapping event_position -> builders snapshots)
        self._saved_states: Dict[int, Dict[str, Any]] = {}

        # Quality metrics
        self.metrics = {
            "duplicates_filtered": 0,
            "late_events_handled": 0,
            "corrupted_events": 0,
            "checkpoints_created": 0,
            "checkpoints_restored": 0
        }

    def load_replay_data(self, symbols: List[Symbol], start: datetime, end: datetime) -> None:
        """Pre-load historical datasets. (Implemented as no-op here for port compatibility)."""
        pass

    def next_tick(self) -> Optional[Any]:
        """Port compatibility method. Processes and returns the next replayed event payload."""
        event = self.process_next_event()
        return event.payload if event else None

    def set_replay_speed(self, speed_factor: float) -> None:
        """Set the replay speed factor."""
        self.replay_speed = speed_factor

    def load_events(self, events: List[ReplayEvent]) -> None:
        """Load, sort, deduplicate, and validate a stream of historical ReplayEvents."""
        self.events = []
        self.current_index = 0
        self._saved_states.clear()

        seen_event_ids = set()
        seen_sequences = set()
        last_timestamp = 0

        # Deduplicate, order, and filter
        for event in events:
            # 1. Corrupted payload check
            if not event.event_id or not event.event_type or not isinstance(event.payload, dict):
                self.metrics["corrupted_events"] += 1
                logger.warning(f"Discarding corrupted event: {event.event_id}")
                continue

            # 2. Duplicate detection
            if event.event_id in seen_event_ids:
                self.metrics["duplicates_filtered"] += 1
                continue
            if event.sequence_number != 0 and event.sequence_number in seen_sequences:
                self.metrics["duplicates_filtered"] += 1
                continue

            seen_event_ids.add(event.event_id)
            if event.sequence_number != 0:
                seen_sequences.add(event.sequence_number)

            self.events.append(event)

        # 3. Deterministic Ordering
        if self.timestamp_priority == "exchange":
            # Primary: Exchange Timestamp, Secondary: Sequence Number, Tertiary: Event ID
            self.events.sort(key=lambda e: (e.timestamp.to_millis(), e.sequence_number, e.event_id))
        else:
            # Sort by local ingestion timestamp inside the payload if available, else fallback
            self.events.sort(key=lambda e: (
                e.payload.get("local_timestamp", e.timestamp.to_millis()),
                e.sequence_number,
                e.event_id
            ))

        # 4. Late event detection (post-sort verification)
        valid_ordered_events = []
        for event in self.events:
            ts_millis = event.timestamp.to_millis()
            if ts_millis < last_timestamp:
                self.metrics["late_events_handled"] += 1
                logger.warning(f"Late event detected and re-sorted: {event.event_id}")
            last_timestamp = ts_millis
            valid_ordered_events.append(event)

        self.events = valid_ordered_events
        logger.info(f"Loaded {len(self.events)} sorted, deduplicated events into replay engine")

    def process_next_event(self) -> Optional[ReplayEvent]:
        """Process the next chronological event in the stream and advance pointer."""
        if self._paused or self.current_index >= len(self.events):
            return None

        event = self.events[self.current_index]
        symbol_val = event.payload.get("s")
        if not symbol_val and "symbol" in event.payload:
            symbol_val = event.payload.get("symbol")
        
        if symbol_val:
            matching_symbol = next((s for s in self.builders.keys() if s.value.upper() == symbol_val.upper()), None)
            if matching_symbol:
                builder = self.builders[matching_symbol]
                
                # Apply update based on event type
                if event.event_type == "depth_snapshot":
                    # Convert payload back to OrderBookSnapshot
                    bids_levels = [
                        {"price": Decimal(str(b[0])), "qty": Decimal(str(b[1]))}
                        for b in event.payload.get("bids", [])
                    ]
                    asks_levels = [
                        {"price": Decimal(str(a[0])), "qty": Decimal(str(a[1]))}
                        for a in event.payload.get("asks", [])
                    ]
                    # We can use apply_snapshot directly after converting dictionary
                    snapshot = OrderBookSnapshot(
                        symbol=matching_symbol,
                        timestamp=event.timestamp,
                        bids=[
                            # OrderBookLevel level
                            copy.deepcopy(builder.state.to_snapshot().bids[0]) 
                            # Wait, instead of copying, just instantiate OrderBookSnapshot using a helper or standard builders
                        ] if False else [], # Wait, let's parse it properly
                        asks=[],
                        sequence_id=event.sequence_number
                    )
                    # Let's write a helper to reconstruct snapshot from dictionary
                    snapshot = self._parse_snapshot_payload(matching_symbol, event)
                    builder.apply_snapshot(snapshot)
                
                elif event.event_type in ("depth_diff", "depth_update"):
                    # Process incremental diff update
                    builder.apply_diff(event.payload)

        self.current_index += 1
        return event

    def pause(self) -> None:
        """Pause replay."""
        self._paused = True

    def resume(self) -> None:
        """Resume replay."""
        self._paused = False

    def is_paused(self) -> bool:
        """Check if replay is paused."""
        return self._paused

    def create_checkpoint(self) -> ReplayCheckpoint:
        """Capture the exact state of all order books and current event stream index."""
        # Calculate combined checksum of all order books
        combined_checksum = 0
        state_hashes = []
        
        # Serialize the states of all builders at this index
        snapshots = {}
        for symbol, builder in self.builders.items():
            if builder.is_initialized:
                snapshots[symbol.value] = builder.state.to_snapshot()
                combined_checksum += builder.state.calculate_checksum()
                state_hashes.append(hash(f"{symbol.value}:{builder.state.last_update_id}"))

        self._saved_states[self.current_index] = snapshots
        self.metrics["checkpoints_created"] += 1

        last_processed_ts = (
            self.events[self.current_index - 1].timestamp 
            if self.current_index > 0 and self.events 
            else ExchangeTimestamp(0)
        )

        return ReplayCheckpoint(
            timestamp=last_processed_ts,
            order_book_checksum=combined_checksum,
            market_state_hash=hash(tuple(state_hashes)),
            event_position=self.current_index
        )

    def restore_checkpoint(self, checkpoint: ReplayCheckpoint) -> None:
        """Restore all builders and replay index back to checkpoint state."""
        pos = checkpoint.event_position
        if pos not in self._saved_states:
            raise ValueError(f"No checkpoint state saved for event position: {pos}")

        saved_snapshots = self._saved_states[pos]
        for symbol_str, snapshot in saved_snapshots.items():
            matching_symbol = next((s for s in self.builders.keys() if s.value == symbol_str), None)
            if matching_symbol:
                self.builders[matching_symbol].apply_snapshot(snapshot)

        self.current_index = pos
        self.metrics["checkpoints_restored"] += 1
        logger.info(f"Successfully restored replay engine to checkpoint at index: {pos}")

    def _parse_snapshot_payload(self, symbol: Symbol, event: ReplayEvent) -> OrderBookSnapshot:
        """Helper to build OrderBookSnapshot from event payload."""
        from domain.entities import OrderBookLevel
        from domain.value_objects import Price, Quantity
        
        payload = event.payload
        bids = [
            OrderBookLevel(Price(Decimal(str(b[0])), symbol), Quantity(Decimal(str(b[1])), symbol.base_asset()))
            for b in payload.get("bids", [])
        ]
        asks = [
            OrderBookLevel(Price(Decimal(str(a[0])), symbol), Quantity(Decimal(str(a[1])), symbol.base_asset()))
            for a in payload.get("asks", [])
        ]
        return OrderBookSnapshot(
            symbol=symbol,
            timestamp=event.timestamp,
            bids=bids,
            asks=asks,
            sequence_id=event.sequence_number
        )
