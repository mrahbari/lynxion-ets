from typing import Dict, List, Type, Any
from .base_engine import BaseEngine
from shared.logger import logger


class EngineRegistry:
    """Registry for managing engines"""
    
    def __init__(self):
        self.engines: Dict[str, BaseEngine] = {}
        self.engine_types: Dict[str, Type[BaseEngine]] = {}
        
    def register_engine_type(self, name: str, engine_class: Type[BaseEngine]):
        """Register an engine type"""
        self.engine_types[name] = engine_class
        logger.info(f"Registered engine type: {name}")
        
    def create_engine(self, name: str, engine_type: str, **kwargs) -> BaseEngine:
        """Create an engine instance"""
        if engine_type not in self.engine_types:
            raise ValueError(f"Unknown engine type: {engine_type}")
            
        engine_class = self.engine_types[engine_type]
        engine = engine_class(name)
        
        # Initialize with any additional kwargs
        for key, value in kwargs.items():
            if hasattr(engine, key):
                setattr(engine, key, value)
        
        # Store the engine
        self.engines[name] = engine
        logger.info(f"Created engine: {name} of type {engine_type}")
        
        return engine
        
    def get_engine(self, name: str) -> BaseEngine:
        """Get an engine by name"""
        if name not in self.engines:
            raise ValueError(f"Engine not found: {name}")
        return self.engines[name]
        
    def get_all_engines(self) -> List[BaseEngine]:
        """Get all engines"""
        return list(self.engines.values())
        
    def start_engine(self, name: str):
        """Start a specific engine"""
        engine = self.get_engine(name)
        engine.start()
        
    def stop_engine(self, name: str):
        """Stop a specific engine"""
        engine = self.get_engine(name)
        engine.stop()
        
    def start_all_engines(self):
        """Start all engines"""
        for engine in self.engines.values():
            engine.start()
            
    def stop_all_engines(self):
        """Stop all engines"""
        for engine in self.engines.values():
            engine.stop()
            
    def process_signal(self, engine_name: str, signal: Any):
        """Process a signal through a specific engine"""
        engine = self.get_engine(engine_name)
        return engine.process_signal(signal)
        
    def update_all_engines(self, data: Dict[str, Any]):
        """Update all engines with new data"""
        for engine in self.engines.values():
            engine.update_data(data)