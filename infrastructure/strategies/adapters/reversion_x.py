from .base_strategy import BaseStrategy
from shared.types import Signal, SignalType, Order, OrderType, OrderSide
from shared.logger import logger
from datetime import datetime
import numpy as np


class ReversionXStrategy(BaseStrategy):
    """Mean reversion strategy that looks for overbought/oversold conditions"""
    
    def __init__(self, name: str, symbol: str, config: dict = None):
        super().__init__(name, symbol, config)
        
        # Reversion specific parameters
        self.oversold_level = config.get('oversold_level', -0.7)  # Signal score indicating oversold
        self.overbought_level = config.get('overbought_level', 0.7)  # Signal score indicating overbought
        self.reversion_threshold = config.get('reversion_threshold', 0.5)  # Minimum reversion signal strength
        self.max_position_reversals = config.get('max_position_reversals', 3)  # Max positions in mean reversion
        self.entry_buffer = []  # Track entry points for mean reversion
        self.current_reversal_count = 0  # Number of reversion entries
        self.reversion_momentum = 0  # Track reversion momentum
        
        # Position management
        self.entry_prices = []  # Track entry prices for pyramiding
        self.max_pyramid_levels = config.get('max_pyramid_levels', 3)  # Max levels in pyramiding
        self.pyramid_ratio = config.get('pyramid_ratio', 0.7)  # Ratio of position for pyramiding
    
    def generate_order(self, signal: Signal) -> Order:
        """Generate a mean reversion order based on the signal"""
        if not self.should_trade(signal):
            return None
            
        # Check for overbought/oversold conditions
        is_oversold = signal.score < self.oversold_level
        is_overbought = signal.score > self.overbought_level
        
        # Calculate the strength of the reversion signal
        reversion_strength = 0
        if is_oversold and signal.signal_type == SignalType.BUY:
            reversion_strength = abs(signal.score - self.oversold_level)
        elif is_overbought and signal.signal_type == SignalType.SELL:
            reversion_strength = abs(signal.score - self.overbought_level)
        
        # Validate reversion signal
        if reversion_strength < self.reversion_threshold:
            logger.debug(f"Reversion signal too weak: {reversion_strength}, threshold: {self.reversion_threshold}")
            return None
            
        # Check if we're already at max reversion positions
        if self.current_reversal_count >= self.max_position_reversals:
            logger.debug(f"At max reversion positions: {self.current_reversal_count}")
            return None
            
        # Check if the signal aligns with mean reversion
        if not ((is_oversold and signal.signal_type == SignalType.BUY) or 
                (is_overbought and signal.signal_type == SignalType.SELL)):
            logger.debug(f"Signal {signal.signal_type} doesn't align with reversion conditions")
            return None
        
        # Calculate dynamic position size for reversion strategy
        account_balance = self.config.get('account_balance', 10000)
        position_size = self.calculate_reversion_position_size(signal, reversion_strength, account_balance)
        
        if position_size <= 0:
            logger.warning(f"Invalid position size calculated: {position_size}")
            return None
            
        # Create order
        order = self.create_order(signal, position_size)
        order.strategy = f"{self.name}_reversion"
        
        # Add to entry tracking
        current_price = signal.metadata.get('current_price', 0) if signal.metadata else 0
        if current_price > 0:
            self.entry_prices.append(current_price)
        
        self.current_reversal_count += 1
        self.reversion_momentum = reversion_strength * (1 if signal.signal_type == SignalType.BUY else -1)
        
        logger.debug(f"ReversionX order: {order.side} {order.quantity} of {order.symbol}, "
                    f"reversion_strength: {reversion_strength:.3f}")
        return order
    
    def calculate_reversion_position_size(self, signal: Signal, reversion_strength: float, account_balance: float) -> float:
        """Calculate position size specifically for mean reversion"""
        # Start with base position size calculation
        base_size = self.calculate_position_size(signal, account_balance)
        
        # Adjust based on reversion strength (stronger reversion = larger position)
        strength_factor = 0.5 + (reversion_strength * 0.7)  # Scale from 0.5 to 1.2
        
        # Adjust based on how far we are from extreme levels
        distance_factor = 1.0
        if signal.score < self.oversold_level:
            # The more oversold, the more cautious (unless confirmed reversal)
            distance_from_extreme = abs(signal.score - self.oversold_level)
            distance_factor = min(1.5, 0.5 + distance_from_extreme)
        elif signal.score > self.overbought_level:
            # The more overbought, the more cautious (unless confirmed reversal)
            distance_from_extreme = abs(signal.score - self.overbought_level)
            distance_factor = min(1.5, 0.5 + distance_from_extreme)
        
        # Market regime adjustment
        regime_factor = 1.0
        if signal.metadata:
            vol_regime = signal.metadata.get('volatility_regime', 'normal')
            if vol_regime == 'high':
                # In high volatility, mean reversion can be more profitable but riskier
                regime_factor = 1.1
            elif vol_regime == 'low':
                # In low volatility, mean reversion signals might be less reliable
                regime_factor = 0.8
                
            # Check if trend is strong (mean reversion might struggle in strong trends)
            trend_strength = signal.metadata.get('trend_strength', 0)
            if abs(trend_strength) > 0.05:  # Strong trend
                regime_factor = 0.6  # Reduce position size in strong trends
        
        # Confidence adjustment (mean reversion often has lower confidence signals)
        confidence_factor = min(1.2, 0.7 + signal.confidence * 0.6)  # Scale from 0.7 to 1.3
        
        # Pyramiding adjustment if we already have positions
        pyramid_factor = 1.0
        if len(self.entry_prices) > 0:
            # For pyramiding in mean reversion
            pyramid_factor = self.pyramid_ratio ** len(self.entry_prices)
            # Only pyramid up to max levels
            if len(self.entry_prices) >= self.max_pyramid_levels:
                pyramid_factor = 0  # Don't add more positions
        
        # Calculate final position size
        final_size = base_size * strength_factor * distance_factor * regime_factor * confidence_factor * pyramid_factor
        
        # Cap position size to prevent over-leveraging
        max_reversion_size = account_balance * 0.03  # Max 3% of balance per reversion trade
        final_size = min(final_size, max_reversion_size)
        
        return final_size
    
    def should_trade(self, signal: Signal) -> bool:
        """Enhanced trade decision for mean reversion"""
        # Use parent's decision first
        if not super().should_trade(signal):
            return False
            
        # Additional reversion checks
        # Don't revert in strong trending markets
        if signal.metadata:
            trend_strength = signal.metadata.get('trend_strength', 0)
            if abs(trend_strength) > 0.1:  # Very strong trend
                logger.debug(f"Skipping reversion trade in strong trend: {trend_strength}")
                return False
                
            vol_regime = signal.metadata.get('volatility_regime', 'normal')
            if vol_regime == 'extreme':
                # Be careful with mean reversion in extreme volatility
                return signal.confidence > 0.7  # Only high confidence signals
        
        # Don't trade if signal is not at extreme levels
        is_oversold = signal.score < self.oversold_level
        is_overbought = signal.score > self.overbought_level
        if not (is_oversold or is_overbought):
            return False
            
        return True
    
    def update_state(self, market_data: dict):
        """Update strategy state with market data"""
        # Check if we need to take profits or stop losses based on reversion
        current_price = market_data.get('price', 0)
        if current_price > 0 and self.entry_prices:
            # Check each entry for exit conditions
            entries_to_remove = []
            
            for i, entry_price in enumerate(self.entry_prices):
                # Calculate PnL for this entry
                if self.reversion_momentum > 0:  # Expecting bullish reversion
                    pnl = (current_price - entry_price) / entry_price
                else:  # Expecting bearish reversion
                    pnl = (entry_price - current_price) / entry_price
                
                # Check exit conditions
                exit_condition = ""
                should_exit = False
                
                if pnl >= self.take_profit:
                    should_exit = True
                    exit_condition = "take_profit"
                elif pnl <= -self.stop_loss:
                    should_exit = True
                    exit_condition = "stop_loss"
                elif len(self.entry_prices) > 1 and pnl < 0:
                    # If we have multiple entries and this one is negative, take small loss to average
                    should_exit = True
                    exit_condition = "pyramid_exit"
                
                if should_exit:
                    entries_to_remove.append(i)
            
            # Remove completed entries
            for i in sorted(entries_to_remove, reverse=True):
                if i < len(self.entry_prices):
                    removed_price = self.entry_prices.pop(i)
                    logger.debug(f"ReversionX exited position at {current_price} (entry: {removed_price}, PnL: {(current_price-removed_price)/removed_price:.4f}, reason: {exit_condition})")
                    self.current_reversal_count = max(0, self.current_reversal_count - 1)
    
    def reset_reversion_state(self):
        """Reset the reversion state for a new cycle"""
        self.entry_prices.clear()
        self.current_reversal_count = 0
        self.reversion_momentum = 0
        logger.debug(f"Reset reversion state for strategy {self.name}")