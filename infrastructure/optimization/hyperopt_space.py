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
            # Return specific space based on strategy name
            if strategy_name == "CryptoLiquidity":
                return cls._get_crypto_liquidity_space()
            elif strategy_name == "CryptoMTFTrend":
                return cls._get_crypto_mtf_trend_space()
            elif strategy_name == "CryptoVWAPReversal":
                return cls._get_crypto_vwap_reversal_space()
            elif strategy_name == "CryptoOIFootprint":
                return cls._get_crypto_oi_footprint_space()
            elif strategy_name == "CryptoSweepScalper":
                return cls._get_crypto_sweep_scalper_space()
            else:
                # Fallback to generic space if strategy not found or doesn't support optimization
                return cls._get_generic_space()

    @classmethod
    def _get_crypto_liquidity_space(cls) -> Dict[str, Any]:
        """Get parameter space for CryptoLiquidity strategy."""
        return {
            "min_oi_trend": hp.uniform("min_oi_trend", 0.01, 0.10),
            "max_funding_bias": hp.uniform("max_funding_bias", 0.001, 0.01),
            "cvd_divergence_strength": hp.uniform("cvd_divergence_strength", 1.0, 6.0)
        }

    @classmethod
    def _get_crypto_mtf_trend_space(cls) -> Dict[str, Any]:
        """Get parameter space for CryptoMTFTrend strategy."""
        return {
            "trend_period": hp.choice("trend_period", [30, 50, 80]),
        }

    @classmethod
    def _get_crypto_vwap_reversal_space(cls) -> Dict[str, Any]:
        """Get parameter space for CryptoVWAPReversal strategy."""
        return {
            "lookback": hp.quniform("lookback", 100, 400, 10),
            "std_mult": hp.uniform("std_mult", 1.0, 4.0),
        }

    @classmethod
    def _get_crypto_oi_footprint_space(cls) -> Dict[str, Any]:
        """Get parameter space for CryptoOIFootprint strategy."""
        return {
            "oi_expansion": hp.uniform("oi_expansion", 0.02, 0.10),
            "delta_strength": hp.uniform("delta_strength", 2, 10),
        }

    @classmethod
    def _get_crypto_sweep_scalper_space(cls) -> Dict[str, Any]:
        """Get parameter space for CryptoSweepScalper strategy."""
        return {
            "lookback": hp.choice("lookback", [3, 4, 5]),
        }

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

        # Register all crypto strategies with the registry
        from infrastructure.strategies.adapters.liquidity_strategy_adapter import LiquidityStrategyAdapter
        from infrastructure.strategies.adapters.mtf_trend_strategy_adapter import MTFTrendStrategyAdapter
        from infrastructure.strategies.adapters.vwap_reversal_strategy_adapter import VWAPReversalStrategyAdapter
        from infrastructure.strategies.adapters.oi_footprint_strategy_adapter import OIFootprintStrategyAdapter
        from infrastructure.strategies.adapters.sweep_scalper_strategy_adapter import SweepScalperAdapter

        self.strategy_registry.register_strategy("CryptoLiquidity", LiquidityStrategyAdapter)
        self.strategy_registry.register_strategy("CryptoMTFTrend", MTFTrendStrategyAdapter)
        self.strategy_registry.register_strategy("CryptoVWAPReversal", VWAPReversalStrategyAdapter)
        self.strategy_registry.register_strategy("CryptoOIFootprint", OIFootprintStrategyAdapter)
        self.strategy_registry.register_strategy("CryptoSweepScalper", SweepScalperAdapter)

    def get_space(self, strategy_name: str) -> Dict[str, Any]:
        """Get parameter space for a given strategy via registry."""
        return self.strategy_registry.get_parameter_space(strategy_name)


# For backward compatibility, provide the default space
parameter_space = HyperoptParameterSpace()