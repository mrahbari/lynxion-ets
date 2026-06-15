"""
Use cases for execution functionality in the enterprise hedge fund trading system.
"""
from typing import List
from domain.entities import Order
from application.services.execution_services import ExecutionOrchestrationService


class ExecuteOrderUseCase:
    """Use case for executing an order"""
    
    def __init__(self, execution_service):
        self.execution_service = execution_service
    
    def execute(self, order: Order) -> str:
        """Execute the use case to place an order"""
        return self.execution_service.execute_order(order)


class ExecuteAlgorithmicOrderUseCase:
    """Use case for executing an algorithmic order"""
    
    def __init__(self, execution_service):
        self.execution_service = execution_service
    
    def execute(self, order: Order, algorithm_name: str = "TWAP") -> str:
        """Execute the use case to place an algorithmic order"""
        return self.execution_service.execute_algorithmic_order(order, algorithm_name)


class ExecuteSmartOrderUseCase:
    """Use case for executing an order with smart execution"""
    
    def __init__(self, execution_orchestration_service: ExecutionOrchestrationService):
        self.execution_orchestration_service = execution_orchestration_service
    
    def execute(self, order: Order, execution_preferences: dict = None) -> str:
        """Execute the use case to place an order using smart execution"""
        return self.execution_orchestration_service.execute_smart_execution(order, execution_preferences)


class CancelOrderUseCase:
    """Use case for cancelling an order"""
    
    def __init__(self, execution_service):
        self.execution_service = execution_service
    
    def execute(self, order_id: str) -> bool:
        """Execute the use case to cancel an order"""
        return self.execution_service.cancel_order(order_id)


class GetExecutionStatusUseCase:
    """Use case for getting execution status"""
    
    def __init__(self, execution_service):
        self.execution_service = execution_service
    
    def execute(self, execution_id: str) -> str:
        """Execute the use case to get execution status"""
        return self.execution_service.get_execution_status(execution_id)