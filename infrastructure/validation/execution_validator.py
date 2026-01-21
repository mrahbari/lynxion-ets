"""
Execution validation system to verify that orders are placed and filled as expected.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading
import time
from enum import Enum

class ExecutionStatus(Enum):
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    TIMEOUT = "timeout"

class ExecutionValidator:
    """Validates that orders are executed as expected."""
    
    def __init__(self, validation_timeout: int = 30):  # 30 seconds timeout
        self.validation_timeout = validation_timeout
        self.pending_orders: Dict[str, Dict] = {}  # order_id -> validation_info
        self.validation_results: Dict[str, Dict] = {}  # order_id -> result
        self.lock = threading.Lock()
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_pending_orders, daemon=True)
        self.monitor_thread.start()
        
    def register_order_intent(self, order_id: str, expected_fill_price: float, 
                            expected_quantity: float, side: str, symbol: str):
        """Register an order intent for validation."""
        with self.lock:
            self.pending_orders[order_id] = {
                'expected_fill_price': expected_fill_price,
                'expected_quantity': expected_quantity,
                'side': side,
                'symbol': symbol,
                'timestamp': datetime.now(),
                'status': ExecutionStatus.PENDING
            }
            
    def update_order_status(self, order_id: str, status: ExecutionStatus, 
                          actual_fill_price: float = None, actual_quantity: float = None):
        """Update the status of an order."""
        with self.lock:
            if order_id in self.pending_orders:
                order_info = self.pending_orders[order_id]
                order_info['status'] = status
                order_info['actual_fill_price'] = actual_fill_price
                order_info['actual_quantity'] = actual_quantity
                order_info['updated_timestamp'] = datetime.now()
                
                # Move to results if final status
                if status in [ExecutionStatus.FILLED, ExecutionStatus.CANCELLED, 
                             ExecutionStatus.REJECTED, ExecutionStatus.TIMEOUT]:
                    self.validation_results[order_id] = order_info.copy()
                    del self.pending_orders[order_id]
                    
    def validate_execution(self, order_id: str) -> Dict:
        """Validate execution and return validation report."""
        with self.lock:
            if order_id in self.validation_results:
                result = self.validation_results[order_id]
                return self._create_validation_report(result)
            elif order_id in self.pending_orders:
                # Still pending, return current status
                return {
                    'order_id': order_id,
                    'status': self.pending_orders[order_id]['status'].value,
                    'validated': False,
                    'message': 'Order still pending validation'
                }
            else:
                return {
                    'order_id': order_id,
                    'status': 'unknown',
                    'validated': False,
                    'message': 'Order not found in validation system'
                }
                
    def _create_validation_report(self, result: Dict) -> Dict:
        """Create a detailed validation report."""
        expected_qty = result.get('expected_quantity', 0)
        actual_qty = result.get('actual_quantity', 0)
        expected_price = result.get('expected_fill_price', 0)
        actual_price = result.get('actual_fill_price', 0)
        
        # Calculate validation metrics
        qty_filled_pct = (actual_qty / expected_qty * 100) if expected_qty > 0 else 0
        price_slippage_pct = ((actual_price - expected_price) / expected_price * 100) if expected_price > 0 else 0
        
        # Determine validation outcome
        is_valid = (
            result['status'] == ExecutionStatus.FILLED and
            qty_filled_pct >= 95 and  # At least 95% filled
            abs(price_slippage_pct) <= 0.5  # Less than 0.5% slippage
        )
        
        return {
            'order_id': result.get('order_id'),
            'status': result['status'].value,
            'validated': is_valid,
            'expected_quantity': expected_qty,
            'actual_quantity': actual_qty,
            'quantity_filled_percentage': qty_filled_pct,
            'expected_fill_price': expected_price,
            'actual_fill_price': actual_price,
            'price_slippage_percentage': price_slippage_pct,
            'validation_passed': is_valid,
            'message': 'Execution validated successfully' if is_valid else 'Execution validation failed'
        }
        
    def _monitor_pending_orders(self):
        """Monitor pending orders for timeout."""
        while self.monitoring_active:
            time.sleep(1)  # Check every second
            
            with self.lock:
                now = datetime.now()
                orders_to_timeout = []
                
                for order_id, order_info in self.pending_orders.items():
                    if (now - order_info['timestamp']).seconds > self.validation_timeout:
                        orders_to_timeout.append(order_id)
                        
                for order_id in orders_to_timeout:
                    self.pending_orders[order_id]['status'] = ExecutionStatus.TIMEOUT
                    self.validation_results[order_id] = self.pending_orders[order_id].copy()
                    del self.pending_orders[order_id]
                    
    def shutdown(self):
        """Shutdown the validator."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)

# Global execution validator instance
execution_validator = ExecutionValidator()