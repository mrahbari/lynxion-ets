from typing import Dict, List, Optional, Tuple
from shared.types import Order, OrderType, Fill, OrderSide
from shared.logger import logger
from datetime import datetime, timedelta
import time
import threading
import numpy as np
from collections import deque


class VWAPExecution:
    """Volume-Weighted Average Price execution algorithm"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # VWAP parameters
        self.lookback_period = config.get('vwap_lookback_minutes', 60)  # Look at last 60 minutes of data
        self.update_frequency = config.get('vwap_update_frequency', 30)  # Update every 30 seconds
        self.price_buffer_size = config.get('vwap_price_buffer_size', 100)  # Keep 100 price points
        self.volume_buffer_size = config.get('vwap_volume_buffer_size', 100)  # Keep 100 volume points
        self.max_slice_deviation = config.get('vwap_max_slice_deviation', 0.2)  # Max 20% deviation from VWAP
        self.enable_price_improvement = config.get('vwap_price_improvement', True)
        
        # Market data tracking
        self.price_history = {}
        self.volume_history = {}
        self.vwap_calculations = {}
        
        # Active executions
        self.active_vwaps = {}
        self.execution_stats = {}
        
        # Market hours (simplified)
        self.market_open = config.get('market_open', (9, 30))  # 9:30 AM
        self.market_close = config.get('market_close', (16, 0))  # 4:00 PM
    
    def execute_vwap_order(self, 
                          symbol: str, 
                          total_quantity: float, 
                          side: OrderSide, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          urgency: float = 0.5) -> List[Fill]:
        """Execute a VWAP order by following volume patterns"""
        
        if start_time is None:
            start_time = datetime.now()
        if end_time is None:
            # Default: remainder of trading day or next 2 hours, whichever is shorter
            market_close = datetime.combine(start_time.date(), 
                                          datetime.min.time().replace(
                                              hour=self.market_close[0], 
                                              minute=self.market_close[1]))
            default_end = start_time + timedelta(hours=2)
            end_time = min(market_close, default_end)
        
        order_id = f"vwap_{int(time.time() * 1000000)}"
        
        # Initialize VWAP execution
        self.active_vwaps[order_id] = {
            'symbol': symbol,
            'total_quantity': total_quantity,
            'side': side,
            'start_time': start_time,
            'end_time': end_time,
            'urgency': urgency,  # 0.0 = low urgency (patient), 1.0 = high urgency (aggressive)
            'executed_quantity': 0,
            'executed_value': 0,
            'status': 'ACTIVE',
            'target_schedule': self._calculate_vwap_schedule(symbol, total_quantity, start_time, end_time),
            'current_slice': 0
        }
        
        logger.info(f"Starting VWAP execution: {order_id} for {total_quantity} {symbol}, "
                   f"from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}")
        
        all_fills = []
        
        try:
            current_time = datetime.now()
            while current_time < end_time and self.active_vwaps[order_id]['executed_quantity'] < total_quantity:
                # Calculate the target quantity for this time period based on historical VWAP
                target_qty = self._get_target_quantity(order_id)
                
                if target_qty > 0:
                    # Execute slice
                    slice_order = Order(
                        symbol=symbol,
                        side=side,
                        quantity=target_qty,
                        order_type=OrderType.MARKET
                    )
                    
                    fill = self._execute_vwap_slice(slice_order, order_id)
                    if fill:
                        all_fills.append(fill)
                        # Update execution tracking
                        self.active_vwaps[order_id]['executed_quantity'] += fill.quantity
                        self.active_vwaps[order_id]['executed_value'] += fill.quantity * fill.price
                        
                        logger.debug(f"VWAP fill: {fill.quantity} @ {fill.price}, "
                                    f"total executed: {self.active_vwaps[order_id]['executed_quantity']}/{total_quantity}")
                
                # Wait before next check
                time.sleep(self.update_frequency)
                current_time = datetime.now()
                
                # Update schedule as we progress through the day
                self.active_vwaps[order_id]['target_schedule'] = self._update_schedule(order_id)
            
            # Update execution status
            self.active_vwaps[order_id]['status'] = 'COMPLETED' if self.active_vwaps[order_id]['executed_quantity'] >= total_quantity else 'PARTIAL'
            self.active_vwaps[order_id]['completed_time'] = datetime.now()
            
            logger.info(f"VWAP execution completed: {order_id}, "
                       f"executed {self.active_vwaps[order_id]['executed_quantity']}/{total_quantity}")
            
        except Exception as e:
            logger.error(f"Error in VWAP execution {order_id}: {e}")
            self.active_vwaps[order_id]['status'] = 'ERROR'
            self.active_vwaps[order_id]['error'] = str(e)
        finally:
            # Record execution stats
            self._record_execution_stats(order_id, all_fills)
        
        return all_fills
    
    def _calculate_vwap_schedule(self, symbol: str, total_quantity: float, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Calculate the VWAP-based execution schedule"""
        # In a real system, this would analyze historical volume patterns
        # For this example, we'll create a simplified schedule
        
        total_duration = (end_time - start_time).total_seconds()
        schedule = []
        
        # Get historical VWAP data for this time period
        historical_vwap = self._get_historical_vwap(symbol, start_time, end_time)
        
        # Create schedule chunks
        chunk_size = self.update_frequency  # 30 seconds
        num_chunks = int(total_duration / chunk_size)
        
        # Calculate quantity allocation based on typical volume patterns
        # For simplicity, assume volume is higher at market open and close
        for i in range(num_chunks):
            chunk_start = start_time + timedelta(seconds=i * chunk_size)
            chunk_end = start_time + timedelta(seconds=(i + 1) * chunk_size)
            
            # Simplified volume profile (higher at open/close, lower in middle)
            hours_into_session = (chunk_start.hour - self.market_open[0]) + (chunk_start.minute / 60.0)
            total_session_hours = (self.market_close[0] - self.market_open[0]) + ((self.market_close[1] - self.market_open[1]) / 60.0)
            
            # Volume profile: higher at beginning and end, lower in middle (bell curve)
            t = hours_into_session / total_session_hours if total_session_hours > 0 else 0.5
            volume_factor = 0.5 + 0.5 * np.sin(np.pi * t)  # Sine wave for bell curve
            
            # Allocate quantity based on volume factor
            chunk_quantity = total_quantity * (volume_factor / num_chunks) * 2  # Adjust for bell curve
            
            schedule.append({
                'start_time': chunk_start,
                'end_time': chunk_end,
                'target_quantity': chunk_quantity,
                'estimated_vwap': historical_vwap if historical_vwap else 100.0  # Placeholder
            })
        
        return schedule
    
    def _update_schedule(self, order_id: str) -> List[Dict]:
        """Update the execution schedule as orders are filled"""
        execution = self.active_vwaps[order_id]
        remaining_quantity = execution['total_quantity'] - execution['executed_quantity']
        
        # Adjust schedule based on remaining quantity and time left
        new_schedule = []
        time_left = (execution['end_time'] - datetime.now()).total_seconds()
        
        if time_left > 0:
            # Recalculate schedule with remaining quantity
            for chunk in execution['target_schedule']:
                if chunk['end_time'] > datetime.now():
                    # Scale down the target quantity proportionally
                    original_duration = (chunk['end_time'] - chunk['start_time']).total_seconds()
                    remaining_duration = time_left if time_left < original_duration else original_duration
                    time_ratio = remaining_duration / original_duration
                    scaled_quantity = chunk['target_quantity'] * time_ratio
                    new_schedule.append({**chunk, 'target_quantity': scaled_quantity})
        
        return new_schedule
    
    def _get_target_quantity(self, order_id: str) -> float:
        """Get the target quantity to execute based on VWAP schedule"""
        execution = self.active_vwaps[order_id]
        
        # Find the current target time chunk
        current_time = datetime.now()
        current_chunk = None
        
        for chunk in execution['target_schedule']:
            if chunk['start_time'] <= current_time <= chunk['end_time']:
                current_chunk = chunk
                break
        
        if not current_chunk:
            return 0  # No valid time chunk
        
        # Calculate how much should have been executed by now
        time_elapsed = (current_time - execution['start_time']).total_seconds()
        total_duration = (execution['end_time'] - execution['start_time']).total_seconds()
        expected_completion = time_elapsed / total_duration if total_duration > 0 else 0
        
        target_so_far = execution['total_quantity'] * expected_completion
        remaining_to_target = max(0, target_so_far - execution['executed_quantity'])
        remaining_to_complete = execution['total_quantity'] - execution['executed_quantity']
        
        # Adjust based on urgency (higher urgency means execute more aggressively)
        urgency_factor = 0.5 + 0.5 * execution['urgency']
        target_qty = min(remaining_to_target * urgency_factor, remaining_to_complete)
        
        # Ensure it's within reasonable bounds
        min_slice = execution['total_quantity'] * 0.01  # 1% minimum slice
        max_slice = execution['total_quantity'] * 0.1   # 10% maximum slice
        
        return max(min_slice, min(max_slice, target_qty))
    
    def _execute_vwap_slice(self, order: Order, parent_order_id: str) -> Optional[Fill]:
        """Execute a single slice of the VWAP order"""
        try:
            current_price = self._get_current_price(order.symbol)
            if current_price is None:
                logger.error(f"Could not get current price for {order.symbol}")
                return None
            
            # Get current VWAP for the symbol
            current_vwap = self._get_current_vwap(order.symbol)
            
            if current_vwap is None:
                # Fallback to market execution if no VWAP data available
                current_vwap = current_price
            
            # Determine execution approach based on market conditions
            price_deviation = abs(current_price - current_vwap) / current_vwap if current_vwap != 0 else 0
            
            if price_deviation <= self.max_slice_deviation and self.enable_price_improvement:
                # Price is close to VWAP, try for improvement
                fill = self._execute_at_vwap_improvement(order, current_vwap, current_price)
            else:
                # Price is away from VWAP, focus on execution
                fill = self._submit_market_slice(order, current_price)
            
            return fill
            
        except Exception as e:
            logger.error(f"Error executing VWAP slice: {e}")
            return None
    
    def _execute_at_vwap_improvement(self, order: Order, target_vwap: float, current_price: float) -> Optional[Fill]:
        """Try to execute close to VWAP price with potential for improvement"""
        # Calculate limit price based on VWAP (with slight improvement if possible)
        if order.side == OrderSide.BUY:
            limit_price = min(current_price, target_vwap * 1.0001)  # Don't go above current market by much
        else:
            limit_price = max(current_price, target_vwap * 0.9999)  # Don't go below current market by much
        
        # Submit limit order with a short timeout
        fill = self._submit_limit_slice(order, limit_price, timeout=5)
        
        # If limit order didn't fill, fallback to market
        if not fill:
            fill = self._submit_market_slice(order, current_price)
        
        return fill
    
    def _submit_market_slice(self, order: Order, current_price: float) -> Optional[Fill]:
        """Submit a market order slice with realistic pricing"""
        # Calculate execution price with realistic slippage
        slippage = self._calculate_execution_slippage(order.quantity, order.symbol, order.side)
        
        if order.side == OrderSide.BUY:
            executed_price = current_price * (1 + slippage)
        else:
            executed_price = current_price * (1 - slippage)
        
        fill = Fill(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=executed_price,
            timestamp=datetime.now(),
            order_id=f"vwap_slice_{int(time.time() * 1000000)}"
        )
        
        return fill
    
    def _submit_limit_slice(self, order: Order, limit_price: float, timeout: int = 10) -> Optional[Fill]:
        """Submit a limit order slice with timeout"""
        # For this simulation, we'll check if the limit would be hit immediately
        current_price = self._get_current_price(order.symbol)
        if current_price is None:
            return None
        
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
                order_id=f"vwap_limit_slice_{int(time.time() * 1000000)}"
            )
            return fill
        
        # In a real system, this would wait for the order to fill or timeout
        return None
    
    def _get_current_vwap(self, symbol: str) -> Optional[float]:
        """Get the current VWAP for a symbol"""
        # In a real implementation, this would calculate VWAP from real-time data
        # For now, we'll return the current price as a placeholder
        return self._get_current_price(symbol)
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price (placeholder implementation)"""
        # This would connect to real market data in production
        # For simulation, return a placeholder value
        return 100.0  # Placeholder price
    
    def _calculate_execution_slippage(self, quantity: float, symbol: str, side: OrderSide) -> float:
        """Calculate realistic execution slippage based on market conditions"""
        # Base slippage on order size and market liquidity
        base_slippage = 0.0003  # 0.03% base slippage
        
        # Increase with order size
        size_coefficient = min(5.0, (quantity / 500.0))  # Adjust based on your market scale
        
        # Increase during volatile market conditions
        volatility_factor = self.config.get('market_volatility', {}).get(symbol, 1.0)
        
        total_slippage = base_slippage * size_coefficient * volatility_factor
        return min(0.005, total_slippage)  # Cap at 0.5%
    
    def _get_historical_vwap(self, symbol: str, start_time: datetime, end_time: datetime) -> Optional[float]:
        """Get historical VWAP for the same time period"""
        # In a real implementation, this would query historical data
        # For this example, return a placeholder
        return 100.0
    
    def _record_execution_stats(self, order_id: str, fills: List[Fill]):
        """Record execution statistics"""
        if not fills:
            return
        
        total_quantity = sum(f.quantity for f in fills)
        avg_price = sum(f.price * f.quantity for f in fills) / total_quantity if total_quantity > 0 else 0
        execution_time = (fills[-1].timestamp - fills[0].timestamp).total_seconds()
        
        self.execution_stats[order_id] = {
            'total_quantity': total_quantity,
            'avg_price': avg_price,
            'execution_time': execution_time,
            'num_fills': len(fills),
            'min_price': min(f.price for f in fills),
            'max_price': max(f.price for f in fills),
            'total_value': avg_price * total_quantity
        }
    
    def cancel_vwap(self, order_id: str) -> bool:
        """Cancel an active VWAP execution"""
        if order_id in self.active_vwaps:
            self.active_vwaps[order_id]['status'] = 'CANCELLED'
            self.active_vwaps[order_id]['cancelled_at'] = datetime.now()
            logger.info(f"VWAP execution cancelled: {order_id}")
            return True
        return False
    
    def get_active_vwaps(self) -> Dict:
        """Get all active VWAP executions"""
        return self.active_vwaps.copy()
    
    def get_execution_stats(self, order_id: str) -> Optional[Dict]:
        """Get execution statistics for a specific order"""
        return self.execution_stats.get(order_id)