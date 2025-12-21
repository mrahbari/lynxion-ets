from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from shared.types import Signal
from shared.logger import logger
from domain.value_objects import Symbol
from infrastructure.brokers.broker_manager import BrokerManager


class BaseWatcher(ABC):
    """Base class for all watchers"""

    def __init__(self, name: str, symbol: str, broker_service: BrokerManager = None, target_broker: str = None):
        self.name = name
        self.symbol = symbol
        self.is_running = False
        self.last_signal: Optional[Signal] = None
        # Add broker service and target broker
        self.broker_service = broker_service
        self.target_broker = target_broker or "bingx"  # Default to bingx if no target specified
        # Ensure target broker name is lowercase to match broker keys
        self.target_broker = self.target_broker.lower()

    def get_broker(self):
        """Get the appropriate broker for this watcher"""
        if self.broker_service and hasattr(self.broker_service, 'get_broker_by_name'):
            return self.broker_service.get_broker_by_name(self.target_broker)
        elif self.broker_service and hasattr(self.broker_service, 'get_broker'):
            # Fallback to instrument_type mapping if get_broker_by_name not available
            return self.broker_service.get_broker(self.target_broker)
        return None

    @abstractmethod
    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze market conditions and return a signal"""
        pass
    
    def start(self):
        """Start the watcher"""
        self.is_running = True
        # Only log if the watcher is enabled
        if getattr(self, 'enabled', True):  # Default to True if no 'enabled' attribute
            logger.info(f"Started watcher: {self.name} for symbol: {self.symbol}")

    def stop(self):
        """Stop the watcher"""
        self.is_running = False
        # Only log if the watcher is enabled
        if getattr(self, 'enabled', True):  # Default to True if no 'enabled' attribute
            logger.info(f"Stopped watcher: {self.name} for symbol: {self.symbol}")
        
    def update_data(self, data: Dict[str, Any]):
        """Update watcher with new market data"""
        pass
        
    def get_last_signal(self) -> Optional[Signal]:
        """Get the last generated signal"""
        return self.last_signal
        
    def calculate_score(self, data: Dict[str, Any]) -> float:
        """Calculate a numerical score for the signal (-1.0 to 1.0)"""
        # Default implementation - should be overridden by subclasses
        return 0.0
        
    def should_emit_signal(self, current_signal: Signal) -> bool:
        """Determine if a new signal should be emitted"""
        # Default: emit if the signal is different from the last one
        if not self.last_signal:
            return True
            
        # Don't emit if the same signal was generated recently
        return (current_signal.signal_type != self.last_signal.signal_type or 
                abs(current_signal.confidence - self.last_signal.confidence) > 0.1)