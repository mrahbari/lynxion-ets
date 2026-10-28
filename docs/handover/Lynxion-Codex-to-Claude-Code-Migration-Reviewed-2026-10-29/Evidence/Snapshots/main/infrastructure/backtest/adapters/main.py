from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Backtester Service"""
    logger.info("Starting Backtester Service...")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Initialize backtester components
    from backtester.simulator import BacktestSimulator, BacktestDataProvider
    from backtester.walk_forward import WalkForwardAnalyzer
    
    # Create components
    backtester = BacktestSimulator({
        'initial_capital': 100000,
        'commission': 0.001,
        'slippage': 0.0005
    })
    
    data_provider = BacktestDataProvider()
    wfa = WalkForwardAnalyzer({
        'in_sample_size': 252,
        'out_of_sample_size': 63
    })
    
    logger.info("Backtester Service initialized successfully")
    logger.info("Service ready to run backtests and optimization")


if __name__ == "__main__":
    main()