"""
Hybrid Data Provider that can switch between Mock and CSV providers based on configuration.
"""
from typing import List, Dict, Any, Optional
from domain.ports.data_ports import DataProviderPort
from domain.entities.trading_entities import MarketData
from domain.value_objects import Symbol
from infrastructure.data.data_adapters import MockDataProviderAdapter
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
from application.configs.configs import Configs


class HybridDataProviderAdapter(DataProviderPort):
    """
    A flexible data provider that can use either mock or real CSV data based on configuration.
    This allows for easy switching between development and production modes.
    """

    def __init__(self, use_mock: bool = None, csv_base_path: str = None):
        """
        Initialize the hybrid data provider.

        Args:
            use_mock: If True, use mock data; if False, use CSV data; if None, determine from environment
            csv_base_path: Path to CSV historical data files (defaults to './data/history/raw/1m' or env var)
        """
        # Determine base path - from parameter, configuration, or default
        if csv_base_path is None:
            csv_base_path = Configs.data.csv_data_path if Configs.data and hasattr(Configs.data, 'csv_data_path') else './data/history/raw/1m'

        # Determine whether to use mock based on configuration or parameter
        if use_mock is None:
            use_mock = Configs.infrastructure.use_mock_data if Configs.infrastructure and hasattr(Configs.infrastructure, 'use_mock_data') else False

        self.use_mock = use_mock
        self.csv_base_path = csv_base_path

        if self.use_mock:
            self.provider = MockDataProviderAdapter()
        else:
            self.provider = CSVHistoryLoaderAdapter(base_path=csv_base_path)
    
    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for a symbol."""
        return self.provider.get_current_price(symbol)
    
    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical data for a symbol."""
        return self.provider.get_historical_data(symbol, period, timeframe)
    
    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """Subscribe to real-time market data for a symbol."""
        return self.provider.subscribe_to_market_data(symbol, callback)
    
    def unsubscribe_from_market_data(self, subscription_id: str):
        """Unsubscribe from real-time market data."""
        return self.provider.unsubscribe_from_market_data(subscription_id)
    
    def switch_to_mock(self):
        """Switch to mock data provider."""
        self.use_mock = True
        self.provider = MockDataProviderAdapter()
    
    def switch_to_csv(self):
        """Switch to CSV data provider."""
        self.use_mock = False
        self.provider = CSVHistoryLoaderAdapter(base_path=self.csv_base_path)


def create_data_provider(use_mock: bool = None, csv_base_path: str = None) -> DataProviderPort:
    """
    Factory function to create the appropriate data provider based on configuration.

    Args:
        use_mock: Whether to use mock data; if None, checks environment variable
        csv_base_path: Path to CSV historical data files (defaults to env var or './data/history/raw/1m')

    Returns:
        Configured data provider instance
    """
    return HybridDataProviderAdapter(use_mock=use_mock, csv_base_path=csv_base_path)