"""
Advanced execution algorithms for the enterprise hedge fund trading system.
Implements sophisticated order execution strategies like Iceberg, PEG, TWAP, VWAP.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from enum import Enum
from shared.logger import logger
from shared.metrics import metrics_collector, time_operation
from domain.entities import Order, Symbol
from domain.value_objects import Money


class ExecutionAlgorithmType(Enum):
    """Types of execution algorithms"""
    TWAP = "twap"
    VWAP = "vwap"
    ICEBERG = "iceberg"
    PEG = "peg"
    MARKET = "market"
    LIMIT = "limit"


class ExecutionInstruction:
    """Instruction for breaking down a large order into smaller parts"""
    def __init__(self, 
                 symbol: Symbol,
                 total_quantity: float,
                 side: str,  # 'BUY' or 'SELL'
                 order_type: str,
                 timestamp: datetime,
                 child_orders: List[Dict[str, Any]] = None):
        self.symbol = symbol
        self.total_quantity = total_quantity
        self.side = side
        self.order_type = order_type
        self.timestamp = timestamp
        self.child_orders = child_orders or []
        self.executed_quantity = 0.0
        self.status = 'PENDING'  # PENDING, PARTIAL, COMPLETED, CANCELLED


class BaseExecutionAlgorithm:
    """Base class for execution algorithms"""
    
    def __init__(self, name: str):
        self.name = name
    
    def generate_execution_instructions(self, 
                                      order: Order, 
                                      market_data: Dict[str, Any],
                                      execution_params: Dict[str, Any]) -> ExecutionInstruction:
        """Generate execution instructions for an order"""
        raise NotImplementedError


class TWAPExecutionAlgorithm(BaseExecutionAlgorithm):
    """Time Weighted Average Price execution algorithm"""
    
    def __init__(self):
        super().__init__("TWAP")
    
    def generate_execution_instructions(self, 
                                      order: Order, 
                                      market_data: Dict[str, Any],
                                      execution_params: Dict[str, Any]) -> ExecutionInstruction:
        """Generate TWAP execution instructions"""
        start_time = execution_params.get('start_time', datetime.now())
        end_time = execution_params.get('end_time', start_time + timedelta(hours=1))
        time_window = (end_time - start_time).total_seconds()
        
        # Calculate time intervals
        interval_seconds = execution_params.get('interval_seconds', 300)  # 5 minutes default
        num_intervals = max(1, int(time_window / interval_seconds))
        
        # Calculate quantity per interval
        total_quantity = float(order.quantity) if hasattr(order, 'quantity') else 1.0
        quantity_per_interval = total_quantity / num_intervals
        
        # Generate child orders
        child_orders = []
        current_time = start_time
        
        for i in range(num_intervals):
            child_order = {
                'symbol': order.symbol,
                'quantity': quantity_per_interval,
                'side': order.side if hasattr(order, 'side') else 'BUY',
                'type': order.order_type if hasattr(order, 'order_type') else 'MARKET',
                'timestamp': current_time,
                'part_number': i + 1,
                'total_parts': num_intervals
            }
            child_orders.append(child_order)
            current_time += timedelta(seconds=interval_seconds)
        
        # Add final order to account for rounding
        executed_so_far = quantity_per_interval * num_intervals
        remaining = total_quantity - executed_so_far
        if remaining > 0.0001:  # Significant remainder
            child_orders.append({
                'symbol': order.symbol,
                'quantity': remaining,
                'side': order.side if hasattr(order, 'side') else 'BUY',
                'type': order.order_type if hasattr(order, 'order_type') else 'MARKET',
                'timestamp': current_time,
                'part_number': num_intervals + 1,
                'total_parts': num_intervals + 1
            })
        
        return ExecutionInstruction(
            symbol=order.symbol,
            total_quantity=total_quantity,
            side=order.side if hasattr(order, 'side') else 'BUY',
            order_type=order.order_type if hasattr(order, 'order_type') else 'MARKET',
            timestamp=datetime.now(),
            child_orders=child_orders
        )


class VWAPExecutionAlgorithm(BaseExecutionAlgorithm):
    """Volume Weighted Average Price execution algorithm"""
    
    def __init__(self):
        super().__init__("VWAP")
    
    def generate_execution_instructions(self, 
                                      order: Order, 
                                      market_data: Dict[str, Any],
                                      execution_params: Dict[str, Any]) -> ExecutionInstruction:
        """Generate VWAP execution instructions using historical volume data"""
        start_time = execution_params.get('start_time', datetime.now())
        end_time = execution_params.get('end_time', start_time + timedelta(hours=1))
        
        # Get volume profile (in a real system, this would come from historical data)
        # For now, we'll simulate a typical volume profile
        volume_profile = self._get_volume_profile(start_time, end_time, market_data)
        
        total_quantity = float(order.quantity) if hasattr(order, 'quantity') else 1.0
        total_volume = sum(volume_profile.values())
        
        if total_volume == 0:
            # Fallback to TWAP if no volume data
            logger.warning(f"No volume data available for {order.symbol.value}, falling back to TWAP logic")
            # Use simple time-based distribution
            twap = TWAPExecutionAlgorithm()
            return twap.generate_execution_instructions(order, market_data, execution_params)
        
        # Generate orders based on volume profile
        child_orders = []
        for time_slot, volume_ratio in volume_profile.items():
            quantity = total_quantity * (volume_ratio / total_volume)
            if quantity > 0.0001:  # Only create order if significant quantity
                child_orders.append({
                    'symbol': order.symbol,
                    'quantity': quantity,
                    'side': order.side if hasattr(order, 'side') else 'BUY',
                    'type': order.order_type if hasattr(order, 'order_type') else 'MARKET',
                    'timestamp': time_slot,
                    'volume_weight': volume_ratio / total_volume
                })
        
        return ExecutionInstruction(
            symbol=order.symbol,
            total_quantity=total_quantity,
            side=order.side if hasattr(order, 'side') else 'BUY',
            order_type=order.order_type if hasattr(order, 'order_type') else 'MARKET',
            timestamp=datetime.now(),
            child_orders=child_orders
        )
    
    def _get_volume_profile(self, start_time: datetime, end_time: datetime, 
                           market_data: Dict[str, Any]) -> Dict[datetime, float]:
        """Get volume profile for the time period (simplified implementation)"""
        # In a real implementation, this would query historical volume data
        # For now, create a mock volume profile
        profile = {}
        current_time = start_time
        
        # Create 5-minute intervals
        interval = timedelta(minutes=5)
        while current_time < end_time:
            # Simulate volume pattern (higher volume at beginning and end of session)
            hour = current_time.hour
            minute = current_time.minute
            
            # Typical trading session volume pattern (simplified)
            if 9 <= hour <= 11 or 14 <= hour <= 15:
                volume_weight = 1.2  # Higher volume in active hours
            elif 11 < hour < 14:
                volume_weight = 0.8  # Lower volume during lunch
            else:
                volume_weight = 0.5  # Lower volume at edges
            
            profile[current_time] = volume_weight
            current_time += interval
        
        return profile


class IcebergExecutionAlgorithm(BaseExecutionAlgorithm):
    """Iceberg execution algorithm - shows only a portion of the total order"""
    
    def __init__(self):
        super().__init__("Iceberg")
    
    def generate_execution_instructions(self, 
                                      order: Order, 
                                      market_data: Dict[str, Any],
                                      execution_params: Dict[str, Any]) -> ExecutionInstruction:
        """Generate Iceberg execution instructions"""
        total_quantity = float(order.quantity) if hasattr(order, 'quantity') else 1.0
        display_quantity = execution_params.get('display_quantity', min(total_quantity * 0.1, 100.0))  # 10% or 100, whichever is smaller
        price_offset = execution_params.get('price_offset', 0.001)  # 0.1% from market price
        
        # Generate initial visible order
        child_orders = [{
            'symbol': order.symbol,
            'quantity': min(display_quantity, total_quantity),
            'side': order.side if hasattr(order, 'side') else 'BUY',
            'type': 'LIMIT',  # Iceberg orders are typically limit orders
            'timestamp': datetime.now(),
            'display_quantity': display_quantity,
            'price_offset': price_offset,
            'order_type': 'ICEBERG'
        }]
        
        remaining_quantity = total_quantity - min(display_quantity, total_quantity)
        executed_quantity = min(display_quantity, total_quantity)
        
        # Additional orders will be generated dynamically as the displayed quantity is filled
        # For now, we create placeholder orders
        if remaining_quantity > 0:
            # In a real implementation, these would be created dynamically as fills happen
            pass
        
        return ExecutionInstruction(
            symbol=order.symbol,
            total_quantity=total_quantity,
            side=order.side if hasattr(order, 'side') else 'BUY',
            order_type='ICEBERG',
            timestamp=datetime.now(),
            child_orders=child_orders
        )


class PEGExecutionAlgorithm(BaseExecutionAlgorithm):
    """PEG (Percentage of Volume) execution algorithm"""
    
    def __init__(self):
        super().__init__("PEG")
    
    def generate_execution_instructions(self, 
                                      order: Order, 
                                      market_data: Dict[str, Any],
                                      execution_params: Dict[str, Any]) -> ExecutionInstruction:
        """Generate PEG execution instructions"""
        total_quantity = float(order.quantity) if hasattr(order, 'quantity') else 1.0
        peg_ratio = execution_params.get('peg_ratio', 0.1)  # 10% of market volume
        max_order_size = execution_params.get('max_order_size', 1000.0)  # Max individual order size
        
        # Get market volume (in real system, this would come from real-time market data)
        market_volume = market_data.get('volume', 10000.0)  # Default to 10000 if not available
        target_volume = market_volume * peg_ratio
        
        # Calculate how many orders to split into
        order_size = min(target_volume, max_order_size)
        num_orders = max(1, int(total_quantity / order_size))
        actual_order_size = total_quantity / num_orders
        
        child_orders = []
        for i in range(num_orders):
            child_orders.append({
                'symbol': order.symbol,
                'quantity': actual_order_size,
                'side': order.side if hasattr(order, 'side') else 'BUY',
                'type': 'MARKET',  # PEG typically uses market orders
                'timestamp': datetime.now(),  # Would be dynamic in real implementation
                'peg_ratio': peg_ratio,
                'target_volume': target_volume
            })
        
        return ExecutionInstruction(
            symbol=order.symbol,
            total_quantity=total_quantity,
            side=order.side if hasattr(order, 'side') else 'BUY',
            order_type='PEG',
            timestamp=datetime.now(),
            child_orders=child_orders
        )


class ExecutionAlgorithmManager:
    """Manager for all execution algorithms"""
    
    def __init__(self):
        self.algorithms = {
            ExecutionAlgorithmType.TWAP.value: TWAPExecutionAlgorithm(),
            ExecutionAlgorithmType.VWAP.value: VWAPExecutionAlgorithm(),
            ExecutionAlgorithmType.ICEBERG.value: IcebergExecutionAlgorithm(),
            ExecutionAlgorithmType.PEG.value: PEGExecutionAlgorithm(),
        }
    
    def get_algorithm(self, algorithm_type: ExecutionAlgorithmType) -> Optional[BaseExecutionAlgorithm]:
        """Get an execution algorithm by type"""
        return self.algorithms.get(algorithm_type.value)
    
    def execute_order_with_algorithm(self, 
                                   order: Order, 
                                   algorithm_type: ExecutionAlgorithmType,
                                   market_data: Dict[str, Any],
                                   execution_params: Dict[str, Any]) -> ExecutionInstruction:
        """Execute an order using the specified algorithm"""
        algorithm = self.get_algorithm(algorithm_type)
        if not algorithm:
            raise ValueError(f"Unknown execution algorithm: {algorithm_type}")
        
        logger.info(f"Executing order with {algorithm_type.value} algorithm", 
                   symbol=order.symbol.value, 
                   quantity=str(order.quantity) if hasattr(order, 'quantity') else 'unknown',
                   algorithm=algorithm_type.value)
        
        try:
            instructions = algorithm.generate_execution_instructions(order, market_data, execution_params)
            
            # Record metrics
            metrics_collector.record_performance_metric(
                f"execution_algorithm_{algorithm_type.value}", 
                0.001,  # Placeholder time
                {'symbol': order.symbol.value, 'algorithm': algorithm_type.value}
            )
            
            logger.info(f"Generated {len(instructions.child_orders)} child orders for execution",
                       parent_order_id=getattr(order, 'order_id', 'unknown'),
                       child_orders_count=len(instructions.child_orders))
            
            return instructions
        except Exception as e:
            logger.error(f"Error in {algorithm_type.value} execution algorithm: {str(e)}",
                        symbol=order.symbol.value, 
                        algorithm=algorithm_type.value)
            # Fallback to market order
            return self._create_market_order_fallback(order)
    
    def _create_market_order_fallback(self, order: Order) -> ExecutionInstruction:
        """Create a fallback market order if algorithm fails"""
        logger.warning("Falling back to market order due to algorithm failure", 
                      symbol=order.symbol.value)
        
        child_orders = [{
            'symbol': order.symbol,
            'quantity': float(order.quantity) if hasattr(order, 'quantity') else 1.0,
            'side': order.side if hasattr(order, 'side') else 'BUY',
            'type': 'MARKET',
            'timestamp': datetime.now(),
            'fallback': True
        }]
        
        return ExecutionInstruction(
            symbol=order.symbol,
            total_quantity=float(order.quantity) if hasattr(order, 'quantity') else 1.0,
            side=order.side if hasattr(order, 'side') else 'BUY',
            order_type='MARKET',
            timestamp=datetime.now(),
            child_orders=child_orders
        )


# Global execution algorithm manager instance
execution_algorithm_manager = ExecutionAlgorithmManager()