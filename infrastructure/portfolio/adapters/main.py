from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Portfolio Manager Service"""
    logger.info("Starting Portfolio Manager Service...")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Initialize portfolio manager components
    from portfolio_manager.allocator import PortfolioAllocator
    from portfolio_manager.risk_parity import RiskParity
    from portfolio_manager.volatility_target import VolatilityTarget
    
    # Create components
    allocator = PortfolioAllocator({
        'initial_capital': 100000,
        'risk_free_rate': 0.02,
        'max_position_size': 0.1
    })
    
    risk_parity = RiskParity({
        'target_risk_contribution': 1.0,
        'max_weight': 0.2
    })
    
    vol_target = VolatilityTarget({
        'target_volatility': 0.15,
        'initial_capital': 100000
    })
    
    logger.info("Portfolio Manager Service initialized successfully")
    logger.info("Service ready to manage portfolio allocation")


if __name__ == "__main__":
    main()