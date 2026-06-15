from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities import Signal, Order, Fill, Position
from domain.value_objects import Symbol, Money


class BacktestEnginePort(Protocol):
    """Canonical backtest engine port (E3.T1 -- Option A: Retire & Redefine).

    Redefined around the live, golden-tested
    ``infrastructure.backtest.realistic_backtester.RealisticBacktester``: run a
    single-asset backtest over an OHLCV frame using an injected strategy function
    and return the performance-metrics dict.

    The previous ``(symbol, start_date, end_date, initial_capital)`` shape (plus a
    separate ``get_backtest_results``) described the legacy/dead engines
    (``BasicBacktestEngineAdapter`` and the unused ``*BacktestEngine`` classes) and
    has been retired from the canonical contract. Those modules are deprecated
    pending E8 removal.

    ``data`` is intentionally typed ``Any`` (an OHLCV pandas DataFrame at runtime)
    so the domain layer takes no hard pandas dependency.
    """

    @abstractmethod
    def run_backtest(self,
                     data: Any,
                     strategy_function,
                     strategy_params: Optional[Dict[str, Any]] = None,
                     initial_capital: Optional[float] = None,
                     strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """Run a backtest with the given strategy function; return the metrics dict."""
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