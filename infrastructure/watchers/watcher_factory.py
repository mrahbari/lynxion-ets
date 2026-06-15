"""
Watcher Factory - Creates appropriate watcher instances based on configuration
"""
from enum import Enum
from typing import Dict, Any, Type
from domain.value_objects import Symbol
from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter
from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter as HistoricalCandleWatcher
from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher as ConsolidatedMarketPulseWatcher
from infrastructure.watchers.adapters.volatility import VolatilityWatcher
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
from infrastructure.watchers.adapters.orderflow_ws import OrderFlowWSWatcher
from infrastructure.watchers.adapters.cmc_screener import CMCScreener
from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
from infrastructure.watchers.adapters.liquidity import LiquidityWatcher
from infrastructure.watchers.adapters.tick import TickWatcherAdapter
from infrastructure.watchers.watcher_config import (
    get_historical_candle_config,
    get_market_pulse_config,
    get_volatility_config,
    get_trend_mtf_config,
    get_anomaly_ml_config,
    get_orderflow_ws_config,
    get_funding_rate_config,
    get_liquidity_config,
    get_tick_config
)


class WatcherType(Enum):
    HISTORICAL_CANDLE = "historical_candle"
    MARKET_PULSE = "market_pulse"
    VOLATILITY = "volatility"
    TREND_MTF = "trend_mtf"
    ANOMALY_ML = "anomaly_ml"
    ORDERFLOW_WS = "orderflow_ws"
    CMC_SCREEN = "cmc_screener"
    FUNDING_RATE = "funding_rate"
    LIQUIDITY = "liquidity"
    TICK = "tick"


class WatcherFactory:
    """
    Factory for creating watcher instances based on configuration.
    Allows for flexible selection of watcher implementations.
    """
    
    # Mapping of watcher types to their regular implementations
    REGULAR_WATCHERS: Dict[WatcherType, Type] = {
        WatcherType.HISTORICAL_CANDLE: HistoricalCandleWatcherAdapter,
        WatcherType.MARKET_PULSE: MarketPulseWatcher,
        WatcherType.VOLATILITY: VolatilityWatcher,
        WatcherType.TREND_MTF: TrendMTFWatcher,
        WatcherType.ANOMALY_ML: AnomalyMLWatcher,
        WatcherType.ORDERFLOW_WS: OrderFlowWSWatcher,
        WatcherType.CMC_SCREEN: CMCScreener,
        WatcherType.FUNDING_RATE: FundingRateWatcher,
        WatcherType.LIQUIDITY: LiquidityWatcher,
        WatcherType.TICK: TickWatcherAdapter,
    }
    
    # Mapping of watcher types to their consolidated implementations
    CONSOLIDATED_WATCHERS: Dict[WatcherType, Type] = {
        WatcherType.HISTORICAL_CANDLE: HistoricalCandleWatcher,  # Consolidated version
        WatcherType.MARKET_PULSE: ConsolidatedMarketPulseWatcher,  # Consolidated version
        WatcherType.VOLATILITY: VolatilityWatcher,  # Same implementation
        WatcherType.TREND_MTF: TrendMTFWatcher,  # Same implementation
        WatcherType.ANOMALY_ML: AnomalyMLWatcher,  # Same implementation
        WatcherType.ORDERFLOW_WS: OrderFlowWSWatcher,  # Same implementation
        WatcherType.CMC_SCREEN: CMCScreener,  # Same implementation
        WatcherType.FUNDING_RATE: FundingRateWatcher,  # Same implementation
        WatcherType.LIQUIDITY: LiquidityWatcher,  # Same implementation
        WatcherType.TICK: TickWatcherAdapter,  # Same implementation
    }

    @classmethod
    def create_watcher(cls, settings, watcher_type: WatcherType, name: str, symbol: str,
                      broker_service=None, target_broker=None, **kwargs) -> Any:
        """
        Create a watcher instance based on configuration.

        Args:
            settings: Injected settings object (E1.T4 — supplied by the caller; this
                factory no longer imports bootstrap.settings.loaders). Forwarded to
                the watcher constructors that need it (settings.watcher).
            watcher_type: Type of watcher to create
            name: Name of the watcher
            symbol: Trading symbol
            broker_service: Broker service instance
            target_broker: Target broker
            **kwargs: Additional arguments for watcher construction

        Returns:
            Configured watcher instance
        """
        # Check if consolidated version should be used
        _watcher_cfg = settings.watcher
        use_consolidated = getattr(_watcher_cfg, f'use_consolidated_{watcher_type.value.lower()}', False) if _watcher_cfg else False

        if use_consolidated:
            watcher_class = cls.CONSOLIDATED_WATCHERS[watcher_type]
        else:
            watcher_class = cls.REGULAR_WATCHERS[watcher_type]

        # Get standardized configuration for the watcher type
        config = cls._get_config_for_watcher_type(watcher_type, settings)

        # Handle special cases for watchers that have different constructor signatures
        if watcher_type == WatcherType.HISTORICAL_CANDLE:
            if use_consolidated:
                return watcher_class(settings, name, symbol,
                                   broker_service=broker_service,
                                   lookback=config.get('lookback'),
                                   adaptive_sensitivity=config.get('adaptive_sensitivity', False))
            else:
                # For regular version, use original constructor
                return watcher_class(settings, name, symbol, broker_service=broker_service, **kwargs)
        elif watcher_type == WatcherType.MARKET_PULSE:
            if use_consolidated:
                return watcher_class(name, symbol,
                                   broker_service=broker_service,
                                   target_broker=target_broker,
                                   lookback=config.get('lookback'),
                                   adaptive_sensitivity=config.get('adaptive_sensitivity', False),
                                   watcher_config=_watcher_cfg)
            else:
                # For regular version, use original constructor
                return watcher_class(name, symbol, broker_service=broker_service,
                                   target_broker=target_broker, watcher_config=_watcher_cfg, **kwargs)
        elif watcher_type == WatcherType.CMC_SCREEN:
            # CMCScreener has its own constructor signature (no broker service needed)
            return watcher_class(settings, name, symbol, **kwargs)
        elif watcher_type == WatcherType.TICK:
            # TickWatcherAdapter has its own constructor signature (no target_broker parameter)
            return watcher_class(name, symbol, broker_service=broker_service, watcher_config=_watcher_cfg, **kwargs)
        else:
            # For other watchers, use standard constructor
            return watcher_class(name, symbol, broker_service=broker_service,
                               target_broker=target_broker, watcher_config=_watcher_cfg, **kwargs)

    @classmethod
    def _get_config_for_watcher_type(cls, watcher_type: WatcherType, settings) -> dict:
        """Get standardized configuration for a specific watcher type."""
        config_map = {
            WatcherType.HISTORICAL_CANDLE: get_historical_candle_config,
            WatcherType.MARKET_PULSE: get_market_pulse_config,
            WatcherType.VOLATILITY: get_volatility_config,
            WatcherType.TREND_MTF: get_trend_mtf_config,
            WatcherType.ANOMALY_ML: get_anomaly_ml_config,
            WatcherType.ORDERFLOW_WS: get_orderflow_ws_config,
            WatcherType.CMC_SCREEN: lambda _settings: {},  # CMCScreener has its own config
            WatcherType.FUNDING_RATE: get_funding_rate_config,
            WatcherType.LIQUIDITY: get_liquidity_config,
            WatcherType.TICK: get_tick_config,
        }

        config_func = config_map.get(watcher_type)
        if config_func:
            return config_func(settings)
        return {}

    @classmethod
    def get_available_watchers(cls) -> Dict[str, Type]:
        """Get all available watcher types with their classes."""
        return {watcher_type.value: watcher_class for watcher_type, watcher_class in cls.REGULAR_WATCHERS.items()}