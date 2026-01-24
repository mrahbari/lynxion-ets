"""
Historical Data Tracker for Statistical Validation in the Enterprise Hedge Fund Trading System
Tracks historical observations, interpretations, fusions, decisions, executions, and closures
for statistical validation and authority scoring.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading


class HistoricalDataTracker:
    """
    Tracks historical data for statistical validation across all system components
    """
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.lock = threading.RLock()  # Use RLock to allow recursive locking
        
        # Track historical data by component and symbol
        self.historical_data = {
            'watcher': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'engine': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'fusion': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'strategy': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'broker': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'broker_close': defaultdict(lambda: deque(maxlen=self.max_entries))
        }
        
        # Track by symbol as well
        self.symbol_data = {
            'watcher': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'engine': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'fusion': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'strategy': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'broker': defaultdict(lambda: deque(maxlen=self.max_entries)),
            'broker_close': defaultdict(lambda: deque(maxlen=self.max_entries))
        }
    
    def add_watcher_observation(self, symbol: str, observation_data: Dict[str, Any]):
        """Add a watcher observation to historical data"""
        with self.lock:
            # Add to component-specific storage
            self.historical_data['watcher']['all'].append(observation_data)
            # Add to symbol-specific storage
            self.symbol_data['watcher'][symbol].append(observation_data)
    
    def add_engine_interpretation(self, symbol: str, interpretation_data: Dict[str, Any]):
        """Add an engine interpretation to historical data"""
        with self.lock:
            # Add to component-specific storage
            self.historical_data['engine']['all'].append(interpretation_data)
            # Add to symbol-specific storage
            self.symbol_data['engine'][symbol].append(interpretation_data)
    
    def add_fusion_result(self, symbol: str, fusion_data: Dict[str, Any]):
        """Add a fusion result to historical data"""
        with self.lock:
            # Add to component-specific storage
            self.historical_data['fusion']['all'].append(fusion_data)
            # Add to symbol-specific storage
            self.symbol_data['fusion'][symbol].append(fusion_data)
    
    def add_strategy_decision(self, symbol: str, decision_data: Dict[str, Any]):
        """Add a strategy decision to historical data"""
        with self.lock:
            # Add to component-specific storage
            self.historical_data['strategy']['all'].append(decision_data)
            # Add to symbol-specific storage
            self.symbol_data['strategy'][symbol].append(decision_data)
    
    def add_broker_execution(self, symbol: str, execution_data: Dict[str, Any]):
        """Add a broker execution to historical data"""
        with self.lock:
            # Add to component-specific storage
            self.historical_data['broker']['all'].append(execution_data)
            # Add to symbol-specific storage
            self.symbol_data['broker'][symbol].append(execution_data)
    
    def add_broker_close(self, symbol: str, close_data: Dict[str, Any]):
        """Add a broker close to historical data"""
        with self.lock:
            # Add to component-specific storage
            self.historical_data['broker_close']['all'].append(close_data)
            # Add to symbol-specific storage
            self.symbol_data['broker_close'][symbol].append(close_data)
    
    def get_watcher_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical watcher observations"""
        with self.lock:
            if symbol:
                return list(self.symbol_data['watcher'][symbol])[-limit:]
            else:
                return list(self.historical_data['watcher']['all'])[-limit:]
    
    def get_engine_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical engine interpretations"""
        with self.lock:
            if symbol:
                return list(self.symbol_data['engine'][symbol])[-limit:]
            else:
                return list(self.historical_data['engine']['all'])[-limit:]
    
    def get_fusion_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical fusion results"""
        with self.lock:
            if symbol:
                return list(self.symbol_data['fusion'][symbol])[-limit:]
            else:
                return list(self.historical_data['fusion']['all'])[-limit:]
    
    def get_strategy_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical strategy decisions"""
        with self.lock:
            if symbol:
                return list(self.symbol_data['strategy'][symbol])[-limit:]
            else:
                return list(self.historical_data['strategy']['all'])[-limit:]
    
    def get_broker_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical broker executions"""
        with self.lock:
            if symbol:
                return list(self.symbol_data['broker'][symbol])[-limit:]
            else:
                return list(self.historical_data['broker']['all'])[-limit:]
    
    def get_broker_close_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical broker closes"""
        with self.lock:
            if symbol:
                return list(self.symbol_data['broker_close'][symbol])[-limit:]
            else:
                return list(self.historical_data['broker_close']['all'])[-limit:]
    
    def get_all_history_for_symbol(self, symbol: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all historical data for a specific symbol"""
        with self.lock:
            return {
                'watcher': list(self.symbol_data['watcher'][symbol]),
                'engine': list(self.symbol_data['engine'][symbol]),
                'fusion': list(self.symbol_data['fusion'][symbol]),
                'strategy': list(self.symbol_data['strategy'][symbol]),
                'broker': list(self.symbol_data['broker'][symbol]),
                'broker_close': list(self.symbol_data['broker_close'][symbol])
            }
    
    def clear_symbol_data(self, symbol: str):
        """Clear historical data for a specific symbol"""
        with self.lock:
            for component in self.symbol_data:
                if symbol in self.symbol_data[component]:
                    del self.symbol_data[component][symbol]
    
    def clear_all_data(self):
        """Clear all historical data"""
        with self.lock:
            for component in self.historical_data:
                self.historical_data[component]['all'].clear()
            for component in self.symbol_data:
                self.symbol_data[component].clear()


# Global historical data tracker instance
historical_data_tracker = HistoricalDataTracker()