"""
Infrastructure base adapter for watcher implementations following correct architecture.
Watchers should only produce raw market observations, not trading signals with strategy selection.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from domain.entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from domain.ports.watcher_ports import WatcherPort
from shared.logger import EnhancedLogger


class BaseWatcher(WatcherPort):
    """Base class for watcher adapters implementing WatcherPort - produces only raw market observations"""

    def __init__(self, name: str, symbol: Symbol):
        self.name = name
        self.symbol = symbol
        self._is_running = False
        self.last_observation: Optional[MarketObservation] = None
        self.logger = EnhancedLogger(f"{name}_{symbol.value}")

    def analyze(self, symbol: Symbol) -> Optional[MarketObservation]:
        """Analyze market conditions and return a raw market observation - to be implemented by subclasses"""
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

    def should_emit_observation(self, current_observation: MarketObservation) -> bool:
        """Determine if a new observation should be emitted"""
        if not self.last_observation:
            return True

        # Don't emit if the same observation type was generated recently with similar confidence
        return (current_observation.observation_type != self.last_observation.observation_type or
                abs(float(current_observation.confidence.value) - float(self.last_observation.confidence.value)) > 0.1)