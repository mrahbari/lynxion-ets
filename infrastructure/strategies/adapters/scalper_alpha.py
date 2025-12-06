from .base_strategy import BaseStrategy
from shared.types import Signal, SignalType, Order, OrderType, OrderSide
from shared.logger import logger
from datetime import datetime
import numpy as np


class ScalperAlphaStrategy(BaseStrategy):
    """High-frequency scalping strategy that aims to profit from small price movements"""
    
    def __init__(self, name: str, symbol: str, config: dict = None):
        super().__init__(name, symbol, config)
        
        # Scalping specific parameters
        self.min_price_move = config.get('min_price_move', 0.001)  # Minimum price move to trigger trade
        self.max_spread_ratio = config.get('max_spread_ratio', 0.5)  # Maximum spread ratio to trade
        self.max_positions = config.get('max_positions', 5)  # Max concurrent positions
        self.scalp_target = config.get('scalp_target', 0.002)  # Aim for 0.2% profit
        self.time_limit = config.get('time_limit', 300)  # Max holding time in seconds (5 minutes)
        
        # Internal tracking
        self.active_positions = 0
        self.last_signal_time = datetime.min
        self.entry_prices = {}  # Track entry prices for active positions
    
    def generate_order(self, signal: Signal) -> Order:
        """Generate a scalping order based on the signal"""
        if not self.should_trade(signal):
            return None
            
        # Check if market spread is favorable
        if signal.metadata and 'bid_ask_spread' in signal.metadata:
            spread = signal.metadata['bid_ask_spread']
            if spread > self.max_spread_ratio * signal.score:  # If spread is too wide relative to signal strength
                logger.debug(f"Spread too wide for scalping: {spread}, skipping trade")
                return None
        
        # Check if there's enough minimum price movement potential
        if abs(signal.score) < self.min_price_move:
            logger.debug(f"Signal score too weak for scalping: {signal.score}, skipping trade")
            return None
            
        # Check if we've reached max positions
        if self.active_positions >= self.max_positions:
            logger.debug(f"Max positions reached: {self.active_positions}, skipping trade")
            return None
            
        # Check if enough time has passed since last trade (to avoid over-trading)
        time_since_last = (datetime.now() - self.last_signal_time).total_seconds()
        if time_since_last < 10:  # Don't trade more than once every 10 seconds
            logger.debug(f"Not enough time since last trade: {time_since_last}s, skipping trade")
            return None
            
        # Calculate dynamic position size for scalping
        account_balance = self.config.get('account_balance', 10000)  # Default to $10k
        position_size = self.calculate_scalping_position_size(signal, account_balance)
        
        if position_size <= 0:
            logger.warning(f"Invalid position size calculated: {position_size}")
            return None
            
        # Create order
        order = self.create_order(signal, position_size)
        
        # Add scalping-specific metadata
        order.strategy = f"{self.name}_scalp"
        order.time_in_force = "IOC"  # Immediate or Cancel to ensure quick execution
        
        # Set stop loss and take profit for scalping
        current_price = signal.metadata.get('current_price', 0) if signal.metadata else 0
        if current_price > 0:
            if signal.signal_type == SignalType.BUY:
                order.stop_price = current_price * (1 - self.stop_loss)
            else:
                order.stop_price = current_price * (1 + self.stop_loss)
        
        if self.validate_order(order):
            # Update internal tracking
            self.active_positions += 1
            self.last_signal_time = datetime.now()
            
            if signal.signal_type == SignalType.BUY:
                self.entry_prices[order.client_order_id or f"pos_{datetime.now().timestamp()}"] = current_price
            else:
                self.entry_prices[order.client_order_id or f"pos_{datetime.now().timestamp()}"] = current_price
                
            logger.debug(f"ScalperAlpha generated order: {order.side} {order.quantity} of {order.symbol}")
            return order
        else:
            logger.warning("Generated order failed validation")
            return None
    
    def calculate_scalping_position_size(self, signal: Signal, account_balance: float) -> float:
        """Calculate position size specifically for scalping"""
        # Start with base position size
        base_size = self.calculate_position_size(signal, account_balance)
        
        # Adjust for scalping characteristics
        # Higher confidence signals get larger positions, but scaled for scalping
        confidence_factor = 0.7 + (signal.confidence * 0.3)  # Scale from 0.7 to 1.0
        
        # Market regime adjustment
        regime_factor = 1.0
        if signal.metadata:
            vol_regime = signal.metadata.get('volatility_regime', 'normal')
            if vol_regime == 'high':
                # In high volatility, use smaller positions for scalping
                regime_factor = 0.6
            elif vol_regime == 'low':
                # In low volatility, can use slightly larger positions
                regime_factor = 1.2
                
            # Adjust based on liquidity
            liquidity_regime = signal.metadata.get('liquidity_regime', 'normal')
            if liquidity_regime == 'low':
                regime_factor = 0.5  # Be more conservative in low liquidity
            elif liquidity_regime == 'high':
                regime_factor = 1.1  # Can take larger positions in high liquidity
        
        # Adjust based on signal strength
        signal_strength_factor = max(0.5, min(1.5, 1.0 + abs(signal.score) * 10))  # Scale based on signal strength
        
        # Calculate final position size
        final_size = base_size * confidence_factor * regime_factor * signal_strength_factor
        
        # Cap position size to prevent over-leveraging
        max_scalp_size = account_balance * 0.05  # Max 5% of balance per scalp trade
        final_size = min(final_size, max_scalp_size)
        
        return final_size
    
    def should_trade(self, signal: Signal) -> bool:
        """Enhanced trade decision for scalping"""
        # Use parent's decision first
        if not super().should_trade(signal):
            return False
            
        # Additional scalping checks
        # Don't scalp on very low confidence signals
        if signal.confidence < 0.5:
            return False
            
        # Don't scalp during very high volatility extremes
        if signal.metadata:
            vol_regime = signal.metadata.get('volatility_regime', 'normal')
            if vol_regime == 'extreme':
                return False
                
        return True
    
    def update_state(self, market_data: dict):
        """Update strategy state with market data"""
        # Close positions that have reached targets or time limits
        
        # Check each active position for take-profit, stop-loss, or time limit
        positions_to_close = []
        
        for pos_id, entry_price in self.entry_prices.items():
            current_price = market_data.get('price', 0)
            if current_price > 0 and entry_price > 0:
                # Calculate PnL
                if pos_id in self.entry_prices:  # Check if position still exists
                    pnl_pct = (current_price - entry_price) / entry_price if entry_price != 0 else 0
                    time_held = (datetime.now() - self.last_signal_time).total_seconds()
                    
                    # Check exit conditions
                    should_exit = False
                    exit_reason = ""
                    
                    if abs(pnl_pct) >= self.scalp_target:
                        # Target reached
                        should_exit = True
                        exit_reason = "target_reached"
                    elif abs(pnl_pct) >= self.stop_loss:
                        # Stop loss hit
                        should_exit = True
                        exit_reason = "stop_loss_hit"
                    elif time_held >= self.time_limit:
                        # Time limit reached
                        should_exit = True
                        exit_reason = "time_limit"
                        
                    if should_exit:
                        positions_to_close.append((pos_id, exit_reason))
        
        # Process position closures
        for pos_id, reason in positions_to_close:
            if pos_id in self.entry_prices:
                del self.entry_prices[pos_id]
                self.active_positions = max(0, self.active_positions - 1)
                logger.debug(f"Closed position {pos_id} for reason: {reason}")