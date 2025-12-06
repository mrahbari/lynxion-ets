from typing import Dict, List, Optional
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
import numpy as np


class AdaptiveSelector:
    """Adaptively selects which strategies to use based on market conditions and performance"""
    
    def __init__(self):
        self.strategy_performance: Dict[str, Dict] = {}
        self.strategy_enabled: Dict[str, bool] = {}
        self.regime_strategy_weights: Dict[str, Dict[str, float]] = {}
        self.performance_decay = 0.95  # How much past performance decays over time
        
    def update_strategy_performance(self, strategy_name: str, pnl: float, confidence: float):
        """Update the performance metrics for a strategy"""
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = {
                'total_pnl': 0.0,
                'total_confidence_weighted_pnl': 0.0,
                'signals_count': 0,
                'win_count': 0,
                'last_update': datetime.now()
            }
            self.strategy_enabled[strategy_name] = True  # Enable new strategies by default
        
        perf = self.strategy_performance[strategy_name]
        
        # Apply decay to historical performance
        perf['total_pnl'] *= self.performance_decay
        perf['total_confidence_weighted_pnl'] *= self.performance_decay
        
        # Update with new performance
        perf['total_pnl'] += pnl
        perf['total_confidence_weighted_pnl'] += pnl * confidence
        perf['signals_count'] += 1
        
        if pnl > 0:
            perf['win_count'] += 1
            
        perf['last_update'] = datetime.now()
        
    def select_strategies(self, signal: Signal, active_strategies: List[str]) -> List[str]:
        """Select which strategies should be active for a given signal"""
        selected_strategies = []
        
        for strategy in active_strategies:
            if self.is_strategy_suitable(strategy, signal):
                score = self.calculate_strategy_score(strategy, signal)
                # Only select if score is above threshold
                if score > 0.3:  # Adjustable threshold
                    selected_strategies.append(strategy)
        
        # Sort by score if we want to prioritize
        selected_strategies.sort(key=lambda s: self.calculate_strategy_score(s, signal), reverse=True)
        
        logger.debug(f"AdaptiveSelector selected strategies: {selected_strategies} for signal {signal.signal_type}")
        
        return selected_strategies
    
    def is_strategy_suitable(self, strategy_name: str, signal: Signal) -> bool:
        """Check if a strategy is suitable for the current signal"""
        # Check if strategy is enabled
        if not self.strategy_enabled.get(strategy_name, True):
            return False
            
        # Check if strategy supports this signal type
        # This would check strategy-specific configuration in a full implementation
        return True
    
    def calculate_strategy_score(self, strategy_name: str, signal: Signal) -> float:
        """Calculate a score for how good a strategy is for the current conditions"""
        # Start with performance-based score
        perf_score = self.get_performance_score(strategy_name)
        
        # Adjust based on market regime compatibility
        regime_score = self.get_regime_compatibility_score(strategy_name, signal)
        
        # Adjust based on signal characteristics
        signal_score = self.get_signal_compatibility_score(strategy_name, signal)
        
        # Combine scores (weighted average)
        combined_score = (perf_score * 0.5) + (regime_score * 0.3) + (signal_score * 0.2)
        
        # Ensure it's between 0 and 1
        return max(0.0, min(1.0, combined_score))
    
    def get_performance_score(self, strategy_name: str) -> float:
        """Get performance-based score for a strategy"""
        if strategy_name not in self.strategy_performance:
            return 0.5  # Neutral score for unknown strategies
            
        perf = self.strategy_performance[strategy_name]
        
        if perf['signals_count'] == 0:
            return 0.5
            
        # Calculate win rate
        win_rate = perf['win_count'] / perf['signals_count']
        
        # Calculate average PnL per signal
        avg_pnl = perf['total_pnl'] / perf['signals_count'] if perf['signals_count'] > 0 else 0
        
        # Normalize and combine metrics
        win_rate_score = min(1.0, max(0.0, win_rate))  # Keep between 0 and 1
        pnl_score = max(0.0, min(1.0, 0.5 + avg_pnl))  # Center around 0.5, range 0-1
        
        # Weighted combination
        return (win_rate_score * 0.6) + (pnl_score * 0.4)
    
    def get_regime_compatibility_score(self, strategy_name: str, signal: Signal) -> float:
        """Get score for how compatible the strategy is with current market regime"""
        # This would check the strategy's performance in similar market regimes
        # For now, return a neutral score
        if not hasattr(signal, 'regime') or not signal.metadata:
            return 0.5
            
        regime = signal.metadata.get('regime', 'normal')
        
        if strategy_name in self.regime_strategy_weights:
            return self.regime_strategy_weights[strategy_name].get(regime, 0.5)
        else:
            return 0.5
    
    def get_signal_compatibility_score(self, strategy_name: str, signal: Signal) -> float:
        """Get score for how compatible the strategy is with the current signal"""
        # Higher confidence signals might be better for more selective strategies
        # This is a simplified version
        return signal.confidence
    
    def auto_disable_poor_strategies(self, threshold: float = -0.1, min_signals: int = 10):
        """Automatically disable strategies that are performing poorly"""
        for strategy_name, perf in self.strategy_performance.items():
            if perf['signals_count'] >= min_signals:
                avg_pnl = perf['total_pnl'] / perf['signals_count']
                
                if avg_pnl < threshold and self.strategy_enabled[strategy_name]:
                    self.strategy_enabled[strategy_name] = False
                    logger.info(f"Disabled strategy {strategy_name} due to poor performance (avg_pnl: {avg_pnl:.4f})")
    
    def get_strategy_recommendations(self) -> Dict[str, float]:
        """Get recommendation scores for all strategies"""
        recommendations = {}
        for strategy in self.strategy_performance.keys():
            recommendations[strategy] = self.calculate_strategy_score(strategy, 
                Signal("DUMMY", SignalType.HOLD, 0.5, 0.0, "mock", datetime.now()))
        return recommendations