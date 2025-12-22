"""
Strategy Manager for handling strategy lifecycle, health monitoring, and automatic restarts.
"""
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from domain.value_objects import Symbol
from domain.entities.trading_entities import Signal
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter
from shared.logger import EnhancedLogger


class StrategyManager:
    """
    Manages multiple strategies with health monitoring and automatic restart capabilities.
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
                health_status = strategy.get_health_status()
                
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
                if health_status.get('signal_count', 0) % 10 == 0:  # Every 10 signals
                    self.logger.info(f"Strategy {name} - Signals: {health_status.get('signal_count')}, "
                                   f"Errors: {health_status.get('error_count')}, "
                                   f"Status: {health_status.get('health_status')}")
                
            except Exception as e:
                self.logger.error(f"Error checking health for strategy {name}: {e}")
                self._handle_strategy_error(name, strategy)
    
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
    
    def generate_signal_for_strategy(self, name: str, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal for a specific strategy with error isolation."""
        if name not in self.strategies:
            self.logger.error(f"Strategy {name} not found")
            return None
        
        strategy = self.strategies[name]
        
        try:
            signal = strategy.generate_signal(symbol)
            return signal
        except Exception as e:
            self.logger.error(f"Error generating signal for strategy {name}: {e}")
            # Record the error in the strategy's health monitor
            strategy.health_monitor.record_error(e)
            self._handle_strategy_error(name, strategy)
            return None
    
    def generate_signals_for_all_strategies(self, symbol: Symbol) -> Dict[str, Optional[Signal]]:
        """Generate signals for all strategies with error isolation."""
        results = {}
        
        for name in list(self.strategies.keys()):  # Use list to avoid modification during iteration
            try:
                signal = self.generate_signal_for_strategy(name, symbol)
                results[name] = signal
            except Exception as e:
                self.logger.error(f"Unexpected error for strategy {name}: {e}")
                results[name] = None
        
        return results
    
    def get_all_health_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all strategies."""
        statuses = {}
        for name, strategy in self.strategies.items():
            try:
                statuses[name] = strategy.get_health_status()
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
            return self.strategies[name].get_health_status()
        except Exception as e:
            self.logger.error(f"Error getting performance for strategy {name}: {e}")
            return {}
    
    def is_strategy_healthy(self, name: str) -> bool:
        """Check if a specific strategy is healthy."""
        if name not in self.strategies:
            return False
        
        try:
            health_status = self.strategies[name].get_health_status()
            return health_status.get('health_status') == 'HEALTHY'
        except Exception:
            return False


# Global strategy manager instance
strategy_manager = StrategyManager()