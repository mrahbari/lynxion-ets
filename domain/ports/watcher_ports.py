from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities import Signal
from domain.value_objects import Symbol


class WatcherPort(Protocol):
    """Port for market watchers that monitor market conditions and generate alerts/signals"""
    
    @abstractmethod
    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze market conditions for the given symbol and return a signal if applicable"""
        pass
    
    @abstractmethod
    def start(self):
        """Start the watcher"""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop the watcher"""
        pass
    
    @abstractmethod
    def update_data(self, data: Dict[str, Any]):
        """Update the watcher with new market data"""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Check if the watcher is currently running"""
        pass