from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Engines Service"""
    logger.info("Starting Engines Service...")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Initialize engines service components
    from engines_service.registry import EngineRegistry
    from engines_service.engines.trend_engine import TrendEngine
    from engines_service.engines.volatility_engine import VolatilityEngine
    from engines_service.engines.liquidity_engine import LiquidityEngine
    from engines_service.engines.orderflow_engine import OrderFlowEngine
    from engines_service.engines.regime_engine import RegimeEngine
    from engines_service.engines.correlation_engine import CorrelationEngine
    from engines_service.engines.ml_weight_engine import MLWeightEngine
    
    # Create registry
    registry = EngineRegistry()
    
    # Register engine types
    registry.register_engine_type("Trend", TrendEngine)
    registry.register_engine_type("Volatility", VolatilityEngine)
    registry.register_engine_type("Liquidity", LiquidityEngine)
    registry.register_engine_type("OrderFlow", OrderFlowEngine)
    registry.register_engine_type("Regime", RegimeEngine)
    registry.register_engine_type("Correlation", CorrelationEngine)
    registry.register_engine_type("MLWeight", MLWeightEngine)
    
    # Create specific engines
    # Example: Create several engines
    # registry.create_engine("TrendEngine", "Trend")
    # registry.create_engine("VolatilityEngine", "Volatility")
    # registry.create_engine("LiquidityEngine", "Liquidity")
    # registry.create_engine("OrderFlowEngine", "OrderFlow")
    # registry.create_engine("RegimeEngine", "Regime")
    # registry.create_engine("CorrelationEngine", "Correlation")
    # registry.create_engine("MLWeightEngine", "MLWeight")
    
    # Start all engines
    # registry.start_all_engines()
    
    logger.info("Engines Service initialized successfully")
    logger.info("Service ready to process signals")


if __name__ == "__main__":
    main()