"""Optimization ports and interfaces following hexagonal architecture."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable

# E4.T3: tabular market data / returns are intentionally typed ``Any`` (an OHLCV
# pandas DataFrame / Series at runtime) so the domain layer takes no hard pandas
# dependency. Concrete pandas types live in the infrastructure adapters that
# implement these ports (e.g. ``infrastructure/optimization``).


class IOptimizableStrategy(ABC):
    """Interface for strategies that support hyperparameter optimization."""

    @abstractmethod
    def get_parameter_space(self) -> Dict[str, Any]:
        """Return hyperparameter space for optimization."""
        pass

    @abstractmethod
    def get_constraint_functions(self) -> List[Callable]:
        """Return constraint functions for the optimization."""
        pass

    @abstractmethod
    def get_optimization_objectives(self) -> List[str]:
        """Return list of optimization objectives."""
        pass


class IParameterSpace(ABC):
    """Interface for parameter spaces."""

    @abstractmethod
    def get_space(self, strategy_name: str) -> Dict[str, Any]:
        """Get parameter space for a given strategy."""
        pass


class IHyperoptObjective(ABC):
    """Interface for hyperopt objective functions."""

    @abstractmethod
    def create_objective_function(self,
                                data_dict,
                                risk_config,
                                optimization_objectives=None,
                                strategy_or_strategy_function=None):
        """Create objective function for hyperopt."""
        pass


class IStrategyRegistry(ABC):
    """Interface for strategy registry."""

    @abstractmethod
    def register_strategy(self, strategy_name: str, strategy_class):
        """Register a strategy with its optimization capabilities."""
        pass

    @abstractmethod
    def get_strategy(self, strategy_name: str):
        """Get a registered strategy."""
        pass

    @abstractmethod
    def get_parameter_space(self, strategy_name: str) -> Dict[str, Any]:
        """Get parameter space for a strategy."""
        pass


class IDataLoader(ABC):
    """Interface for data loading operations."""

    @abstractmethod
    def load_historical_data(self, symbol: str, timeframe: str, limit: int) -> Any:
        """Load historical market data."""
        pass

    @abstractmethod
    def cache_exists(self, symbol: str, timeframe: str) -> bool:
        """Check if cached data exists."""
        pass


class IMetricCalculator(ABC):
    """Interface for performance metric calculation."""

    @abstractmethod
    def calculate_sharpe_ratio(self, returns: Any) -> float:
        """Calculate Sharpe ratio."""
        pass

    @abstractmethod
    def calculate_max_drawdown(self, equity_curve: Any) -> float:
        """Calculate maximum drawdown."""
        pass

    @abstractmethod
    def calculate_win_rate(self, trades: Any) -> float:
        """Calculate win rate."""
        pass


class IOptimizationService(ABC):
    """Interface for optimization services."""

    @abstractmethod
    def optimize_strategy(self, strategy_name: str, data, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize strategy parameters."""
        pass

    @abstractmethod
    def get_optimized_parameters(self, strategy_name: str, symbol: str) -> Dict[str, Any]:
        """Get previously optimized parameters."""
        pass

    @abstractmethod
    def save_optimized_parameters(self, strategy_name: str, symbol: str, parameters: Dict[str, Any]) -> None:
        """Save optimized parameters."""
        pass