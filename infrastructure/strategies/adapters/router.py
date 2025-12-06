from typing import Dict, List, Optional, Callable
from shared.types import Signal, SignalType, Order
from shared.logger import logger
from datetime import datetime
import threading


class StrategyRouter:
    """Routes signals to appropriate strategies based on market conditions and strategy preferences"""
    
    def __init__(self):
        self.strategies: Dict[str, Callable] = {}
        self.strategy_configs: Dict[str, Dict] = {}
        self.signal_queue = []
        self.order_queue = []
        self.lock = threading.Lock()
        
    def register_strategy(self, name: str, strategy_func: Callable, config: Optional[Dict] = None):
        """Register a strategy with the router"""
        with self.lock:
            self.strategies[name] = strategy_func
            self.strategy_configs[name] = config or {}
            logger.info(f"Registered strategy: {name}")
    
    def route_signal(self, signal: Signal) -> Optional[Order]:
        """Route a signal to an appropriate strategy"""
        with self.lock:
            # Determine which strategy should handle this signal
            target_strategy = self._select_strategy(signal)
            
            if not target_strategy or target_strategy not in self.strategies:
                logger.warning(f"No suitable strategy found for signal: {signal.signal_type} for {signal.symbol}")
                return None
                
            try:
                # Execute the strategy
                order = self.strategies[target_strategy](signal)
                
                if order:
                    logger.debug(f"Strategy {target_strategy} generated order: {order.side} {order.quantity} of {order.symbol}")
                    self.order_queue.append(order)
                    
                return order
            except Exception as e:
                logger.error(f"Error executing strategy {target_strategy}: {e}")
                return None
    
    def route_signals_batch(self, signals: List[Signal]) -> List[Order]:
        """Route multiple signals"""
        orders = []
        for signal in signals:
            order = self.route_signal(signal)
            if order:
                orders.append(order)
        return orders
    
    def _select_strategy(self, signal: Signal) -> Optional[str]:
        """Select the most appropriate strategy for a signal"""
        # Get all strategies that are compatible with this signal type
        compatible_strategies = []
        
        for name, config in self.strategy_configs.items():
            # Check if strategy supports this signal type
            supported_types = config.get('supported_signal_types', [SignalType.BUY, SignalType.SELL, SignalType.HOLD])
            if signal.signal_type in supported_types:
                # Check if strategy supports this symbol
                supported_symbols = config.get('supported_symbols', [])
                if not supported_symbols or signal.symbol in supported_symbols:
                    # Calculate strategy preference based on various factors
                    preference_score = self._calculate_strategy_preference(name, signal)
                    compatible_strategies.append((name, preference_score))
        
        if not compatible_strategies:
            return None
            
        # Return the strategy with the highest preference score
        best_strategy = max(compatible_strategies, key=lambda x: x[1])
        return best_strategy[0]
    
    def _calculate_strategy_preference(self, strategy_name: str, signal: Signal) -> float:
        """Calculate how well a strategy matches the current signal"""
        config = self.strategy_configs[strategy_name]
        score = 0.0
        
        # Base confidence factor
        score += signal.confidence * 0.4
        
        # Regime compatibility
        current_regime = getattr(signal, 'regime', 'normal')
        regime_compat = config.get('regime_compatibility', {}).get(current_regime, 0.5)
        score += regime_compat * 0.3
        
        # Market condition compatibility
        market_conditions = config.get('market_conditions', {})
        for condition, required in market_conditions.items():
            if hasattr(signal, condition) and getattr(signal, condition) == required:
                score += 0.1
                
        # Strategy-specific factors
        strategy_type = config.get('strategy_type', 'general')
        if strategy_type == 'trend_following' and signal.signal_type in [SignalType.BUY, SignalType.SELL]:
            score += 0.1
        elif strategy_type == 'mean_reversion' and signal.signal_type in [SignalType.BUY, SignalType.SELL]:
            score += 0.1
        elif strategy_type == 'breakout' and signal.signal_type in [SignalType.BUY, SignalType.SELL]:
            score += 0.1
            
        # Risk management factors
        if signal.confidence > 0.8:
            score += 0.1  # High confidence signals get priority
            
        return score
    
    def get_strategy_stats(self) -> Dict[str, int]:
        """Get statistics about strategy usage"""
        stats = {}
        # In a real implementation, we would track how often each strategy is used
        for name in self.strategies:
            stats[name] = 0  # Placeholder - would track actual usage
        return stats
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders"""
        with self.lock:
            return self.order_queue.copy()
    
    def clear_orders(self):
        """Clear all pending orders"""
        with self.lock:
            self.order_queue.clear()