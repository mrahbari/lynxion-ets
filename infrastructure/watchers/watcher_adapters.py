"""
Infrastructure base adapter for watcher implementations.
Contains only the shared base class to avoid duplication across individual watcher adapters.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from domain.entities import Signal
from domain.value_objects import Symbol, Percentage
from domain.ports.watcher_ports import WatcherPort
from shared.logger import EnhancedLogger


class BaseWatcherAdapter(WatcherPort):
    """Base class for watcher adapters implementing WatcherPort"""

    def __init__(self, name: str, symbol: Symbol):
        self.name = name
        self.symbol = symbol
        self._is_running = False
        self.last_signal: Optional[Signal] = None
        self.logger = EnhancedLogger(f"{name}_{symbol.value}")

    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze market conditions and return a signal - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement analyze method")

    def start(self):
        """Start the watcher"""
        try:
            self._is_running = True
            self.logger.log_watcher_analysis(self.name, self.symbol.value, "Started")
        except Exception as e:
            self.logger.error(f"Error starting watcher {self.name}: {e}")

    def stop(self):
        """Stop the watcher"""
        try:
            self._is_running = False
            self.logger.log_watcher_analysis(self.name, self.symbol.value, "Stopped")
        except Exception as e:
            self.logger.error(f"Error stopping watcher {self.name}: {e}")

    def is_running(self) -> bool:
        """Check if the watcher is currently running"""
        return self._is_running

    def update_data(self, data: Dict[str, Any]):
        """Update the watcher with new market data"""
        # Base implementation - can be overridden by specific watchers
        pass

    def should_emit_signal(self, current_signal: Signal) -> bool:
        """Determine if a new signal should be emitted"""
        if not self.last_signal:
            return True

        # Don't emit if the same signal was generated recently with similar confidence
        return (current_signal.signal_type.name != self.last_signal.signal_type.name or
                abs(float(current_signal.confidence.value) - float(self.last_signal.confidence.value)) > 0.1)