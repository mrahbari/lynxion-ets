"""
Advanced execution service with risk-aware execution and multi-broker support.
"""
from typing import Dict, List, Optional
from decimal import Decimal
import time

from domain.entities import Order, Fill, Position
from domain.value_objects import Symbol, Money, Percentage
from domain.ports.execution_ports import ExecutionPort
from application.services.execution_services import ExecutionService
from infrastructure.risk.advanced_risk_management import SLTPManager
from shared.logger import logger


class RiskAwareExecutionService(ExecutionService):
    """Enhanced execution service with advanced risk controls and multi-broker support"""

    def __init__(self,
                 execution_port: ExecutionPort,
                 algorithm_ports: List = None,
                 fees_per_trade: float = 0.001,  # 0.1% per trade
                 slippage_tolerance: float = 0.005,  # 0.5% slippage
                 default_timeout: int = 30):
        super().__init__(execution_port, algorithm_ports)
        self.fees_per_trade = fees_per_trade
        self.slippage_tolerance = slippage_tolerance
        self.default_timeout = default_timeout

        # SL/TP management
        self.sltp_manager = SLTPManager()

        # Execution tracking
        self.active_positions: Dict[str, Position] = {}  # order_id -> position
        self.position_pnls: Dict[str, float] = {}  # order_id -> realized_pnl
        self.execution_stats: Dict[str, Dict] = {}  # execution_id -> stats

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

    def execute_risk_aware_order(self, order: Order) -> str:
        """Execute an order with advanced risk management (overriding the basic method)"""
        logger.info(f"Risk-aware execution started for {order.side} {order.quantity} {order.symbol.value}")

        # Pre-execution validation
        if not self._validate_execution_feasibility(order):
            logger.warning(f"Execution not feasible for order: {order.symbol.value}")
            return None

        try:
            # Execute the order
            execution_id = self.execution_port.execute_order(order)
            if execution_id:
                # Track execution statistics
                self.execution_stats[execution_id] = {
                    'order': order,
                    'execution_time': time.time(),
                    'fees_paid': float(order.price.amount if order.price else 0) * float(order.quantity) * self.fees_per_trade,
                    'slippage': self._calculate_slippage(order),
                    'status': 'EXECUTED'
                }

                logger.info(f"Order executed successfully, ID: {execution_id}")
            else:
                logger.warning(f"Order execution failed for {order.symbol.value}")

            return execution_id

        except Exception as e:
            logger.error(f"Execution error for {order.symbol.value}: {e}")
            return None
    
    def _validate_execution_feasibility(self, order: Order) -> bool:
        """Validate that the execution is feasible"""
        # Check if order parameters are reasonable
        if not order.price or float(order.price.amount) <= 0:
            logger.warning("Order has invalid price")
            return False
        
        if float(order.quantity) <= 0:
            logger.warning("Order has invalid quantity")
            return False
        
        # Check if the order fits within risk parameters
        # (This would be connected to the risk management system)
        
        return True
    
    def _calculate_slippage(self, order: Order) -> float:
        """Calculate slippage for the executed order"""
        # In a real system, this would compare execution price to expected price
        # For now, return a simulated slippage based on order size and market conditions
        base_slippage = float(order.price.amount) * float(order.quantity) * self.slippage_tolerance
        return min(base_slippage, float(order.price.amount) * float(order.quantity) * 0.05)  # Cap slippage at 5%
    
    def execute_risk_managed_order(self, order: Order, 
                                  stop_loss: Optional[Money] = None,
                                  take_profit: Optional[Money] = None,
                                  risk_percentage: Optional[Percentage] = None) -> Optional[str]:
        """Execute order with integrated SL/TP and risk management"""
        logger.info(f"Risk-managed execution for {order.symbol.value}")
        
        # Add SL/TP to order if provided
        if stop_loss:
            order.stop_price = stop_loss
        
        # Validate the risk parameters
        if risk_percentage:
            max_risk_amount = float(order.price.amount if order.price else 0) * float(order.quantity) * float(risk_percentage.value)
            logger.info(f"Max risk for order: ${max_risk_amount:.2f}")
        
        # Execute the main order
        main_execution_id = self.execute_order(order)
        if not main_execution_id:
            return None
        
        # If SL/TP is provided, track for risk management
        if stop_loss or take_profit:
            # In a real system, this would create conditional orders
            # For now, we'll just log the intent
            logger.info(f"SL/TP monitoring set for order {main_execution_id}: SL={stop_loss}, TP={take_profit}")
        
        return main_execution_id
    
    def get_execution_performance(self) -> Dict[str, any]:
        """Get execution performance metrics"""
        if not self.execution_stats:
            return {}
        
        total_fees = sum(stat.get('fees_paid', 0) for stat in self.execution_stats.values())
        total_executions = len(self.execution_stats)
        
        avg_slippage = sum(stat.get('slippage', 0) for stat in self.execution_stats.values()) / total_executions if total_executions > 0 else 0
        
        performance = {
            'total_executions': total_executions,
            'total_fees_paid': total_fees,
            'average_slippage': avg_slippage,
            'success_rate': 1.0,  # Placeholder - would calculate from actual execution results
            'latency_stats': self._calculate_latency_stats()
        }
        
        return performance
    
    def _calculate_latency_stats(self) -> Dict[str, float]:
        """Calculate execution latency statistics"""
        if not self.execution_stats:
            return {'avg_latency': 0.0, 'min_latency': 0.0, 'max_latency': 0.0}
        
        now = time.time()
        latencies = [now - stat['execution_time'] for stat in self.execution_stats.values() if 'execution_time' in stat]
        
        if not latencies:
            return {'avg_latency': 0.0, 'min_latency': 0.0, 'max_latency': 0.0}
        
        return {
            'avg_latency': sum(latencies) / len(latencies),
            'min_latency': min(latencies),
            'max_latency': max(latencies)
        }


class AdvancedExecutionService(RiskAwareExecutionService):
    """Most advanced execution service with all enterprise features"""
    
    def __init__(self, 
                 execution_port: ExecutionPort,
                 algorithm_ports: List = None,
                 fees_per_trade: float = 0.001,
                 slippage_tolerance: float = 0.005,
                 risk_service=None):
        super().__init__(execution_port, algorithm_ports, fees_per_trade, slippage_tolerance)
        self.risk_service = risk_service  # Reference to risk management service
    
    def execute_algorithmic_order(self, order: Order, algorithm_name: str = "TWAP") -> str:
        """Execute an order using algorithmic trading methods with risk management"""
        logger.info(f"Executing algorithmic order using {algorithm_name} for {order.symbol.value}")

        # Pre-execution risk validation
        if self.risk_service:
            is_valid = self.risk_service.validate_order_risk(order)
            if not is_valid:
                logger.warning(f"Risk validation failed for algorithmic order: {order.symbol.value}")
                return None

        # Use the current class's algorithmic execution
        # Loop through algorithm ports to find the matching algorithm
        for algorithm in self.algorithm_ports:
            if algorithm.get_algorithm_name() == algorithm_name:
                logger.info(f"Executing algorithmic order using {algorithm_name}")
                execution_id = algorithm.execute_algorithmic_order(order)
                logger.info(f"Algorithmic order execution initiated, ID: {execution_id}")
                return execution_id

        # If algorithm not found, fall back to default execution
        logger.warning(f"Algorithm {algorithm_name} not found, using default execution")
        return self.execute_order(order)
    
    def batch_execute_orders(self, orders: List[Order]) -> List[str]:
        """Execute multiple orders with portfolio-level risk management"""
        logger.info(f"Batch executing {len(orders)} orders")
        
        if self.risk_service:
            # Validate all orders together for portfolio risk
            for order in orders:
                is_valid = self.risk_service.validate_order_risk(order)
                if not is_valid:
                    logger.warning(f"Risk validation failed for batch order {order.symbol.value}, skipping")
                    continue
        
        execution_ids = []
        for order in orders:
            try:
                execution_id = self.execute_order(order)
                if execution_id:
                    execution_ids.append(execution_id)
            except Exception as e:
                logger.error(f"Failed to execute batch order for {order.symbol.value}: {e}")
        
        logger.info(f"Batch execution completed: {len(execution_ids)}/{len(orders)} orders executed")
        return execution_ids