"""Hyperopt parameter space implementations following hexagonal architecture."""

from hyperopt import hp
from typing import Dict, Any
from shared.logger import EnhancedLogger
from domain.ports.optimization_ports import IParameterSpace, IStrategyRegistry


class StrategyRegistry(IStrategyRegistry):
    """Registry for strategies that can be optimized."""

    _registry = {}

    @classmethod
    def register_strategy(cls, strategy_name: str, strategy_class):
        """Register a strategy with its optimization capabilities."""
        cls._registry[strategy_name] = strategy_class

    @classmethod
    def get_strategy(cls, strategy_name: str):
        """Get a registered strategy."""
        return cls._registry.get(strategy_name)

    @classmethod
    def get_parameter_space(cls, strategy_name: str) -> Dict[str, Any]:
        """Get parameter space for a strategy."""
        strategy = cls.get_strategy(strategy_name)
        if strategy and hasattr(strategy, 'get_parameter_space'):
            return strategy.get_parameter_space()
        else:
            # Fallback to generic space if strategy not found or doesn't support optimization
            return cls._get_generic_space()

    @classmethod
    def _get_generic_space(cls) -> Dict[str, Any]:
        """Get a generic parameter space for unknown strategies."""
        return {
            "rsi_length": hp.quniform("rsi_length", 5, 30, 1),
            "rsi_overbought": hp.quniform("rsi_overbought", 60, 90, 1),
            "rsi_oversold": hp.quniform("rsi_oversold", 10, 40, 1),
            "ema_fast": hp.quniform("ema_fast", 5, 20, 1),
            "ema_slow": hp.quniform("ema_slow", 20, 80, 1),
            "atr_length": hp.quniform("atr_length", 7, 40, 1),
            "atr_multiplier": hp.uniform("atr_multiplier", 1.0, 5.0),
            "risk_per_trade": hp.uniform("risk_per_trade", 0.005, 0.03),
            "tp_ratio": hp.uniform("tp_ratio", 1.0, 5.0),
            "sl_ratio": hp.uniform("sl_ratio", 0.5, 3.0),
        }


class HyperoptParameterSpace(IParameterSpace):
    """Strategy-agnostic parameter space definitions for hyperopt optimization."""

    def __init__(self):
        self.logger = EnhancedLogger("HyperoptParameterSpace")
        self.strategy_registry = StrategyRegistry()

    def get_space(self, strategy_name: str) -> Dict[str, Any]:
        """Get parameter space for a given strategy via registry."""
        return self.strategy_registry.get_parameter_space(strategy_name)


# For backward compatibility, provide the default space
parameter_space = HyperoptParameterSpace()