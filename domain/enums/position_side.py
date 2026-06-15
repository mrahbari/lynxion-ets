"""Canonical ``PositionSide`` enum (single home for the trading system)."""
from enum import Enum


class PositionSide(Enum):
    """Side/direction of a position."""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"
