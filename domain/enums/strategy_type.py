"""
Strategy Type Enum for Enterprise Hedge Fund Trading System

This module defines the available strategy types for the trading system.
"""
from enum import Enum


class StrategyType(Enum):
    """Enumeration of available strategy types"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    MOMENTUM = "momentum"
    SCALPING = "scalping"
    BREAKOUT = "breakout"
    LIQUIDITY = "liquidity"
    MTF_TREND = "mtf_trend"
    OI_FOOTPRINT = "oi_footprint"
    SWEEP_SCALPER = "sweep_scalper"
    VWAP_REVERSAL = "vwap_reversal"