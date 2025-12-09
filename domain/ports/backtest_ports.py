from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities.trading_entities import Signal, Order, Fill, Position
from domain.value_objects import Symbol, Money


class BacktestEnginePort(Protocol):
    """Port for backtesting engine operations"""
    
    @abstractmethod
    def run_backtest(self, 
                     symbol: Symbol, 
                     start_date: str, 
                     end_date: str, 
                     initial_capital: float) -> Dict[str, Any]:
        """Run a backtest for the given parameters"""
        pass
    
    @abstractmethod
    def get_backtest_results(self) -> Dict[str, Any]:
        """Get results from the last backtest"""
        pass


class HistoricalDataProviderPort(Protocol):
    """Port for providing historical market data"""
    
    @abstractmethod
    def get_historical_data(self, 
                           symbol: Symbol, 
                           start_date: str, 
                           end_date: str, 
                           timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical market data for backtesting"""
        pass


class BacktestMetricsPort(Protocol):
    """Port for calculating backtest performance metrics"""
    
    @abstractmethod
    def calculate_metrics(self, trades: List[Fill], initial_capital: float) -> Dict[str, Any]:
        """Calculate performance metrics from backtest results"""
        pass