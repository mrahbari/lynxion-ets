from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from domain.value_objects import Symbol, ExchangeTimestamp


class ReplaySessionStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ReplayEvent:
    """Canonical representation of an event being replayed."""
    event_id: str
    timestamp: ExchangeTimestamp
    event_type: str  # e.g., "trade", "depth_diff", "depth_snapshot"
    payload: Dict[str, Any]
    sequence_number: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.to_millis(),
            "event_type": self.event_type,
            "payload": self.payload,
            "sequence_number": self.sequence_number
        }


@dataclass
class ReplaySession:
    """Manages the configuration and runtime state of a historical replay session."""
    session_id: str
    start_timestamp: ExchangeTimestamp
    end_timestamp: ExchangeTimestamp
    symbols: List[Symbol]
    source: str
    replay_speed: float = 1.0
    deterministic_seed: int = 42
    status: ReplaySessionStatus = ReplaySessionStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "start_timestamp": self.start_timestamp.to_millis(),
            "end_timestamp": self.end_timestamp.to_millis(),
            "symbols": [s.value for s in self.symbols],
            "source": self.source,
            "replay_speed": self.replay_speed,
            "deterministic_seed": self.deterministic_seed,
            "status": self.status.value
        }


@dataclass(frozen=True)
class ReplayCheckpoint:
    """Captures a snapshot of the engine state at a specific event position for restoration."""
    timestamp: ExchangeTimestamp
    order_book_checksum: int
    market_state_hash: int
    event_position: int  # The index/position in the event stream

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.to_millis(),
            "order_book_checksum": self.order_book_checksum,
            "market_state_hash": self.market_state_hash,
            "event_position": self.event_position
        }
