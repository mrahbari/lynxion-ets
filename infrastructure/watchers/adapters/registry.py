from typing import Dict, List, Type
from .base_watcher import BaseWatcher
from shared.logger import logger


class WatcherRegistry:
    """Registry for managing watchers"""
    
    def __init__(self):
        self.watchers: Dict[str, BaseWatcher] = {}
        self.watcher_types: Dict[str, Type[BaseWatcher]] = {}
        
    def register_watcher_type(self, name: str, watcher_class: Type[BaseWatcher]):
        """Register a watcher type"""
        self.watcher_types[name] = watcher_class
        logger.info(f"Registered watcher type: {name}")
        
    def create_watcher(self, name: str, watcher_type: str, symbol: str, **kwargs) -> BaseWatcher:
        """Create a watcher instance"""
        if watcher_type not in self.watcher_types:
            raise ValueError(f"Unknown watcher type: {watcher_type}")
            
        watcher_class = self.watcher_types[watcher_type]
        watcher = watcher_class(name, symbol)
        
        # Store the watcher
        self.watchers[name] = watcher
        logger.info(f"Created watcher: {name} of type {watcher_type} for symbol: {symbol}")
        
        return watcher
        
    def get_watcher(self, name: str) -> BaseWatcher:
        """Get a watcher by name"""
        if name not in self.watchers:
            raise ValueError(f"Watcher not found: {name}")
        return self.watchers[name]
        
    def get_all_watchers(self) -> List[BaseWatcher]:
        """Get all watchers"""
        return list(self.watchers.values())
        
    def start_watcher(self, name: str):
        """Start a specific watcher"""
        watcher = self.get_watcher(name)
        watcher.start()
        
    def stop_watcher(self, name: str):
        """Stop a specific watcher"""
        watcher = self.get_watcher(name)
        watcher.stop()
        
    def start_all_watchers(self):
        """Start all watchers"""
        for watcher in self.watchers.values():
            watcher.start()
            
    def stop_all_watchers(self):
        """Stop all watchers"""
        for watcher in self.watchers.values():
            watcher.stop()
            
    def update_all_watchers(self, data: Dict[str, any]):
        """Update all watchers with new data"""
        for watcher in self.watchers.values():
            watcher.update_data(data)