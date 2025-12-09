from .base_strategy import BaseStrategy
from shared.types import Signal, SignalType, Order, OrderType, OrderSide
from shared.logger import logger
from datetime import datetime
import numpy as np


class TrendFollowStrategy(BaseStrategy):
    """Trend following strategy that aims to capture long-term trends"""
    
    def __init__(self, name: str, symbol: str, config: dict = None):
        super().__init__(name, symbol, config)
        
        # Trend following specific parameters
        self.trend_confirmation = config.get('trend_confirmation', 3)  # Number of signals needed to confirm trend
        self.trend_min_strength = config.get('trend_min_strength', 0.3)  # Minimum trend strength
        self.max_reversal_signals = config.get('max_reversal_signals', 2)  # Max reversal signals before exit
        self.trend_buffer = []  # Buffer to store recent signals
        self.active_trend = None  # Current active trend (None, 'long', 'short')
        self.entry_price = 0  # Price when trend started
        self.consecutive_signals = 0  # Number of consecutive trend signals
        
        # Risk management
        self.risk_per_trade = config.get('risk_per_trade', 0.02)  # Risk 2% per trade
        self.max_drawdown = config.get('max_drawdown', 0.15)  # Max 15% drawdown
    
    def generate_order(self, signal: Signal) -> Order:
        """Generate a trend following order based on the signal"""
        if not self.should_trade(signal):
            return None
            
        # Add signal to trend buffer
        self.trend_buffer.append(signal)
        if len(self.trend_buffer) > 10:  # Keep only recent signals
            self.trend_buffer.pop(0)
            
        # Analyze trend based on signal buffer
        current_trend = self.analyze_trend()
        
        # Check if there's a trend change or confirmation
        if current_trend != self.active_trend:
            # New trend detected
            return self.handle_trend_change(signal, current_trend)
        elif current_trend and self.consecutive_signals >= self.trend_confirmation:
            # Trend confirmed, but we might already be in it
            if self.active_trend is None:
                # New confirmed trend that we're not in yet
                return self.handle_trend_change(signal, current_trend)
        
        # No new trend or position change needed
        return None
    
    def analyze_trend(self):
        """Analyze the current trend based on signal buffer"""
        if len(self.trend_buffer) < 3:
            return None
            
        # Count recent signals
        buy_signals = sum(1 for s in self.trend_buffer[-self.trend_confirmation:] if s.signal_type == SignalType.BUY)
        sell_signals = sum(1 for s in self.trend_buffer[-self.trend_confirmation:] if s.signal_type == SignalType.SELL)
        
        # Check if we have confirmed trend
        if buy_signals >= self.trend_confirmation and buy_signals > sell_signals:
            return 'long'
        elif sell_signals >= self.trend_confirmation and sell_signals > buy_signals:
            return 'short'
        else:
            return None
    
    def handle_trend_change(self, signal: Signal, new_trend: str) -> Order:
        """Handle entering or exiting a trend"""
        # If we're changing from one trend to another, close the previous position first
        if self.active_trend is not None and self.active_trend != new_trend:
            # Generate exit order for existing position
            exit_side = OrderSide.BUY if self.active_trend == 'short' else OrderSide.SELL
            exit_order = Order(
                symbol=self.symbol,
                side=exit_side,
                quantity=self.config.get('current_position', 0),  # Use actual position size
                order_type=OrderType.MARKET,
                time_in_force="GTC"
            )
            exit_order.strategy = f"{self.name}_exit"
            
            # Reset for new trend
            self.active_trend = None
            self.entry_price = 0
            self.consecutive_signals = 0
            
            logger.debug(f"TrendFollow exit order: {exit_order.side} to close {self.symbol}")
            return exit_order
        
        # Now check if we should enter the new trend
        if new_trend is not None:
            # Check signal strength
            if abs(signal.score) < self.trend_min_strength:
                logger.debug(f"Trend signal not strong enough: {signal.score}, min: {self.trend_min_strength}")
                return None
                
            # Calculate position size based on risk management
            account_balance = self.config.get('account_balance', 10000)
            position_size = self.calculate_trend_position_size(signal, account_balance)
            
            if position_size <= 0:
                logger.warning(f"Invalid position size calculated: {position_size}")
                return None
            
            # Create entry order
            entry_side = OrderSide.BUY if new_trend == 'long' else OrderSide.SELL
            order = Order(
                symbol=self.symbol,
                side=entry_side,
                quantity=position_size,
                order_type=OrderType.MARKET,
                time_in_force="GTC"
            )
            
            # Set strategy name
            order.strategy = f"{self.name}_entry"
            
            # Store trend information
            self.active_trend = new_trend
            current_price = signal.metadata.get('current_price', 0) if signal.metadata else 0
            self.entry_price = current_price if current_price > 0 else signal.score  # Fallback to signal score
            self.consecutive_signals = 1
            
            logger.debug(f"TrendFollow entry order: {order.side} {order.quantity} of {order.symbol} for {new_trend} trend")
            return order
        
        return None
    
    def calculate_trend_position_size(self, signal: Signal, account_balance: float) -> float:
        """Calculate position size specifically for trend following"""
        # Calculate position size based on risk per trade and stop loss
        risk_amount = account_balance * self.risk_per_trade
        
        # Get stop loss in price terms
        current_price = signal.metadata.get('current_price', 0) if signal.metadata else 0
        if current_price <= 0:
            current_price = 100  # Default if no price available
        
        # Calculate stop loss distance
        stop_distance = current_price * self.stop_loss
        
        # If stop distance is 0, use a default value
        if stop_distance == 0:
            stop_distance = current_price * 0.02  # Default 2% stop loss
        
        # Calculate position size based on risk
        position_size = risk_amount / stop_distance if stop_distance > 0 else account_balance * 0.01
        
        # Apply additional factors
        # Increase size for high confidence trend signals
        confidence_factor = 0.8 + (signal.confidence * 0.4)  # Scale from 0.8 to 1.2
        
        # Apply regime adjustment
        regime_factor = 1.0
        if signal.metadata:
            trend_aligned = signal.metadata.get('trend_aligned', True)
            if trend_aligned:
                regime_factor = 1.3  # Increase size when trend is confirmed
            else:
                regime_factor = 0.7  # Decrease size when trend alignment is questionable
                
            vol_regime = signal.metadata.get('volatility_regime', 'normal')
            if vol_regime == 'high':
                regime_factor = 0.8  # Reduce size in high volatility
            elif vol_regime == 'low':
                regime_factor = 1.1  # Increase size in low volatility
        
        final_size = position_size * confidence_factor * regime_factor
        
        # Cap at max position if specified
        if self.max_position and final_size > self.max_position:
            final_size = self.max_position
            
        return final_size
    
    def should_trade(self, signal: Signal) -> bool:
        """Enhanced trade decision for trend following"""
        # Use parent's decision first
        if not super().should_trade(signal):
            return False
            
        # Don't trade if we don't have trend confirmation parameters
        if self.trend_confirmation <= 1:
            return False
            
        # Additional trend following checks
        # Only trade when we have market regime information that supports trend following
        if signal.metadata:
            vol_regime = signal.metadata.get('volatility_regime', 'normal')
            if vol_regime == 'extreme':
                # In extreme volatility, trends might be less reliable
                return False
                
            liquidity_regime = signal.metadata.get('liquidity_regime', 'normal')
            if liquidity_regime == 'low':
                # Low liquidity might not support trend following
                return False
        
        return True
    
    def update_state(self, market_data: dict):
        """Update strategy state with market data"""
        # Check if we need to exit the current trend based on market data
        if self.active_trend and market_data.get('price'):
            current_price = market_data['price']
            
            # Calculate current PnL
            if self.entry_price > 0:
                pnl = 0
                if self.active_trend == 'long':
                    pnl = (current_price - self.entry_price) / self.entry_price
                else:  # short
                    pnl = (self.entry_price - current_price) / self.entry_price
                
                # Check if we hit stop loss or should take profit
                if abs(pnl) >= self.max_drawdown:
                    # Max drawdown reached, exit position
                    logger.info(f"TrendFollow max drawdown reached: {pnl:.3f}, exiting trend")
                    self.active_trend = None
                    self.entry_price = 0
                    self.consecutive_signals = 0
                elif pnl >= self.take_profit:
                    # Take profit reached, exit position
                    logger.info(f"TrendFollow take profit reached: {pnl:.3f}, exiting trend")
                    self.active_trend = None
                    self.entry_price = 0
                    self.consecutive_signals = 0