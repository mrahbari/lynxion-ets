from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities import Order, Fill, Position, Balance
from domain.value_objects import Symbol, Money


class BrokerPort(Protocol):
    """Port for broker operations"""
    
    @abstractmethod
    def connect(self):
        """Connect to the broker"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the broker"""
        pass
    
    @abstractmethod
    def place_order(self, order: Order) -> str:
        """Place an order and return order ID"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: Symbol) -> bool:
        """Cancel an order by ID"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str, symbol: Symbol) -> str:
        """Get the status of an order"""
        pass
    
    @abstractmethod
    def get_balance(self, asset: str = None) -> List[Balance]:
        """Get account balance"""
        pass
    
    @abstractmethod
    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get position for a symbol"""
        pass
    
    @abstractmethod
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        pass

    @abstractmethod
    def get_available_symbols(self) -> set:
        """Get set of available symbols on this broker"""
        pass


class BrokerAdapterManagerPort(Protocol):
    """Port for managing multiple brokers"""
    
    @abstractmethod
    def add_broker(self, broker: BrokerPort, name: str):
        """Add a broker to the manager"""
        pass
    
    @abstractmethod
    def get_broker(self, name: str) -> Optional[BrokerPort]:
        """Get a broker by name"""
        pass
    
    @abstractmethod
    def route_order(self, order: Order) -> str:
        """Route an order to an appropriate broker"""
        pass
    
    @abstractmethod
    def get_best_price(self, symbol: Symbol) -> Optional[Money]:
        """Get the best available price across all brokers"""
        pass