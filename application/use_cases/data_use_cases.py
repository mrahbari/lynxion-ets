"""
Use cases for data service functionality in the enterprise hedge fund trading system.
"""
from typing import List, Dict, Any
from domain.entities import MarketData
from domain.value_objects import Symbol
from application.services.data_services import DataRetrievalService


class GetCurrentPriceUseCase:
    """Use case for getting current price"""
    
    def __init__(self, data_retrieval_service: DataRetrievalService):
        self.data_retrieval_service = data_retrieval_service
    
    def execute(self, symbol: Symbol) -> float:
        """Execute the use case to get current price"""
        return self.data_retrieval_service.get_current_price(symbol)


class GetHistoricalDataUseCase:
    """Use case for getting historical data"""
    
    def __init__(self, data_retrieval_service: DataRetrievalService):
        self.data_retrieval_service = data_retrieval_service
    
    def execute(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict]:
        """Execute the use case to get historical data"""
        return self.data_retrieval_service.get_historical_data(symbol, period, timeframe)


class SubscribeToMarketDataUseCase:
    """Use case for subscribing to market data"""
    
    def __init__(self, data_retrieval_service: DataRetrievalService):
        self.data_retrieval_service = data_retrieval_service
    
    def execute(self, symbol: Symbol, callback) -> str:
        """Execute the use case to subscribe to market data"""
        return self.data_retrieval_service.subscribe_to_market_data(symbol, callback)


class GetBestPriceUseCase:
    """Use case for getting best price across sources"""
    
    def __init__(self, data_aggregation_service):
        self.data_aggregation_service = data_aggregation_service
    
    def execute(self, symbol: Symbol) -> float:
        """Execute the use case to get best price across sources"""
        return self.data_aggregation_service.get_best_price_across_sources(symbol)


class ValidateDataQualityUseCase:
    """Use case for validating data quality"""
    
    def __init__(self, data_quality_service):
        self.data_quality_service = data_quality_service
    
    def execute(self, symbol: Symbol) -> Dict[str, bool]:
        """Execute the use case to validate data quality"""
        return self.data_quality_service.validate_data_quality(symbol)