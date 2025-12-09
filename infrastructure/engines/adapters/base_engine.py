from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from shared.types import Signal
from shared.logger import logger


class BaseEngine(ABC):
    """Base class for all engines"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_running = False
        self.signal_history: List[Signal] = []
        self.max_history = 1000  # Maximum number of signals to keep in history
        
    @abstractmethod
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal and return an enhanced/corrected signal"""
        pass
    
    def start(self):
        """Start the engine"""
        self.is_running = True
        logger.info(f"Started engine: {self.name}")
        
    def stop(self):
        """Stop the engine"""
        self.is_running = False
        logger.info(f"Stopped engine: {self.name}")
        
    def update_data(self, data: Dict[str, Any]):
        """Update engine with new market data"""
        pass
        
    def add_signal_to_history(self, signal: Signal):
        """Add a signal to the history"""
        self.signal_history.append(signal)
        
        # Keep history size within limits
        if len(self.signal_history) > self.max_history:
            self.signal_history.pop(0)
            
    def get_recent_signals(self, count: int = 10) -> List[Signal]:
        """Get the most recent signals"""
        return self.signal_history[-count:]
        
    def calculate_confidence_adjustment(self, signal: Signal) -> float:
        """Calculate confidence adjustment based on various factors"""
        # Default implementation - return the signal's confidence as is
        return signal.confidence
        
    def should_process_signal(self, signal: Signal) -> bool:
        """Determine if a signal should be processed"""
        # Default: process all signals
        return True