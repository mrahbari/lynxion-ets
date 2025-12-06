from typing import Dict, Type, Any, Optional
from domain.ports.trading_ports import (
    SignalPort, OrderManagementPort, MarketDataPort, 
    PositionManagementPort, RiskManagementPort
)
from domain.ports.strategy_ports import (
    EnginePort, StrategyPort, FusionPort, RiskGovernorPort
)


class Container:
    """Dependency injection container for the application"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._service_factories: Dict[str, callable] = {}
    
    def register(self, name: str, service: Any, singleton: bool = True):
        """Register a service instance or factory"""
        if singleton:
            self._services[name] = service
        else:
            self._service_factories[name] = service
    
    def register_singleton(self, name: str, service: Any):
        """Register a singleton service instance"""
        self._services[name] = service
    
    def register_factory(self, name: str, factory: callable):
        """Register a service factory"""
        self._service_factories[name] = factory
    
    def resolve(self, name: str) -> Any:
        """Resolve a service by name"""
        if name in self._services:
            return self._services[name]
        elif name in self._service_factories:
            # Create instance using factory and cache it if it's a singleton concept
            service = self._service_factories[name]()
            self._services[name] = service  # Cache for future use as singleton
            return service
        else:
            raise ValueError(f"Service '{name}' not registered in container")
    
    def has(self, name: str) -> bool:
        """Check if a service is registered"""
        return name in self._services or name in self._service_factories


# Global container instance
container = Container()


# Type aliases for commonly used ports
SignalPortType = SignalPort
OrderManagementPortType = OrderManagementPort
MarketDataPortType = MarketDataPort
PositionManagementPortType = PositionManagementPort
RiskManagementPortType = RiskManagementPort
EnginePortType = EnginePort
StrategyPortType = StrategyPort
FusionPortType = FusionPort
RiskGovernorPortType = RiskGovernorPort