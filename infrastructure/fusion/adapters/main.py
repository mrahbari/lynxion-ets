from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Fusion Service"""
    logger.info("Starting Fusion Service...")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Initialize fusion service components
    from fusion_service.fusion_v3 import FusionV3
    
    # Create fusion engine
    fusion_engine = FusionV3(
        max_signals_history=100,
        confidence_threshold=0.3,
        regime_aware=True,
        ml_weighted=True
    )
    
    logger.info("Fusion Service initialized successfully")
    logger.info("Service ready to fuse signals")


if __name__ == "__main__":
    main()