from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Risk Governor Service"""
    logger.info("Starting Risk Governor Service...")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Initialize risk governor components
    from risk_governor.governor import RiskGovernor
    from risk_governor.exposure import ExposureManager
    from risk_governor.kelly import KellyCriterion
    from risk_governor.drawdown import DrawdownManager
    
    # Create components
    governor = RiskGovernor({
        'initial_capital': 100000,
        'max_portfolio_risk': 0.02,
        'max_position_risk': 0.01,
        'max_drawdown': 0.15
    })
    
    exposure_manager = ExposureManager({
        'initial_capital': 100000,
        'max_asset_exposure': 0.1,
        'max_sector_exposure': 0.3
    })
    
    kelly_criterion = KellyCriterion({
        'kelly_fraction': 0.5,
        'max_position_size': 0.1
    })
    
    drawdown_manager = DrawdownManager({
        'max_drawdown_limit': 0.15,
        'max_drawdown_rolling': 0.10
    })
    
    logger.info("Risk Governor Service initialized successfully")
    logger.info("Service ready to manage risk")


if __name__ == "__main__":
    main()