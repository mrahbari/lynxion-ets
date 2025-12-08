"""
Use cases for backtesting functionality in the enterprise hedge fund trading system.
"""
from typing import List, Dict, Any
from domain.value_objects import Symbol, Money
from application.services.backtest_services import BacktestExecutionService


class RunBacktestUseCase:
    """Use case for running a backtest"""
    
    def __init__(self, backtest_service: BacktestExecutionService):
        self.backtest_service = backtest_service
    
    def execute(self, 
                symbol: Symbol,
                start_date: str,
                end_date: str,
                initial_capital: float,
                strategy_name: str = "DefaultStrategy") -> Dict[str, Any]:
        """Execute the use case to run a backtest"""
        return self.backtest_service.run_strategy_backtest(
            symbol, start_date, end_date, initial_capital, strategy_name
        )


class CompareStrategiesUseCase:
    """Use case for comparing strategy performance"""
    
    def __init__(self, backtest_service: BacktestExecutionService):
        self.backtest_service = backtest_service
    
    def execute(self, 
                symbol: Symbol,
                start_date: str,
                end_date: str,
                initial_capital: float,
                strategies: List[str]) -> Dict[str, Any]:
        """Execute the use case to compare strategies"""
        return self.backtest_service.compare_strategies(
            symbol, start_date, end_date, initial_capital, strategies
        )


class ValidateStrategyUseCase:
    """Use case for validating strategy performance"""
    
    def __init__(self, backtest_service: BacktestExecutionService):
        self.backtest_service = backtest_service
    
    def execute(self, 
                results: Dict[str, Any], 
                min_return_threshold: float = 0.0,
                max_drawdown_threshold: float = 0.1) -> bool:
        """Execute the use case to validate strategy performance"""
        return self.backtest_service.validate_strategy_performance(
            results, min_return_threshold, max_drawdown_threshold
        )


class OptimizeStrategyUseCase:
    """Use case for optimizing strategy parameters"""
    
    def __init__(self, backtest_optimization_service):
        self.backtest_optimization_service = backtest_optimization_service
    
    def execute(self,
                symbol: Symbol,
                start_date: str,
                end_date: str,
                initial_capital: float,
                strategy_name: str,
                parameter_ranges: Dict[str, tuple]) -> Dict[str, Any]:
        """Execute the use case to optimize strategy parameters"""
        return self.backtest_optimization_service.optimize_strategy_parameters(
            symbol, start_date, end_date, initial_capital, strategy_name, parameter_ranges
        )


class AnalyzeBacktestResultsUseCase:
    """Use case for analyzing backtest results"""
    
    def __init__(self, backtest_analytics_service):
        self.backtest_analytics_service = backtest_analytics_service
    
    def execute(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the use case to analyze backtest results"""
        return self.backtest_analytics_service.analyze_backtest_results(results)