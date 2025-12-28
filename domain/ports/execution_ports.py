from abc import abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from domain.entities.trading_entities import Order, Fill
from domain.value_objects import Symbol


class ExecutionPort(Protocol):
    """Port for execution services that handle order execution"""
    
    @abstractmethod
    def execute_order(self, order: Order) -> str:  # Returns execution ID or order ID
        """Execute an order and return execution identifier"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        pass
    
    @abstractmethod
    def get_execution_status(self, execution_id: str) -> str:
        """Get the status of an execution"""
        pass

    @abstractmethod
    def get_available_symbols(self) -> set:
        """Get the set of available symbols on the broker"""
        pass


class ExecutionAlgorithmPort(Protocol):
    """Port for execution algorithms (TWAP, VWAP, etc.)"""
    
    @abstractmethod
    def execute_algorithmic_order(self, order: Order) -> str:
        """Execute an order using algorithmic trading methods"""
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """Get the name of this execution algorithm"""
        pass