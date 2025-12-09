from datetime import datetime
from shared.logger import logger


def main():
    """Main entry point for the Data Service"""
    logger.info("Starting Data Service...")
    logger.info(f"Timestamp: {datetime.now()}")
    
    # Initialize data service components
    from data_service.downloader import DataDownloader
    from data_service.historical_loader import HistoricalDataLoader
    from data_service.websocket_router import WebSocketRouter
    from data_service.rest_client import RestClient
    
    # Create instances
    downloader = DataDownloader()
    historical_loader = HistoricalDataLoader()
    ws_router = WebSocketRouter()
    rest_client = RestClient("api_key", "api_secret")  # Placeholder credentials
    
    logger.info("Data Service initialized successfully")
    
    # This would start data collection services
    # ws_router.start_all_streams(["btcusdt@ticker", "ethusdt@ticker"])  # Example streams
    
    logger.info("Data Service running...")


if __name__ == "__main__":
    main()