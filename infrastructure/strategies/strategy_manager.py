"""
Strategy Manager for handling strategy lifecycle, health monitoring, and execution coordination.
This is the ONLY layer that selects strategies and deploys capital.
"""
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from domain.value_objects import Symbol
from domain.entities.signal_entities import FusedSignal, ExecutionIntent
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter
from shared.logger import EnhancedLogger


class StrategyManager:
    """
    Manages multiple strategies with health monitoring and execution coordination.
    This is the ONLY layer that selects strategies and decides on capital deployment.
    """

    def __init__(self):
        self.strategies: Dict[str, BaseStrategyAdapter] = {}
        self.strategy_factories: Dict[str, Callable[[], BaseStrategyAdapter]] = {}
        self.strategy_threads: Dict[str, threading.Thread] = {}
        self.strategy_status: Dict[str, str] = {}  # 'RUNNING', 'STOPPED', 'ERROR'
        self.health_check_interval = 30  # seconds
        self.auto_restart_enabled = True
        self.logger = EnhancedLogger("StrategyManager")
        self.monitoring_active = False
        self.monitoring_thread = None

    def register_strategy(self, name: str, strategy: BaseStrategyAdapter,
                         factory: Optional[Callable[[], BaseStrategyAdapter]] = None):
        """Register a strategy with the manager."""
        self.strategies[name] = strategy
        if factory:
            self.strategy_factories[name] = factory
        self.strategy_status[name] = 'RUNNING'
        self.logger.info(f"Registered strategy: {name}")

    def unregister_strategy(self, name: str):
        """Unregister a strategy from the manager."""
        if name in self.strategies:
            del self.strategies[name]
        if name in self.strategy_factories:
            del self.strategy_factories[name]
        if name in self.strategy_status:
            del self.strategy_status[name]
        self.logger.info(f"Unregistered strategy: {name}")

    def start_monitoring(self):
        """Start the health monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            self.logger.info("Strategy monitoring started")

    def stop_monitoring(self):
        """Stop the health monitoring thread."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
        self.logger.info("Strategy monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop to check strategy health."""
        self.logger.info("Strategy monitoring loop started")

        while self.monitoring_active:
            try:
                self._check_all_strategies_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Error in strategy monitoring loop: {e}")
                time.sleep(self.health_check_interval)

    def _check_all_strategies_health(self):
        """Check health of all registered strategies."""
        for name, strategy in self.strategies.items():
            try:
                health_status = self._get_strategy_health_status(name)

                # Check if strategy is in error state
                if health_status.get('health_status') == 'ERROR':
                    self.logger.warning(f"Strategy {name} is in ERROR state")
                    self._handle_strategy_error(name, strategy)
                elif health_status.get('health_status') == 'WARNING':
                    # Check if error count is too high
                    error_count = health_status.get('error_count', 0)
                    if error_count > 5:  # Threshold for restart
                        self.logger.warning(f"Strategy {name} has {error_count} errors, restarting...")
                        self._restart_strategy(name)

                # Log strategy metrics periodically
                if health_status.get('execution_intents_count', 0) % 10 == 0:  # Every 10 execution intents
                    self.logger.info(f"Strategy {name} - Execution Intents: {health_status.get('execution_intents_count')}, "
                                   f"Errors: {health_status.get('error_count')}, "
                                   f"Status: {health_status.get('health_status')}")

            except Exception as e:
                self.logger.error(f"Error checking health for strategy {name}: {e}")
                self._handle_strategy_error(name, strategy)

    def _get_strategy_health_status(self, name: str) -> Dict[str, Any]:
        """Get health status for a specific strategy"""
        # For now, return a basic status - in a real implementation, strategies would track their own health
        return {
            'strategy_name': name,
            'health_status': 'HEALTHY',
            'execution_intents_count': 0,  # Would be tracked by the strategy
            'error_count': 0,
            'last_update': time.time()
        }

    def _handle_strategy_error(self, name: str, strategy: BaseStrategyAdapter):
        """Handle strategy errors based on configuration."""
        if self.auto_restart_enabled and name in self.strategy_factories:
            self.logger.info(f"Attempting to restart strategy: {name}")
            self._restart_strategy(name)
        else:
            self.logger.error(f"Strategy {name} failed and auto-restart is disabled")
            self.strategy_status[name] = 'ERROR'

    def _restart_strategy(self, name: str):
        """Restart a failed strategy."""
        if name not in self.strategy_factories:
            self.logger.error(f"Cannot restart strategy {name}: no factory available")
            return False

        try:
            self.logger.info(f"Restarting strategy: {name}")

            # Get the old strategy's data if needed
            old_strategy = self.strategies[name]

            # Create new instance using factory
            new_strategy = self.strategy_factories[name]()

            # Transfer any important state if needed
            # For now, we'll just replace the strategy
            self.strategies[name] = new_strategy
            self.strategy_status[name] = 'RUNNING'

            self.logger.info(f"Successfully restarted strategy: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to restart strategy {name}: {e}")
            self.strategy_status[name] = 'ERROR'
            return False

    def evaluate_fused_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate a fused signal across all available strategies and return the best execution intent."""
        best_intent = None
        highest_confidence = 0.0

        for name, strategy in self.strategies.items():
            try:
                intent = strategy.evaluate_fused_signal(fused_signal)
                if intent and float(intent.intent_confidence.value) > highest_confidence:
                    best_intent = intent
                    highest_confidence = float(intent.intent_confidence.value)
            except Exception as e:
                self.logger.error(f"Error evaluating fused signal with strategy {name}: {e}")
                continue

        return best_intent

    def get_active_strategies(self) -> List[str]:
        """Get list of active strategy names."""
        return list(self.strategies.keys())

    def add_strategy(self, strategy: BaseStrategyAdapter):
        """Add a strategy to the manager."""
        name = strategy.get_strategy_name()
        self.register_strategy(name, strategy)

    def get_all_health_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all strategies."""
        statuses = {}
        for name in self.strategies.keys():
            try:
                statuses[name] = self._get_strategy_health_status(name)
            except Exception as e:
                self.logger.error(f"Error getting health status for strategy {name}: {e}")
                statuses[name] = {
                    'strategy_name': name,
                    'health_status': 'ERROR',
                    'error': str(e)
                }
        return statuses

    def get_strategy_performance(self, name: str) -> Dict[str, Any]:
        """Get performance metrics for a specific strategy."""
        if name not in self.strategies:
            return {}

        try:
            return self._get_strategy_health_status(name)
        except Exception as e:
            self.logger.error(f"Error getting performance for strategy {name}: {e}")
            return {}

    def is_strategy_healthy(self, name: str) -> bool:
        """Check if a specific strategy is healthy."""
        if name not in self.strategies:
            return False

        try:
            health_status = self._get_strategy_health_status(name)
            return health_status.get('health_status') == 'HEALTHY'
        except Exception:
            return False


# Global strategy manager instance
strategy_manager = StrategyManager()