"""
Application service for execution in the enterprise hedge fund trading system.
"""
from typing import List, Optional
from domain.entities.trading_entities import Order, Fill
from domain.ports.execution_ports import ExecutionPort, ExecutionAlgorithmPort
from shared.logger import logger


class ExecutionService:
    """Application service for order execution"""
    
    def __init__(self, 
                 execution_port: ExecutionPort,
                 algorithm_ports: List[ExecutionAlgorithmPort] = None):
        self.execution_port = execution_port
        self.algorithm_ports = algorithm_ports or []
    
    def execute_order(self, order: Order) -> str:
        """Execute an order using the default execution method"""
        logger.info(f"Executing order for {order.symbol.value}")
        execution_id = self.execution_port.execute_order(order)
        logger.info(f"Order execution initiated, ID: {execution_id}")
        return execution_id
    
    def execute_algorithmic_order(self, order: Order, algorithm_name: str = "TWAP") -> str:
        """Execute an order using a specific algorithm"""
        for algorithm in self.algorithm_ports:
            if algorithm.get_algorithm_name() == algorithm_name:
                logger.info(f"Executing algorithmic order using {algorithm_name}")
                execution_id = algorithm.execute_algorithmic_order(order)
                logger.info(f"Algorithmic order execution initiated, ID: {execution_id}")
                return execution_id
        
        # If algorithm not found, fall back to default execution
        logger.warning(f"Algorithm {algorithm_name} not found, using default execution")
        return self.execute_order(order)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        logger.info(f"Cancelling order: {order_id}")
        success = self.execution_port.cancel_order(order_id)
        logger.info(f"Order cancellation result: {success}")
        return success
    
    def get_execution_status(self, execution_id: str) -> str:
        """Get the status of an execution"""
        status = self.execution_port.get_execution_status(execution_id)
        logger.info(f"Execution status for {execution_id}: {status}")
        return status


class ExecutionOrchestrationService:
    """Service for orchestrating complex execution strategies"""
    
    def __init__(self, execution_service: ExecutionService):
        self.execution_service = execution_service
    
    def execute_smart_execution(self, order: Order, execution_preferences: dict = None) -> str:
        """Execute an order using smart execution based on preferences"""
        if execution_preferences is None:
            execution_preferences = {}
        
        # Determine the best execution method based on preferences
        if order.quantity > 100:  # Large order, use algorithmic execution
            algorithm = execution_preferences.get('algorithm', 'TWAP')
            return self.execution_service.execute_algorithmic_order(order, algorithm)
        else:  # Small order, use direct execution
            return self.execution_service.execute_order(order)
    
    def execute_multi_leg_order(self, orders: List[Order]) -> List[str]:
        """Execute multiple orders as part of a single strategy"""
        execution_ids = []
        for order in orders:
            execution_id = self.execution_service.execute_order(order)
            execution_ids.append(execution_id)
        
        logger.info(f"Executed {len(orders)} orders as part of multi-leg strategy")
        return execution_ids


class ExecutionMonitoringService:
    """Service for monitoring execution performance"""
    
    def __init__(self, execution_service: ExecutionService):
        self.execution_service = execution_service
        self.execution_stats = {}
    
    def monitor_execution(self, execution_id: str) -> dict:
        """Monitor a specific execution and return performance metrics"""
        status = self.execution_service.get_execution_status(execution_id)
        
        metrics = {
            'execution_id': execution_id,
            'status': status,
            'latency': 0.1,  # Placeholder
            'slippage': 0.002,  # Placeholder
            'fill_rate': 1.0  # Placeholder
        }
        
        # Store in stats for historical analysis
        self.execution_stats[execution_id] = metrics
        
        return metrics
    
    def get_execution_performance(self) -> dict:
        """Get overall execution performance metrics"""
        if not self.execution_stats:
            return {}
        
        # Calculate average metrics
        total_latency = sum(m['latency'] for m in self.execution_stats.values())
        avg_latency = total_latency / len(self.execution_stats)
        
        total_slippage = sum(m['slippage'] for m in self.execution_stats.values())
        avg_slippage = total_slippage / len(self.execution_stats)
        
        performance = {
            'total_executions': len(self.execution_stats),
            'average_latency': avg_latency,
            'average_slippage': avg_slippage,
            'success_rate': 1.0  # Placeholder
        }
        
        return performance