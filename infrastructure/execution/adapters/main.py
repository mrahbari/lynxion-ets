from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Execution Engine Service"""
    logger.info("Starting Execution Engine Service...")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Initialize execution engine components
    from execution_engine.executor import Executor
    from execution_engine.twap import TWAPExecution
    from execution_engine.vwap import VWAPExecution
    from execution_engine.smart_router import SmartOrderRouter
    from broker_gateway.order_router import OrderRouter
    from risk_governor.governor import RiskGovernor
    
    # Create components
    order_router = OrderRouter()
    risk_governor = RiskGovernor()
    
    executor = Executor(order_router, risk_governor, {
        'slippage_tolerance': 0.005,
        'timeout_seconds': 30
    })
    
    twap = TWAPExecution({
        'twap_window_minutes': 30,
        'twap_slices': 10
    })
    
    vwap = VWAPExecution({
        'vwap_lookback_minutes': 60,
        'vwap_update_frequency': 30
    })
    
    # Note: SmartOrderRouter needs broker_gateways to be passed
    # smart_router = SmartOrderRouter({}, {})  # Empty for now
    
    logger.info("Execution Engine Service initialized successfully")
    logger.info("Service ready to execute orders")


if __name__ == "__main__":
    main()