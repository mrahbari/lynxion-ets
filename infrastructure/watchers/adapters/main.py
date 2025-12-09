from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Watchers Service"""
    logger.info("Starting Watchers Service...")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Initialize watchers service components
    from watchers_service.registry import WatcherRegistry
    from watchers_service.watchers.market_pulse import MarketPulseWatcher
    from watchers_service.watchers.volatility import VolatilityWatcher
    from watchers_service.watchers.trend_mtf import TrendMTFWatcher
    from watchers_service.watchers.anomaly_ml import AnomalyMLWatcher
    from watchers_service.watchers.orderflow_ws import OrderFlowWSWatcher
    from watchers_service.watchers.liquidity import LiquidityWatcher
    from watchers_service.watchers.funding_rate import FundingRateWatcher
    from watchers_service.watchers.cmc_screener import CMCScreenerWatcher
    
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
    registry.register_watcher_type("CMCScreener", CMCScreenerWatcher)
    
    # Create specific watchers
    # Example: Create a BTCUSDT watcher for each type
    # btc_watchers = [
    #     "MarketPulse", "Volatility", "TrendMTF", "AnomalyML", 
    #     "OrderFlowWS", "Liquidity", "FundingRate", "CMCScreener"
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