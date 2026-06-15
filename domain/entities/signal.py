"""Canonical signal-related domain entities (watcher -> engine -> fusion -> strategy)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from domain.value_objects import Symbol, Percentage
from domain.enums.signal_type import SignalType  # canonical enum home; re-exported here


@dataclass
class Signal:
    """Domain entity representing a trading signal"""
    symbol: Symbol
    signal_type: SignalType
    confidence: Percentage  # 0.0 to 1.0
    score: float  # -1.0 to 1.0
    timestamp: datetime
    source_layer: Optional[str] = None  # Which layer generated this signal (watcher, engine, fusion, strategy)
    metadata: Optional[Dict[str, Any]] = None
    fused_score: Optional[float] = None
    fused_confidence: Optional[Percentage] = None

    def __post_init__(self):
        if not 0.0 <= float(self.confidence.value) <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if not -1.0 <= self.score <= 1.0:
            raise ValueError("Score must be between -1.0 and 1.0")


@dataclass
class MarketObservation:
    """Domain entity representing raw market observations from Watcher layer.
    Should NOT contain strategy information or trading decisions."""
    symbol: Symbol
    observation_type: str  # e.g., 'volatility_expansion', 'momentum_spike', 'liquidity_imbalance'
    observation_value: float  # raw value of the observation
    confidence: Percentage  # 0.0 to 1.0
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not 0.0 <= float(self.confidence.value) <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class InterpretedSignal:
    """Domain entity representing interpreted signals from Engine layer.
    Contains direction and strength but no strategy selection."""
    symbol: Symbol
    signal_type: SignalType  # Only direction (BUY/SELL/NEUTRAL/HOLD)
    direction: float  # -1.0 to 1.0 (short to long)
    strength: float  # 0.0 to 1.0
    confidence: Percentage  # 0.0 to 1.0
    timestamp: datetime
    source_watcher: Optional[str] = None  # Which watcher generated the observation
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not 0.0 <= float(self.confidence.value) <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if not -1.0 <= self.direction <= 1.0:
            raise ValueError("Direction must be between -1.0 and 1.0")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("Strength must be between 0.0 and 1.0")


@dataclass
class FusedSignal:
    """Domain entity representing fused signals from Fusion layer.
    Contains dominant bias but no strategy selection."""
    symbol: Symbol
    dominant_bias: SignalType
    direction: float  # -1.0 to 1.0 (short to long)
    dominance_score: float  # 0.0 to 1.0
    regime_context: str  # e.g., 'trending', 'volatile', 'normal'
    confidence: Percentage  # 0.0 to 1.0
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not 0.0 <= float(self.confidence.value) <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if not 0.0 <= self.dominance_score <= 1.0:
            raise ValueError("Dominance score must be between 0.0 and 1.0")
        if not -1.0 <= self.direction <= 1.0:
            raise ValueError("Direction must be between -1.0 and 1.0")
