from typing import Dict, List, Optional
from shared.types import Order, OrderType, Fill, Signal
from shared.logger import logger
from datetime import datetime
from broker_gateway.order_router import OrderRouter
from risk_governor.governor import RiskGovernor
import time
import threading
import queue


class Executor:
    """Main execution engine that handles order routing, slicing, and fill management"""
    
    def __init__(self, order_router: OrderRouter, risk_governor: RiskGovernor, config: Dict = None):
        self.order_router = order_router
        self.risk_governor = risk_governor
        self.config = config or {}
        
        # Execution parameters
        self.slippage_tolerance = config.get('slippage_tolerance', 0.005)  # 0.5% slippage tolerance
        self.timeout_seconds = config.get('timeout_seconds', 30)  # 30 seconds timeout for orders
        self.retry_attempts = config.get('retry_attempts', 3)  # Number of retry attempts
        
        # Order management
        self.active_orders: Dict[str, Order] = {}
        self.order_status: Dict[str, str] = {}
        self.fill_queue = queue.Queue()
        
        # Execution algorithms
        self.execution_algorithms = {
            'market': self.execute_market_order,
            'limit': self.execute_limit_order,
            'twap': self.execute_twap_order,
            'vwap': self.execute_vwap_order
        }
        
        # Threading
        self.execution_thread = None
        self.running = False
        self.order_queue = queue.Queue()
        
    def start(self):
        """Start the execution engine"""
        self.running = True
        self.execution_thread = threading.Thread(target=self._execution_worker, daemon=True)
        self.execution_thread.start()
        logger.info("Execution engine started")
    
    def stop(self):
        """Stop the execution engine"""
        self.running = False
        if self.execution_thread:
            self.execution_thread.join(timeout=2.0)
        logger.info("Execution engine stopped")
    
    def submit_order(self, order: Order) -> Optional[str]:
        """Submit an order for execution"""
        # Validate order through risk governor
        if hasattr(order, 'symbol') and hasattr(order, 'quantity') and hasattr(order, 'price'):
            current_price = self._get_current_price(order.symbol)
            risk_check = self.risk_governor.assess_order_risk(order, current_price)
            
            if not risk_check['approved']:
                logger.warning(f"Order rejected by risk governor: {risk_check['reasons']}")
                return None
        
        # Add order to queue for execution
        self.order_queue.put(order)
        order_id = f"exec_{int(time.time() * 1000000)}"  # Generate unique order ID
        self.active_orders[order_id] = order
        self.order_status[order_id] = 'SUBMITTED'
        
        logger.debug(f"Order submitted: {order_id} for {order.symbol}, {order.side} {order.quantity}")
        return order_id
    
    def _execution_worker(self):
        """Background worker that processes orders"""
        while self.running:
            try:
                order = self.order_queue.get(timeout=1.0)
                
                # Execute the order based on type
                order_type = order.order_type.value.lower()
                if order_type in self.execution_algorithms:
                    fill = self.execution_algorithms[order_type](order)
                    if fill:
                        self.fill_queue.put(fill)
                else:
                    logger.error(f"Unknown order type: {order_type}")
                
                self.order_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in execution worker: {e}")
    
    def execute_market_order(self, order: Order) -> Optional[Fill]:
        """Execute a market order"""
        try:
            # Get current market price
            current_price = self._get_current_price(order.symbol)
            if current_price is None:
                logger.error(f"Could not get current price for {order.symbol}")
                return None
            
            # Account for slippage in the fill price
            slippage = self._calculate_slippage(order.quantity, order.symbol)
            if order.side == 'BUY':
                fill_price = current_price * (1 + slippage)
            else:
                fill_price = current_price * (1 - slippage)
            
            # Submit order to broker
            order_id = self.order_router.route_order(order)
            if not order_id:
                logger.error(f"Failed to route market order for {order.symbol}")
                return None
            
            # Create fill object
            fill = Fill(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=fill_price,
                timestamp=datetime.now(),
                order_id=order_id
            )
            
            logger.debug(f"Market order filled: {order.symbol}, {order.side} {order.quantity} @ {fill_price}")
            return fill
            
        except Exception as e:
            logger.error(f"Error executing market order: {e}")
            return None
    
    def execute_limit_order(self, order: Order) -> Optional[Fill]:
        """Execute a limit order"""
        if order.price is None:
            logger.error("Limit order must have a price specified")
            return None
        
        try:
            # Submit limit order to broker
            order_id = self.order_router.route_order(order)
            if not order_id:
                logger.error(f"Failed to route limit order for {order.symbol}")
                return None
            
            # For limit orders, we need to wait for fills or cancel if not filled in time
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < self.timeout_seconds:
                # Check if the order status is filled
                status = self.order_router.get_order_status(order_id)
                if status and status.get('status') == 'FILLED':
                    # Get fill details
                    current_price = order.price  # Use the limit price for the fill
                    fill = Fill(
                        symbol=order.symbol,
                        side=order.side,
                        quantity=order.quantity,
                        price=current_price,
                        timestamp=datetime.now(),
                        order_id=order_id
                    )
                    logger.debug(f"Limit order filled: {order.symbol}, {order.side} {order.quantity} @ {current_price}")
                    return fill
                time.sleep(0.1)  # Wait a bit before checking again
            
            # Order not filled within timeout, cancel it
            logger.info(f"Limit order not filled within {self.timeout_seconds}s, cancelling: {order_id}")
            self.order_router.cancel_order(order_id)
            return None
            
        except Exception as e:
            logger.error(f"Error executing limit order: {e}")
            return None
    
    def execute_twap_order(self, order: Order) -> Optional[Fill]:
        """Execute a TWAP (Time-Weighted Average Price) order"""
        # TWAP example implementation - divide large orders into smaller pieces over time
        total_quantity = order.quantity
        time_interval = self.config.get('twap_interval', 300)  # 5 minutes default
        slice_count = self.config.get('twap_slices', 10)  # 10 slices default
        slice_quantity = total_quantity / slice_count
        slice_time = time_interval / slice_count
        
        all_fills = []
        
        # Submit slices sequentially
        for i in range(slice_count):
            if not self.running:
                break
                
            # Create slice order
            slice_order = Order(
                symbol=order.symbol,
                side=order.side,
                quantity=slice_quantity,
                order_type=OrderType.MARKET,
                time_in_force=order.time_in_force
            )
            
            fill = self.execute_market_order(slice_order)
            if fill:
                all_fills.append(fill)
            
            # Wait before next slice
            time.sleep(slice_time)
        
        # Return the average fill price as a single fill
        if all_fills:
            avg_price = sum(f.price * f.quantity for f in all_fills) / sum(f.quantity for f in all_fills)
            total_quantity = sum(f.quantity for f in all_fills)
            
            return Fill(
                symbol=all_fills[0].symbol,
                side=all_fills[0].side,
                quantity=total_quantity,
                price=avg_price,
                timestamp=datetime.now(),
                order_id=all_fills[0].order_id
            )
        
        return None
    
    def execute_vwap_order(self, order: Order) -> Optional[Fill]:
        """Execute a VWAP (Volume-Weighted Average Price) order"""
        # VWAP example - adapt to market volume
        # In a real implementation, this would monitor volume patterns throughout the day
        # and execute orders proportionally to volume
        return self.execute_market_order(order)  # Simplified implementation
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol"""
        try:
            # Use the price router to get current price
            # We'll assume the price_router is accessible through the order_router
            # In a complete implementation this would be a separate component
            from broker_gateway.price_router import PriceRouter  # Assuming this exists
            # This is a simplified version - in practice you'd have access to real-time prices
            return 100.0  # Placeholder value
        except:
            return None
    
    def _calculate_slippage(self, quantity: float, symbol: str) -> float:
        """Calculate expected slippage based on order size and market conditions"""
        # Simplified slippage model - in reality this would be more complex
        # Factors: order size, market liquidity, volatility
        base_slippage = 0.001  # 0.1% base slippage
        
        # Increase slippage for larger orders
        size_factor = min(10.0, quantity / 1000.0)  # Adjust based on your market scale
        
        # Get market conditions if available
        market_volatility = self.config.get('market_volatility', 1.0)
        
        total_slippage = base_slippage * size_factor * market_volatility
        return min(self.slippage_tolerance, total_slippage)
    
    def get_active_orders(self) -> Dict[str, Order]:
        """Get all active orders"""
        return self.active_orders.copy()
    
    def get_fill_queue(self) -> queue.Queue:
        """Get the fill queue for processing fills"""
        return self.fill_queue
    
    def get_execution_metrics(self) -> Dict:
        """Get execution performance metrics"""
        return {
            'active_orders_count': len(self.active_orders),
            'order_status_counts': {
                status: sum(1 for s in self.order_status.values() if s == status)
                for status in set(self.order_status.values())
            }
        }
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order"""
        if order_id in self.active_orders:
            try:
                success = self.order_router.cancel_order(order_id)
                if success:
                    self.order_status[order_id] = 'CANCELLED'
                    logger.info(f"Order {order_id} cancelled successfully")
                return success
            except Exception as e:
                logger.error(f"Error cancelling order {order_id}: {e}")
                return False
        else:
            logger.warning(f"Attempted to cancel non-existent order: {order_id}")
            return False