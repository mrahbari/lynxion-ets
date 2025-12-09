"""
Strategy adapters package to enable easier imports.
"""
from infrastructure.strategies.adapters.crypto_liquidity_strategy_adapter import CryptoLiquidityStrategyAdapter
from infrastructure.strategies.adapters.crypto_mtf_trend_strategy_adapter import CryptoMTFTrendStrategyAdapter
from infrastructure.strategies.adapters.crypto_vwap_reversal_strategy_adapter import CryptoVWAPReversalStrategyAdapter
from infrastructure.strategies.adapters.crypto_oi_footprint_strategy_adapter import CryptoOIFootprintStrategyAdapter
from infrastructure.strategies.adapters.crypto_sweep_scalper_adapter import CryptoSweepScalperAdapter

__all__ = [
    'CryptoLiquidityStrategyAdapter',
    'CryptoMTFTrendStrategyAdapter',
    'CryptoVWAPReversalStrategyAdapter',
    'CryptoOIFootprintStrategyAdapter',
    'CryptoSweepScalperAdapter'
]