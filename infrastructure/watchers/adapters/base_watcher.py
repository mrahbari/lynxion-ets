from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from domain.entities import MarketObservation
from shared.logger import logger
from domain.value_objects import Symbol, Percentage
from infrastructure.brokers.broker_manager import BrokerManager
import time
import threading
from decimal import Decimal


class BaseWatcher(ABC):
    """Base class for all watchers - produces only raw market observations, not trading signals"""

    def __init__(self, name: str, symbol: str, broker_service: BrokerManager = None, target_broker: str = None):
        self.name = name
        self.symbol = symbol
        self.is_running = False
        self.last_observation: Optional[MarketObservation] = None
        # Add broker service and target broker
        self.broker_service = broker_service
        self.target_broker = target_broker or "bingx"  # Default to bingx if no target specified
        # Ensure target broker name is lowercase to match broker keys
        if self.target_broker is not None:
            self.target_broker = self.target_broker.lower()

        # Add health monitoring capabilities
        self._last_error_time = None
        self._consecutive_errors = 0
        self._error_history = []
        self._max_error_history = 10
        self._health_lock = threading.Lock()

        # Add performance tracking
        self._observation_history = []
        self._max_observation_history = 100
        self._average_processing_time = 0.0
        self._total_processing_time = 0.0
        self._processing_count = 0
        self._observations_generated = 0
        self._errors_occurred = 0

    def get_broker(self):
        """Get the appropriate broker for this watcher"""
        if self.broker_service and hasattr(self.broker_service, 'get_broker_by_name'):
            return self.broker_service.get_broker_by_name(self.target_broker)
        elif self.broker_service and hasattr(self.broker_service, 'get_broker'):
            # Fallback to instrument_type mapping if get_broker_by_name not available
            return self.broker_service.get_broker(self.target_broker)
        return None

    def analyze(self, symbol: Symbol) -> Optional[MarketObservation]:
        """Analyze market conditions and return a raw market observation (no strategy selection)"""
        start_time = time.time()
        try:
            observation = self._analyze_impl(symbol)
            processing_time = time.time() - start_time

            # Update performance metrics
            with self._health_lock:
                self._observations_generated += 1
                self._total_processing_time += processing_time
                self._processing_count += 1
                self._average_processing_time = self._total_processing_time / self._processing_count

                # Keep track of recent observations
                self._observation_history.append({
                    'timestamp': time.time(),
                    'processing_time': processing_time,
                    'has_observation': observation is not None
                })

                # Keep only recent history
                if len(self._observation_history) > self._max_observation_history:
                    self._observation_history = self._observation_history[-self._max_observation_history:]

                # Reset error counters on successful operation
                self._consecutive_errors = 0
                self._errors_occurred = max(0, self._errors_occurred - 1)  # Reduce error count gradually

            return observation
        except Exception as e:
            processing_time = time.time() - start_time

            # Record error
            self._record_error(str(e), processing_time)

            # Log the error
            logger.error(f"Error in watcher {self.name}: {e}")
            raise

    @abstractmethod
    def _analyze_impl(self, symbol: Symbol) -> Optional[MarketObservation]:
        """Internal analyze implementation to be overridden by subclasses.
        Must return a MarketObservation, not a trading signal."""
        pass

    def _record_error(self, error_message: str, processing_time: float = 0.0):
        """Record an error in the watcher's operation."""
        with self._health_lock:
            self._errors_occurred += 1
            self._consecutive_errors += 1
            self._last_error_time = time.time()

            # Add to error history
            self._error_history.append({
                'timestamp': time.time(),
                'message': error_message,
                'processing_time': processing_time
            })

            # Keep only recent errors
            if len(self._error_history) > self._max_error_history:
                self._error_history = self._error_history[-self._max_error_history:]

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for this watcher."""
        with self._health_lock:
            return {
                'watcher_name': self.name,
                'symbol': self.symbol,
                'is_running': self.is_running,
                'observations_generated': self._observations_generated,
                'errors_occurred': self._errors_occurred,
                'consecutive_errors': self._consecutive_errors,
                'last_error_time': self._last_error_time,
                'average_processing_time': self._average_processing_time,
                'total_processing_time': self._total_processing_time,
                'processing_count': self._processing_count,
                'error_history_count': len(self._error_history),
                'observation_history_count': len(self._observation_history),
                'health_status': 'ERROR' if self._consecutive_errors >= 5 else \
                               'WARNING' if self._consecutive_errors >= 2 else 'HEALTHY'
            }

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

    def get_last_observation(self) -> Optional[MarketObservation]:
        """Get the last generated observation"""
        return self.last_observation

    def calculate_observation_value(self, data: Dict[str, Any]) -> float:
        """Calculate a numerical value for the observation (-1.0 to 1.0)"""
        # Default implementation - should be overridden by subclasses
        return 0.0

    def should_emit_observation(self, current_observation: MarketObservation) -> bool:
        """Determine if a new observation should be emitted"""
        # Default: emit if the observation is different from the last one
        if not self.last_observation:
            return True

        # Compare observations based on type and confidence
        current_conf = float(current_observation.confidence.value) if hasattr(current_observation.confidence, 'value') else float(current_observation.confidence)
        last_conf = float(self.last_observation.confidence.value) if hasattr(self.last_observation.confidence, 'value') else float(self.last_observation.confidence)

        # Don't emit if the same observation type was generated recently with similar confidence
        return (current_observation.observation_type != self.last_observation.observation_type or
                abs(current_conf - last_conf) > 0.1)