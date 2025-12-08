from typing import Dict, List, Optional
from shared.types import Order, OrderType, Fill, OrderSide
from shared.logger import logger
from datetime import datetime, timedelta
import time
import threading


class TWAPExecution:
    """Time-Weighted Average Price execution algorithm"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # TWAP parameters
        self.default_window_minutes = config.get('twap_window_minutes', 30)  # 30 minute default window
        self.default_slices = config.get('twap_slices', 10)  # 10 slices by default
        self.min_slice_time = config.get('twap_min_slice_time', 10)  # Minimum 10 seconds between slices
        self.max_slice_size = config.get('twap_max_slice_size', 0.1)  # Max 10% of position in one slice as a safety measure
        self.price_improvement_enabled = config.get('twap_price_improvement', True)
        
        # State tracking
        self.active_twaps = {}
        self.execution_stats = {}
        
        # Market data
        self.current_prices = {}
        
    def execute_twap_order(self, 
                          symbol: str, 
                          total_quantity: float, 
                          side: OrderSide, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          num_slices: Optional[int] = None,
                          slice_interval: Optional[int] = None) -> List[Fill]:
        """Execute a TWAP order by breaking it into time-weighted slices"""
        
        # Set defaults if not provided
        if start_time is None:
            start_time = datetime.now()
        if end_time is None:
            end_time = start_time + timedelta(minutes=self.default_window_minutes)
        if num_slices is None:
            num_slices = self.default_slices
        if slice_interval is None:
            total_seconds = (end_time - start_time).total_seconds()
            slice_interval = max(self.min_slice_time, total_seconds / num_slices)
        
        # Calculate slice size
        slice_quantity = total_quantity / num_slices
        
        # Validate slice size against safety limits
        position_size = self.config.get('account_balance', 10000) * self.config.get('position_size', 0.01)  # 1% default position size
        max_slice = position_size * self.max_slice_size
        if slice_quantity > max_slice:
            # Adjust number of slices to meet safety limit
            num_slices = max(1, int(total_quantity / max_slice))
            slice_quantity = total_quantity / num_slices
            slice_interval = max(self.min_slice_time, total_seconds / num_slices)
        
        all_fills = []
        order_id = f"twap_{int(time.time() * 1000000)}"
        
        # Create TWAP execution record
        self.active_twaps[order_id] = {
            'symbol': symbol,
            'total_quantity': total_quantity,
            'side': side,
            'start_time': start_time,
            'end_time': end_time,
            'num_slices': num_slices,
            'slice_quantity': slice_quantity,
            'slice_interval': slice_interval,
            'executed_quantity': 0,
            'status': 'ACTIVE'
        }
        
        logger.info(f"Starting TWAP execution: {order_id} for {total_quantity} {symbol}, "
                   f"{num_slices} slices over {(end_time - start_time).total_seconds()/60:.1f} minutes")
        
        try:
            # Execute each slice
            for i in range(num_slices):
                if datetime.now() > end_time:
                    logger.warning(f"TWAP execution for {order_id} exceeded end time, stopping")
                    break
                
                # Calculate the next execution time
                next_time = start_time + timedelta(seconds=i * slice_interval)
                time_to_wait = (next_time - datetime.now()).total_seconds()
                
                if time_to_wait > 0:
                    time.sleep(min(time_to_wait, 1.0))  # Wake up periodically to check for stop conditions
                    if datetime.now() < next_time:
                        time.sleep(time_to_wait)  # Then sleep the remaining time
                
                # Execute a slice
                slice_order = Order(
                    symbol=symbol,
                    side=side,
                    quantity=slice_quantity,
                    order_type=OrderType.MARKET
                )
                
                fill = self._execute_slice(slice_order, order_id, i+1, num_slices)
                if fill:
                    all_fills.append(fill)
                    self.active_twaps[order_id]['executed_quantity'] += fill.quantity
                    logger.debug(f"TWAP slice {i+1}/{num_slices} executed: {fill.quantity} @ {fill.price}")
                
                # Brief pause to avoid flooding
                time.sleep(0.1)
            
            # Update execution status
            self.active_twaps[order_id]['status'] = 'COMPLETED'
            self.active_twaps[order_id]['completed_time'] = datetime.now()
            
            logger.info(f"TWAP execution completed: {order_id}, "
                       f"executed {self.active_twaps[order_id]['executed_quantity']}/{total_quantity}")
            
        except Exception as e:
            logger.error(f"Error in TWAP execution {order_id}: {e}")
            self.active_twaps[order_id]['status'] = 'ERROR'
            self.active_twaps[order_id]['error'] = str(e)
        finally:
            # Record execution stats
            self._record_execution_stats(order_id, all_fills)
        
        return all_fills
    
    def _execute_slice(self, order: Order, parent_order_id: str, slice_num: int, total_slices: int) -> Optional[Fill]:
        """Execute a single slice of the TWAP order"""
        try:
            # Get current market data for price improvement opportunity
            current_price = self.current_prices.get(order.symbol)
            if current_price is None:
                # Fallback to market execution
                current_price = self._get_current_price(order.symbol)
            
            if current_price is None:
                logger.error(f"Could not get current price for {order.symbol}")
                return None
            
            # If price improvement is enabled, try to get better prices with limit orders
            if self.price_improvement_enabled:
                limit_price = self._calculate_limit_price(order.side, current_price, order.symbol)
                
                # Submit limit order with timeout
                fill = self._submit_limit_slice(order, limit_price, timeout=10)
                
                # If limit order didn't fill, fallback to market
                if not fill:
                    logger.debug(f"TWAP slice {slice_num}/{total_slices} limit order not filled, using market")
                    fill = self._submit_market_slice(order)
            else:
                fill = self._submit_market_slice(order)
            
            return fill
            
        except Exception as e:
            logger.error(f"Error executing TWAP slice {slice_num}: {e}")
            return None
    
    def _submit_market_slice(self, order: Order) -> Optional[Fill]:
        """Submit a market order slice"""
        # This would connect to real market data/order routing system in production
        # For now, we'll simulate market execution with realistic pricing
        current_price = self._get_current_price(order.symbol)
        if current_price is None:
            return None
        
        # Simulate realistic market execution with some slippage
        slippage = self._calculate_execution_slippage(order.quantity, order.symbol, order.side)
        if order.side == OrderSide.BUY:
            executed_price = current_price * (1 + slippage)
        else:
            executed_price = current_price * (1 - slippage)
        
        # Simulate fill execution
        fill = Fill(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=executed_price,
            timestamp=datetime.now(),
            order_id=f"slice_{int(time.time() * 1000000)}"
        )
        
        return fill
    
    def _submit_limit_slice(self, order: Order, limit_price: float, timeout: int = 10) -> Optional[Fill]:
        """Submit a limit order slice with timeout"""
        # In a real system, this would submit to the exchange
        # For simulation, we'll check if the limit price would be hit
        
        current_price = self._get_current_price(order.symbol)
        if current_price is None:
            return None
        
        # Check if limit order would be filled based on current price
        should_fill = False
        if order.side == OrderSide.BUY and current_price <= limit_price:
            should_fill = True
        elif order.side == OrderSide.SELL and current_price >= limit_price:
            should_fill = True
        
        if should_fill:
            fill = Fill(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=limit_price,
                timestamp=datetime.now(),
                order_id=f"limit_slice_{int(time.time() * 1000000)}"
            )
            return fill
        
        # Simulate that the order might get filled within the timeout
        # For this simple implementation, we'll just return None
        # A real implementation would monitor the order until timeout
        return None
    
    def _calculate_limit_price(self, side: OrderSide, current_price: float, symbol: str) -> float:
        """Calculate optimal limit price for price improvement"""
        # Calculate a price that has a good chance of being filled while getting improvement
        if side == OrderSide.BUY:
            # For buy orders, place limit slightly above current price
            return current_price * 1.0005  # 0.05% above market
        else:
            # For sell orders, place limit slightly below current price
            return current_price * 0.9995  # 0.05% below market
    
    def _calculate_execution_slippage(self, quantity: float, symbol: str, side: OrderSide) -> float:
        """Calculate realistic execution slippage"""
        # Base slippage on order size relative to market liquidity
        # This is a simplified model - in practice you'd use real market data
        base_slippage = 0.0005  # 0.05% base slippage
        
        # Adjust for order size (bigger orders have more slippage)
        size_coefficient = min(10.0, (quantity / 100.0))  # Adjust based on your market scale
        market_conditions = self.config.get('market_conditions', {}).get(symbol, 1.0)
        
        total_slippage = base_slippage * size_coefficient * market_conditions
        return min(0.01, total_slippage)  # Cap at 1%
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for simulation"""
        # This would connect to real market data in production
        # For simulation, return a placeholder value
        # In reality, you'd have access to real-time market data
        return 100.0  # Placeholder price
    
    def _record_execution_stats(self, order_id: str, fills: List[Fill]):
        """Record execution statistics"""
        if not fills:
            return
        
        total_quantity = sum(f.quantity for f in fills)
        avg_price = sum(f.price * f.quantity for f in fills) / total_quantity
        execution_time = (fills[-1].timestamp - fills[0].timestamp).total_seconds()
        
        self.execution_stats[order_id] = {
            'total_quantity': total_quantity,
            'avg_price': avg_price,
            'execution_time': execution_time,
            'num_fills': len(fills),
            'min_price': min(f.price for f in fills),
            'max_price': max(f.price for f in fills)
        }
    
    def cancel_twap(self, order_id: str) -> bool:
        """Cancel an active TWAP execution"""
        if order_id in self.active_twaps:
            self.active_twaps[order_id]['status'] = 'CANCELLED'
            self.active_twaps[order_id]['cancelled_at'] = datetime.now()
            logger.info(f"TWAP execution cancelled: {order_id}")
            return True
        return False
    
    def get_active_twaps(self) -> Dict:
        """Get all active TWAP executions"""
        return self.active_twaps.copy()
    
    def get_execution_stats(self, order_id: str) -> Optional[Dict]:
        """Get execution statistics for a specific order"""
        return self.execution_stats.get(order_id)
    
    def get_twap_report(self, order_id: str) -> Dict:
        """Generate a detailed TWAP execution report"""
        if order_id not in self.active_twaps and order_id not in self.execution_stats:
            return {'error': 'Order ID not found'}
        
        twap_data = self.active_twaps.get(order_id, {})
        stats = self.execution_stats.get(order_id, {})
        
        report = {
            'order_id': order_id,
            'status': twap_data.get('status', 'UNKNOWN'),
            'symbol': twap_data.get('symbol', 'UNKNOWN'),
            'total_quantity': twap_data.get('total_quantity', 0),
            'executed_quantity': twap_data.get('executed_quantity', 0),
            'side': twap_data.get('side', 'UNKNOWN'),
            'start_time': twap_data.get('start_time'),
            'end_time': twap_data.get('end_time'),
            'num_slices': twap_data.get('num_slices', 0),
            'slice_quantity': twap_data.get('slice_quantity', 0)
        }
        
        if stats:
            report.update({
                'avg_execution_price': stats.get('avg_price'),
                'execution_time_seconds': stats.get('execution_time'),
                'number_of_fills': stats.get('num_fills'),
                'min_execution_price': stats.get('min_price'),
                'max_execution_price': stats.get('max_price'),
                'total_value_executed': stats.get('avg_price', 0) * stats.get('total_quantity', 0)
            })
        
        return report