from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from shared.types import Signal, Order, OrderType, OrderSide
from shared.logger import logger
from datetime import datetime


class BaseStrategy(ABC):
    """Base class for all strategies"""
    
    def __init__(self, name: str, symbol: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.symbol = symbol
        self.config = config or {}
        self.position_size = config.get('position_size', 0.01)  # Default 1% of capital
        self.stop_loss = config.get('stop_loss', 0.02)  # Default 2% stop loss
        self.take_profit = config.get('take_profit', 0.05)  # Default 5% take profit
        self.max_position = config.get('max_position', float('inf'))
        self.is_active = True
        
    @abstractmethod
    def generate_order(self, signal: Signal) -> Optional[Order]:
        """Generate an order based on the signal"""
        pass
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update strategy configuration"""
        self.config.update(new_config)
        
        # Update internal parameters that might have changed
        if 'position_size' in new_config:
            self.position_size = new_config['position_size']
        if 'stop_loss' in new_config:
            self.stop_loss = new_config['stop_loss']
        if 'take_profit' in new_config:
            self.take_profit = new_config['take_profit']
        if 'max_position' in new_config:
            self.max_position = new_config['max_position']
    
    def calculate_position_size(self, signal: Signal, account_balance: float) -> float:
        """Request position size - this should be handled by the risk manager"""
        # According to the risk governance rules, the Strategy module should only
        # request risk parameters but not calculate them. The actual calculation
        # must be done by the Risk module.

        # Return a default value that will be overridden by the risk manager
        # This is just a placeholder to maintain interface compatibility
        return 0.0
    
    def create_order(self, signal: Signal, quantity: float) -> Order:
        """Create an order based on signal"""
        side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL
        
        order = Order(
            symbol=self.symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            price=None,  # Market orders don't specify price
            time_in_force="GTC"
        )
        
        # Add strategy metadata
        order.strategy = self.name
        
        return order
    
    def should_trade(self, signal: Signal) -> bool:
        """Determine if we should trade based on the signal"""
        if not self.is_active:
            return False
            
        # Don't trade if confidence is too low
        if signal.confidence < 0.3:
            return False
            
        # Don't trade during certain market conditions if specified in config
        if signal.metadata:
            vol_regime = signal.metadata.get('volatility_regime', 'normal')
            if vol_regime == 'extreme' and self.config.get('avoid_extreme_vol', True):
                return False
                
        return True
    
    def validate_order(self, order: Order) -> bool:
        """Validate an order before sending it"""
        # Check if quantity is valid
        if order.quantity <= 0:
            logger.warning(f"Invalid order quantity: {order.quantity}")
            return False
            
        # Add other validation checks as needed
        if order.order_type not in [OrderType.MARKET, OrderType.LIMIT]:
            logger.warning(f"Unsupported order type: {order.order_type}")
            return False
            
        return True
    
    def update_state(self, market_data: Dict[str, Any]):
        """Update strategy state with market data"""
        # Default implementation does nothing
        # Strategies can override this to update internal state
        pass