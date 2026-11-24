"""
Strategy Type Enum for Enterprise Hedge Fund Trading System

This module defines the available strategy types for the trading system.
"""
from enum import Enum


class StrategyType(Enum):
    """Enumeration of available strategy types"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    SCALPING = "scalping"
    BREAKOUT = "breakout"
    LIQUIDITY = "liquidity"
    OI_FOOTPRINT = "oi_footprint"
    VWAP_REVERSAL = "vwap_reversal"