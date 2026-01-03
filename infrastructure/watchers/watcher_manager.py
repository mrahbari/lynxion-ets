"""
Watcher Health Monitoring and Management System
Implements health monitoring, automatic restarts, and error isolation for watchers.
Following correct architecture: Watchers only produce raw market observations.
"""
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from domain.value_objects import Symbol
from domain.entities.signal_entities import MarketObservation
from infrastructure.watchers.base_watcher import BaseWatcherAdapter
from shared.logger import EnhancedLogger


class WatcherHealthMonitor:
    """Monitors health metrics for individual watchers."""

    def __init__(self, watcher_name: str):
        self.watcher_name = watcher_name
        self.created_at = datetime.now()
        self.last_observation_time = None
        self.last_error_time = None
        self.total_observations = 0
        self.error_count = 0
        self.consecutive_errors = 0
        self.last_update_time = time.time()
        self.status = "HEALTHY"  # HEALTHY, WARNING, ERROR
        self.error_messages = []
        self.max_error_messages = 10
        self.lock = threading.Lock()

    def record_observation(self):
        """Record a successful observation generation."""
        with self.lock:
            self.last_observation_time = datetime.now()
            self.total_observations += 1
            self.consecutive_errors = 0
            if self.status == "ERROR":
                self.status = "HEALTHY"
            elif self.status == "WARNING":
                self.status = "HEALTHY"
            self.last_update_time = time.time()

    def record_error(self, error_message: str):
        """Record an error in watcher operation."""
        with self.lock:
            self.last_error_time = datetime.now()
            self.error_count += 1
            self.consecutive_errors += 1

            # Add error message to history
            self.error_messages.append({
                'timestamp': datetime.now(),
                'message': error_message
            })

            # Keep only recent error messages
            if len(self.error_messages) > self.max_error_messages:
                self.error_messages = self.error_messages[-self.max_error_messages:]

            # Update status based on error severity
            if self.consecutive_errors >= 5:
                self.status = "ERROR"
            elif self.consecutive_errors >= 2:
                self.status = "WARNING"
            elif self.status == "HEALTHY":
                # If it was healthy and we have an error, move to warning
                self.status = "WARNING"

            self.last_update_time = time.time()

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of the watcher."""
        with self.lock:
            return {
                'watcher_name': self.watcher_name,
                'created_at': self.created_at,
                'last_observation_time': self.last_observation_time,
                'last_error_time': self.last_error_time,
                'total_observations': self.total_observations,
                'error_count': self.error_count,
                'consecutive_errors': self.consecutive_errors,
                'status': self.status,
                'error_messages': self.error_messages[-3:],  # Last 3 error messages
                'uptime_seconds': time.time() - self.created_at.timestamp(),
                'last_update_time': datetime.fromtimestamp(self.last_update_time)
            }


class WatcherManager:
    """Manages multiple watchers with health monitoring and automatic restart capabilities."""

    def __init__(self):
        self.watchers: Dict[str, BaseWatcherAdapter] = {}
        self.watcher_factories: Dict[str, callable] = {}
        self.watcher_threads: Dict[str, threading.Thread] = {}
        self.watcher_health: Dict[str, WatcherHealthMonitor] = {}
        self.watcher_configs: Dict[str, Dict[str, Any]] = {}
        self.monitoring_active = False
        self.monitoring_thread = None
        self.health_check_interval = 30  # seconds
        self.auto_restart_enabled = True
        self.logger = EnhancedLogger("WatcherManager")
        self.lock = threading.Lock()

    def register_watcher(self, name: str, watcher: BaseWatcherAdapter,
                        factory: Optional[callable] = None,
                        config: Optional[Dict[str, Any]] = None):
        """Register a watcher with the manager."""
        with self.lock:
            self.watchers[name] = watcher
            if factory:
                self.watcher_factories[name] = factory
            if config:
                self.watcher_configs[name] = config
            self.watcher_health[name] = WatcherHealthMonitor(name)
            self.logger.info(f"Registered watcher: {name}")

    def unregister_watcher(self, name: str):
        """Unregister a watcher from the manager."""
        with self.lock:
            if name in self.watchers:
                del self.watchers[name]
            if name in self.watcher_factories:
                del self.watcher_factories[name]
            if name in self.watcher_configs:
                del self.watcher_configs[name]
            if name in self.watcher_health:
                del self.watcher_health[name]
            if name in self.watcher_threads:
                thread = self.watcher_threads[name]
                if thread and thread.is_alive():
                    # Attempt to stop the thread gracefully
                    if hasattr(self.watchers.get(name), 'stop'):
                        try:
                            self.watchers[name].stop()
                        except:
                            pass
                del self.watcher_threads[name]
            self.logger.info(f"Unregistered watcher: {name}")

    def start_monitoring(self):
        """Start the health monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            self.logger.info("Watcher monitoring started")

    def stop_monitoring(self):
        """Stop the health monitoring thread."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
        self.logger.info("Watcher monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop to check watcher health."""
        self.logger.info("Watcher monitoring loop started")

        while self.monitoring_active:
            try:
                self._check_all_watchers_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Error in watcher monitoring loop: {e}")
                time.sleep(self.health_check_interval)

    def _check_all_watchers_health(self):
        """Check health of all registered watchers."""
        for name, watcher in self.watchers.items():
            try:
                health_status = self.watcher_health[name].get_health_status()

                # Check if watcher is in error state
                if health_status.get('status') == 'ERROR':
                    self.logger.warning(f"Watcher {name} is in ERROR state with {health_status.get('consecutive_errors')} consecutive errors")
                    self._handle_watcher_error(name, watcher)
                elif health_status.get('status') == 'WARNING':
                    # Check if error count is too high
                    error_count = health_status.get('error_count', 0)
                    consecutive_errors = health_status.get('consecutive_errors', 0)
                    if consecutive_errors >= 3:  # Threshold for restart
                        self.logger.warning(f"Watcher {name} has {consecutive_errors} consecutive errors, considering restart...")
                        if error_count > 5:  # Restart if total errors exceed threshold
                            self._restart_watcher(name)

                # Log watcher metrics periodically
                if health_status.get('total_observations', 0) % 10 == 0:  # Every 10 observations
                    self.logger.info(f"Watcher {name} - Observations: {health_status.get('total_observations')}, "
                                   f"Errors: {health_status.get('error_count')}, "
                                   f"Status: {health_status.get('status')}")

            except Exception as e:
                self.logger.error(f"Error checking health for watcher {name}: {e}")
                self._handle_watcher_error(name, watcher)

    def _handle_watcher_error(self, name: str, watcher: BaseWatcherAdapter):
        """Handle watcher errors based on configuration."""
        if self.auto_restart_enabled and name in self.watcher_factories:
            self.logger.info(f"Attempting to restart watcher: {name}")
            self._restart_watcher(name)
        else:
            self.logger.error(f"Watcher {name} failed and auto-restart is disabled")

    def _restart_watcher(self, name: str):
        """Restart a failed watcher."""
        if name not in self.watcher_factories:
            self.logger.error(f"Cannot restart watcher {name}: no factory available")
            return False

        try:
            self.logger.info(f"Restarting watcher: {name}")

            # Stop the old watcher if possible
            old_watcher = self.watchers[name]
            if hasattr(old_watcher, 'stop'):
                try:
                    old_watcher.stop()
                except:
                    pass  # Ignore errors when stopping

            # Create new instance using factory
            config = self.watcher_configs.get(name, {})
            new_watcher = self.watcher_factories[name](**config)

            # Replace the watcher
            self.watchers[name] = new_watcher

            # Reset health monitor
            self.watcher_health[name] = WatcherHealthMonitor(name)

            # Restart if the watcher was running
            if hasattr(new_watcher, 'start'):
                try:
                    new_watcher.start()
                    self.logger.info(f"Successfully restarted and started watcher: {name}")
                except Exception as e:
                    self.logger.error(f"Failed to start restarted watcher {name}: {e}")
                    return False
            else:
                self.logger.info(f"Successfully restarted watcher: {name} (no start method)")

            return True

        except Exception as e:
            self.logger.error(f"Failed to restart watcher {name}: {e}")
            return False

    def analyze_symbol(self, name: str, symbol: Symbol) -> Optional[MarketObservation]:
        """Analyze a symbol for a specific watcher with error isolation.
        Returns raw market observations, not trading signals."""
        if name not in self.watchers:
            self.logger.error(f"Watcher {name} not found")
            return None

        watcher = self.watchers[name]

        try:
            observation = watcher.analyze(symbol)
            if observation:
                self.watcher_health[name].record_observation()
            return observation
        except Exception as e:
            error_msg = f"Error analyzing {symbol.value} for watcher {name}: {e}"
            self.logger.error(error_msg)
            # Record the error in the watcher's health monitor
            self.watcher_health[name].record_error(str(e))
            self._handle_watcher_error(name, watcher)
            return None

    def get_all_health_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all watchers."""
        statuses = {}
        for name, health_monitor in self.watcher_health.items():
            try:
                statuses[name] = health_monitor.get_health_status()
            except Exception as e:
                self.logger.error(f"Error getting health status for watcher {name}: {e}")
                statuses[name] = {
                    'watcher_name': name,
                    'status': 'ERROR',
                    'error': str(e)
                }
        return statuses

    def is_watcher_healthy(self, name: str) -> bool:
        """Check if a specific watcher is healthy."""
        if name not in self.watcher_health:
            return False

        try:
            health_status = self.watcher_health[name].get_health_status()
            return health_status.get('status') == 'HEALTHY'
        except Exception:
            return False

    def get_watcher_performance(self, name: str) -> Dict[str, Any]:
        """Get performance metrics for a specific watcher."""
        if name not in self.watcher_health:
            return {}

        try:
            return self.watcher_health[name].get_health_status()
        except Exception as e:
            self.logger.error(f"Error getting performance for watcher {name}: {e}")
            return {}


# Global watcher manager instance
watcher_manager = WatcherManager()