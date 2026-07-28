"""Domain Enum for Watcher Types and Resolution Utilities (E2.T3)."""
from enum import Enum
from typing import Optional


class WatcherType(str, Enum):
    MARKET_PULSE = "MarketPulseWatcher"
    TREND_MTF = "TrendMTFWatcher"
    VOLATILITY = "VolatilityWatcher"
    ANOMALY_ML = "AnomalyMLWatcher"
    ORDERFLOW_WS = "OrderFlowWSWatcher"
    CMC_SCREENER = "CMCScreenerWatcher"
    FUNDING_RATE = "FundingRateWatcher"
    LIQUIDITY = "LiquidityWatcher"
    HISTORICAL_CANDLE = "HistoricalCandleWatcher"
    TICK_WATCHER = "TickWatcherAdapter"
    DEFAULT = "DefaultWatcher"

    @classmethod
    def resolve_from_strategy_or_metadata(
        cls,
        watcher_name: Optional[str] = None,
        strategy_name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Clean, centralized resolution of Watcher titles for notifications and reporting.
        Prevents ad-hoc string comparisons across telegram alert & broker services.
        """
        # 1. Direct watcher_name check if valid
        if watcher_name and watcher_name not in ("N/A", "default", "DefaultWatcher", "None"):
            return watcher_name

        # 2. Check metadata dictionary if available
        if metadata:
            w_meta = metadata.get("watcher_name") or metadata.get("primary_watcher") or metadata.get("source_watcher")
            if w_meta and w_meta not in ("N/A", "default", "DefaultWatcher", "None"):
                return str(w_meta)

        # 3. Fallback resolution via strategy_name using enum mapping
        if strategy_name and strategy_name not in ("N/A", "default", "None", ""):
            strat_lower = strategy_name.lower().replace("_", "").replace("-", "")
            if "mtf" in strat_lower or "trend" in strat_lower or "wfo" in strat_lower:
                return cls.TREND_MTF.value
            elif "vwap" in strat_lower or "pulse" in strat_lower or "reversion" in strat_lower or "mean" in strat_lower:
                return cls.MARKET_PULSE.value
            elif "breakout" in strat_lower or "volatility" in strat_lower or "donchian" in strat_lower:
                return cls.VOLATILITY.value
            elif "liquidity" in strat_lower or "sweep" in strat_lower or "ngls" in strat_lower:
                return cls.LIQUIDITY.value
            elif "orderflow" in strat_lower or "footprint" in strat_lower or "oi" in strat_lower:
                return cls.ORDERFLOW_WS.value
            elif "anomaly" in strat_lower or "ml" in strat_lower:
                return cls.ANOMALY_ML.value
            elif "tick" in strat_lower:
                return cls.TICK_WATCHER.value

        return cls.DEFAULT.value
