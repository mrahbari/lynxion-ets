"""
Use cases for watcher functionality in the enterprise hedge fund trading system.
"""
from typing import List, Optional
from domain.entities.trading_entities import Signal
from domain.value_objects import Symbol
from application.services.watcher_services import WatcherOrchestrationService


class AnalyzeMarketConditionsUseCase:
    """Use case for analyzing market conditions through watchers"""
    
    def __init__(self, watcher_orchestration_service: WatcherOrchestrationService):
        self.watcher_orchestration_service = watcher_orchestration_service
    
    def execute(self, symbol: Symbol) -> Optional[Signal]:
        """Execute the use case to analyze market conditions via watchers"""
        return self.watcher_orchestration_service.process_market_conditions(symbol)


class ManageWatchersUseCase:
    """Use case for managing watcher lifecycle"""
    
    def __init__(self, watcher_service):
        self.watcher_service = watcher_service
    
    def start_all_watchers(self):
        """Start all watchers"""
        self.watcher_service.start_all_watchers()
    
    def stop_all_watchers(self):
        """Stop all watchers"""
        self.watcher_service.stop_all_watchers()
    
    def get_active_watchers(self) -> List[str]:
        """Get list of currently active watchers"""
        return self.watcher_service.get_active_watchers()
    
    def update_watchers_with_data(self, data):
        """Update all watchers with new market data"""
        self.watcher_service.update_all_watchers(data)