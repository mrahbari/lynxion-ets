"""
Application service for data management in the enterprise hedge fund trading system.
"""
from typing import List, Optional, Dict, Any
from domain.entities import MarketData
from domain.value_objects import Symbol
from domain.ports.data_ports import DataProviderPort, DataCachePort, DataAggregatorPort
from shared.logger import logger


class DataRetrievalService:
    """Application service for retrieving market data"""
    
    def __init__(self,
                 data_provider_port: DataProviderPort,
                 data_cache_port: DataCachePort):
        self.data_provider = data_provider_port
        self.data_cache = data_cache_port
    
    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for a symbol"""
        cache_key = f"price_{symbol.value}"
        
        # Try to get from cache first
        cached_price = self.data_cache.retrieve_data(cache_key)
        if cached_price is not None:
            return cached_price
        
        # Get from data provider
        price = self.data_provider.get_current_price(symbol)
        
        # Cache the result
        if price is not None:
            self.data_cache.store_data(cache_key, price, ttl=30)  # 30 seconds TTL
        
        logger.info(f"Retrieved price for {symbol.value}: {price}")
        return price
    
    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical data for a symbol"""
        cache_key = f"historical_{symbol.value}_{period}_{timeframe}"
        
        # Try to get from cache first
        cached_data = self.data_cache.retrieve_data(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Get from data provider
        data = self.data_provider.get_historical_data(symbol, period, timeframe)
        
        # Cache the result
        if data:
            self.data_cache.store_data(cache_key, data, ttl=300)  # 5 minutes TTL
        
        logger.info(f"Retrieved {len(data)} historical data points for {symbol.value}")
        return data
    
    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """Subscribe to real-time market data"""
        logger.info(f"Subscribing to market data for {symbol.value}")
        return self.data_provider.subscribe_to_market_data(symbol, callback)
    
    def unsubscribe_from_market_data(self, subscription_id: str):
        """Unsubscribe from real-time market data"""
        logger.info(f"Unsubscribing from market data: {subscription_id}")
        self.data_provider.unsubscribe_from_market_data(subscription_id)


class DataAggregationService:
    """Service for aggregating data from multiple sources"""
    
    def __init__(self, 
                 data_aggregator_port: DataAggregatorPort,
                 data_cache_port: DataCachePort):
        self.data_aggregator = data_aggregator_port
        self.data_cache = data_cache_port
    
    def get_best_price_across_sources(self, symbol: Symbol) -> Optional[float]:
        """Get the best available price across all data sources"""
        cache_key = f"best_price_{symbol.value}"
        
        # Try to get from cache first
        cached_price = self.data_cache.retrieve_data(cache_key)
        if cached_price is not None:
            return cached_price
        
        # Aggregate data from all sources
        aggregated_data = self.data_aggregator.aggregate_data([], [symbol])
        
        best_price = None
        if symbol in aggregated_data and 'best_price' in aggregated_data[symbol]:
            best_price = aggregated_data[symbol]['best_price']
        
        # Cache the result
        if best_price is not None:
            self.data_cache.store_data(cache_key, best_price, ttl=10)  # 10 seconds TTL
        
        logger.info(f"Best price across sources for {symbol.value}: {best_price}")
        return best_price
    
    def get_price_spread(self, symbol: Symbol) -> Dict[str, float]:
        """Get the price spread across all data sources"""
        aggregated_data = self.data_aggregator.aggregate_data([], [symbol])
        
        if symbol not in aggregated_data:
            return {}
        
        symbol_data = aggregated_data[symbol]
        prices = [price for source, price in symbol_data.items() if isinstance(price, (int, float))]
        
        if not prices:
            return {}
        
        return {
            'min_price': min(prices),
            'max_price': max(prices),
            'spread': max(prices) - min(prices),
            'spread_percentage': ((max(prices) - min(prices)) / min(prices)) * 100 if min(prices) > 0 else 0,
            'average_price': sum(prices) / len(prices)
        }


class DataQualityService:
    """Service for ensuring data quality and handling data issues"""
    
    def __init__(self, data_service: DataRetrievalService):
        self.data_service = data_service
        self.data_quality_metrics = {}
    
    def validate_data_quality(self, symbol: Symbol) -> Dict[str, bool]:
        """Validate the quality of data for a symbol"""
        # Check if we can get a current price
        price = self.data_service.get_current_price(symbol)
        
        # In a real implementation, this would check various quality metrics
        # like latency, consistency, availability, etc.
        quality_metrics = {
            'data_available': price is not None,
            'data_reasonable': 0.01 < price < 1000000 if price is not None else False,  # Check if price is in reasonable range
            'freshness': True  # Placeholder
        }
        
        # Store quality metrics
        self.data_quality_metrics[symbol.value] = quality_metrics
        
        return quality_metrics
    
    def get_alternative_data_source(self, symbol: Symbol) -> Optional[str]:
        """Get an alternative data source if primary is unavailable"""
        # In a real implementation, this would identify backup data sources
        quality = self.validate_data_quality(symbol)
        
        if not quality['data_available']:
            # Return a fallback source
            return "fallback_data_source"
        
        return None


class DataSubscriptionService:
    """Service for managing data subscriptions"""
    
    def __init__(self, data_service: DataRetrievalService):
        self.data_service = data_service
        self.active_subscriptions = {}
    
    def subscribe_to_symbols(self, symbols: List[Symbol], callback) -> Dict[Symbol, str]:
        """Subscribe to multiple symbols"""
        subscriptions = {}
        
        for symbol in symbols:
            subscription_id = self.data_service.subscribe_to_market_data(symbol, callback)
            subscriptions[symbol] = subscription_id
            self.active_subscriptions[subscription_id] = symbol
        
        logger.info(f"Subscribed to {len(symbols)} symbols")
        return subscriptions
    
    def unsubscribe_from_all(self):
        """Unsubscribe from all symbols"""
        for subscription_id in list(self.active_subscriptions.keys()):
            self.data_service.unsubscribe_from_market_data(subscription_id)
            if subscription_id in self.active_subscriptions:
                del self.active_subscriptions[subscription_id]
        
        logger.info("Unsubscribed from all symbols")
    
    def get_subscription_status(self) -> Dict[str, Symbol]:
        """Get the status of all active subscriptions"""
        return self.active_subscriptions.copy()