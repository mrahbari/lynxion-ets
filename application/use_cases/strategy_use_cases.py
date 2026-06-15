"""
Use cases for strategy functionality in the enterprise hedge fund trading system.
"""
from typing import List, Optional, Dict, Any
from domain.entities import Signal, Position
from domain.value_objects import Symbol
from application.services.strategy_services import StrategyOrchestrationService


class ExecuteStrategyCycleUseCase:
    """Use case for executing a complete strategy cycle"""
    
    def __init__(self, strategy_orchestration_service: StrategyOrchestrationService):
        self.strategy_orchestration_service = strategy_orchestration_service
    
    def execute(self, symbol: Symbol, market_data: Dict[str, Any] = None) -> Optional[Signal]:
        """Execute the use case to run a complete strategy cycle"""
        return self.strategy_orchestration_service.execute_strategy_cycle(symbol, market_data)


class SelectBestStrategyUseCase:
    """Use case for selecting the best strategy based on market conditions"""
    
    def __init__(self, strategy_selection_service):
        self.strategy_selection_service = strategy_selection_service
    
    def execute(self, symbol: Symbol, market_data: Dict[str, Any] = None) -> str:
        """Execute the use case to select the best strategy"""
        strategy = self.strategy_selection_service.select_best_strategy(symbol, market_data)
        return strategy.get_strategy_name() if strategy else "None"


class GenerateSignalUseCase:
    """Use case for generating a signal using optimal strategy"""
    
    def __init__(self, strategy_selection_service):
        self.strategy_selection_service = strategy_selection_service
    
    def execute(self, symbol: Symbol, market_data: Dict[str, Any] = None) -> Optional[Signal]:
        """Execute the use case to generate a signal with the optimal strategy"""
        return self.strategy_selection_service.generate_signal_with_optimal_strategy(symbol, market_data)


class GetStrategyPerformanceUseCase:
    """Use case for getting strategy performance metrics"""
    
    def __init__(self, strategy_orchestration_service: StrategyOrchestrationService):
        self.strategy_orchestration_service = strategy_orchestration_service
    
    def execute(self) -> Dict[str, List[Dict]]:
        """Execute the use case to get strategy performance"""
        return self.strategy_orchestration_service.get_strategy_performance()