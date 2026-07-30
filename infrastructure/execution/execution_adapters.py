"""
Infrastructure implementations of execution services.
"""
from typing import List, Optional, Dict, Any
from domain.entities import Order, Fill
from domain.value_objects import Symbol
from domain.ports.execution_ports import ExecutionPort, ExecutionAlgorithmPort
from shared.logger import logger
from datetime import datetime


class BaseExecutionAdapter(ExecutionPort):
    """Base class for execution adapters"""
    
    def __init__(self, name: str):
        self.name = name
    
    def execute_order(self, order: Order) -> str:
        """Execute an order"""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        raise NotImplementedError
    
    def get_execution_status(self, execution_id: str) -> str:
        """Get execution status"""
        raise NotImplementedError


class DirectExecutionAdapter(BaseExecutionAdapter):
    """Infrastructure implementation of direct execution"""
    
    def __init__(self):
        super().__init__("DirectExecution")
        self.execution_history = {}
        self.order_id_counter = 1000
    
    def execute_order(self, order: Order) -> str:
        """Execute an order directly through the broker via LiveExecutionGuard authorization"""
        from infrastructure.adapters.broker_data_adapters import MockBrokerAdapter
        from shared.live_execution_guard import live_execution_guard
        broker = MockBrokerAdapter()
        
        guard_decision, order_id = live_execution_guard.authorize_and_send(
            broker_name="mock", settings=None, order=order,
            send_fn=lambda: broker.place_order(order)
        )
        if not guard_decision.allowed or not order_id:
            logger.error(f"🛑 DIRECT EXECUTION BLOCKED: Order for {order.symbol.value} rejected by Risk Gate: {guard_decision.reason}")
            return ""
        
        # Record in execution history
        self.execution_history[order_id] = {
            'order': order,
            'status': 'PENDING',
            'timestamp': datetime.now()
        }
        
        logger.info(f"Direct execution placed order: {order_id} for {order.symbol.value}")
        return order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        from infrastructure.adapters.broker_data_adapters import MockBrokerAdapter
        broker = MockBrokerAdapter()
        
        # Cancel the order
        success = broker.cancel_order(order_id, Symbol("BTCUSDT"))  # Placeholder symbol
        
        if success:
            if order_id in self.execution_history:
                self.execution_history[order_id]['status'] = 'CANCELED'
        
        logger.info(f"Direct execution cancel order {order_id}: {success}")
        return success
    
    def get_execution_status(self, execution_id: str) -> str:
        """Get execution status"""
        from infrastructure.adapters.broker_data_adapters import MockBrokerAdapter
        broker = MockBrokerAdapter()
        
        status = broker.get_order_status(execution_id, Symbol("BTCUSDT"))  # Placeholder symbol
        
        logger.info(f"Direct execution status for {execution_id}: {status}")
        return status


class TWAPExecutionAdapter(ExecutionAlgorithmPort):
    """Infrastructure implementation of TWAP execution algorithm"""
    
    def __init__(self):
        self.name = "TWAP"
        self.time_window = 60 * 5  # 5 minutes in seconds
        self.slippage_tolerance = 0.005  # 0.5% slippage tolerance
    
    def execute_algorithmic_order(self, order: Order) -> str:
        """Execute an order using TWAP algorithm via LiveExecutionGuard authorization"""
        logger.info(f"TWAP algorithm executing order for {order.symbol.value}")
        from infrastructure.adapters.broker_data_adapters import MockBrokerAdapter
        from shared.live_execution_guard import live_execution_guard
        broker = MockBrokerAdapter()
        
        guard_decision, order_id = live_execution_guard.authorize_and_send(
            broker_name="mock", settings=None, order=order,
            send_fn=lambda: broker.place_order(order)
        )
        if not guard_decision.allowed or not order_id:
            logger.error(f"🛑 TWAP EXECUTION BLOCKED: Order for {order.symbol.value} rejected by Risk Gate: {guard_decision.reason}")
            return ""

        logger.info(f"TWAP execution placed order: {order_id}")
        return order_id
    
    def get_algorithm_name(self) -> str:
        return self.name


class VWAPExecutionAdapter(ExecutionAlgorithmPort):
    """Infrastructure implementation of VWAP execution algorithm"""
    
    def __init__(self):
        self.name = "VWAP"
        self.lookback_period = 20  # periods back to calculate VWAP
    
    def execute_algorithmic_order(self, order: Order) -> str:
        """Execute an order using VWAP algorithm via LiveExecutionGuard authorization"""
        logger.info(f"VWAP algorithm executing order for {order.symbol.value}")
        from infrastructure.adapters.broker_data_adapters import MockBrokerAdapter
        from shared.live_execution_guard import live_execution_guard
        broker = MockBrokerAdapter()
        
        guard_decision, order_id = live_execution_guard.authorize_and_send(
            broker_name="mock", settings=None, order=order,
            send_fn=lambda: broker.place_order(order)
        )
        if not guard_decision.allowed or not order_id:
            logger.error(f"🛑 VWAP EXECUTION BLOCKED: Order for {order.symbol.value} rejected by Risk Gate: {guard_decision.reason}")
            return ""

        logger.info(f"VWAP execution placed order: {order_id}")
        return order_id
    
    def get_algorithm_name(self) -> str:
        return self.name


class SmartRouterExecutionAdapter(ExecutionPort):
    """Infrastructure implementation of smart order routing"""
    
    def __init__(self):
        self.name = "SmartRouter"
        self.brokers = ["Binance", "BingX", "MEXC", "Phemex"]  # Simulated brokers
        self.preferred_broker = "Binance"
    
    def execute_order(self, order: Order) -> str:
        """Execute an order using smart routing via LiveExecutionGuard authorization"""
        logger.info(f"Smart router executing order for {order.symbol.value}")
        from infrastructure.adapters.broker_data_adapters import MockBrokerAdapter
        from shared.live_execution_guard import live_execution_guard
        broker = MockBrokerAdapter()
        
        guard_decision, order_id = live_execution_guard.authorize_and_send(
            broker_name="mock", settings=None, order=order,
            send_fn=lambda: broker.place_order(order)
        )
        if not guard_decision.allowed or not order_id:
            logger.error(f"🛑 SMART ROUTER EXECUTION BLOCKED: Order for {order.symbol.value} rejected by Risk Gate: {guard_decision.reason}")
            return ""

        logger.info(f"Smart router placed order: {order_id} via {self.preferred_broker}")
        return order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on the broker where it was placed"""
        from infrastructure.adapters.broker_data_adapters import MockBrokerAdapter
        broker = MockBrokerAdapter()
        
        # This would need to know which broker has the order
        success = broker.cancel_order(order_id, Symbol("BTCUSDT"))  # Placeholder
        logger.info(f"Smart router cancel order {order_id}: {success}")
        return success
    
    def get_execution_status(self, execution_id: str) -> str:
        """Get execution status from the relevant broker"""
        from infrastructure.adapters.broker_data_adapters import MockBrokerAdapter
        broker = MockBrokerAdapter()
        
        status = broker.get_order_status(execution_id, Symbol("BTCUSDT"))  # Placeholder
        logger.info(f"Smart router status for {execution_id}: {status}")
        return status