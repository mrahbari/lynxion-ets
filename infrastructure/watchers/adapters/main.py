from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Watchers Service"""
    logger.info("Starting Watchers Service...")
    logger.info(f"Timestamp: {datetime.now()}")

    # Initialize watchers service components
    from .registry import WatcherRegistry
    from .market_pulse import MarketPulseWatcher
    from .volatility import VolatilityWatcher
    from .trend_mtf import TrendMTFWatcher
    from .anomaly_ml import AnomalyMLWatcher
    from .orderflow_ws import OrderFlowWSWatcher
    from .liquidity import LiquidityWatcher
    from .funding_rate import FundingRateWatcher
    from .cmc_screener import CMCScreener
    from .historical_candle_watcher import HistoricalCandleWatcherAdapter

    # Create registry
    registry = WatcherRegistry()

    # Register watcher types
    registry.register_watcher_type("MarketPulse", MarketPulseWatcher)
    registry.register_watcher_type("Volatility", VolatilityWatcher)
    registry.register_watcher_type("TrendMTF", TrendMTFWatcher)
    registry.register_watcher_type("AnomalyML", AnomalyMLWatcher)
    registry.register_watcher_type("OrderFlowWS", OrderFlowWSWatcher)
    registry.register_watcher_type("Liquidity", LiquidityWatcher)
    registry.register_watcher_type("FundingRate", FundingRateWatcher)
    registry.register_watcher_type("CMCScreener", CMCScreener)
    registry.register_watcher_type("HistoricalCandle", HistoricalCandleWatcherAdapter)

    # Create specific watchers
    # Example: Create a BTCUSDT watcher for each type
    # btc_watchers = [
    #     "MarketPulse", "Volatility", "TrendMTF", "AnomalyML",
    #     "OrderFlowWS", "Liquidity", "FundingRate", "CMCScreener", "HistoricalCandle"
    # ]
    #
    # for watcher_type in btc_watchers:
    #     registry.create_watcher(f"BTCUSDT_{watcher_type}", watcher_type, "BTCUSDT")

    # Start all watchers
    # registry.start_all_watchers()

    logger.info("Watchers Service initialized successfully")
    logger.info("Service ready to monitor markets")


if __name__ == "__main__":
    main()