from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Strategy Orchestrator Service"""
    logger.info("Starting Strategy Orchestrator Service...")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Initialize strategy orchestrator components
    from strategy_orchestrator.router import StrategyRouter
    from strategy_orchestrator.adaptive_selector import AdaptiveSelector
    from strategy_orchestrator.health_system import HealthSystem
    from strategy_orchestrator.strategies.scalper_alpha import ScalperAlphaStrategy
    from strategy_orchestrator.strategies.trend_follow import TrendFollowStrategy
    from strategy_orchestrator.strategies.reversion_x import ReversionXStrategy
    from strategy_orchestrator.strategies.base_strategy import BaseStrategy
    
    # Create components
    router = StrategyRouter()
    selector = AdaptiveSelector()
    health_system = HealthSystem()
    
    # Register strategies with router
    # router.register_strategy("ScalperAlpha", ScalperAlphaStrategy("ScalperAlpha", "BTCUSDT").generate_order)
    # router.register_strategy("TrendFollow", TrendFollowStrategy("TrendFollow", "BTCUSDT").generate_order)
    # router.register_strategy("ReversionX", ReversionXStrategy("ReversionX", "BTCUSDT").generate_order)
    
    logger.info("Strategy Orchestrator Service initialized successfully")
    logger.info("Service ready to route and manage strategies")


if __name__ == "__main__":
    main()