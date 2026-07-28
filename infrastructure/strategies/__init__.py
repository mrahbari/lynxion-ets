"""
Strategy adapters package for cleaner imports across the system.
"""
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter
from infrastructure.strategies.adapters.trend_follow_strategy_adapter import TrendFollowStrategyAdapter
from infrastructure.strategies.adapters.mean_reversion_strategy_adapter import MeanReversionStrategyAdapter
from infrastructure.strategies.adapters.breakout_strategy_adapter import BreakoutStrategyAdapter

__all__ = [
    'BaseStrategyAdapter',
    'TrendFollowStrategyAdapter',
    'MeanReversionStrategyAdapter',
    'BreakoutStrategyAdapter'
]