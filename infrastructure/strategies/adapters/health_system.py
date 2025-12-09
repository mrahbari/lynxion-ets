from typing import Dict, List, Optional
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime, timedelta
import numpy as np


class HealthSystem:
    """Monitors and manages the health of strategies"""
    
    def __init__(self, 
                 performance_decay: float = 0.98,
                 max_drawdown_threshold: float = 0.1,  # 10% max drawdown
                 min_profit_threshold: float = -0.05,  # -5% min profit
                 signal_frequency_threshold: int = 5):  # Min signals per day to remain active
        self.performance_decay = performance_decay
        self.max_drawdown_threshold = max_drawdown_threshold
        self.min_profit_threshold = min_profit_threshold
        self.signal_frequency_threshold = signal_frequency_threshold
        
        # Strategy health tracking
        self.strategy_health: Dict[str, Dict] = {}
        self.strategy_signals_history: Dict[str, List[Dict]] = {}
        self.strategy_performance_history: Dict[str, List[Dict]] = {}
        
    def update_strategy_health(self, strategy_name: str, pnl: float, signal: Signal):
        """Update the health metrics for a strategy"""
        if strategy_name not in self.strategy_health:
            self.strategy_health[strategy_name] = {
                'total_pnl': 0.0,
                'peak_pnl': 0.0,
                'current_drawdown': 0.0,
                'signals_count': 0,
                'win_count': 0,
                'last_signal_time': datetime.now(),
                'is_healthy': True,
                'consecutive_losses': 0,
                'avg_signal_confidence': 0.0
            }
            self.strategy_signals_history[strategy_name] = []
            self.strategy_performance_history[strategy_name] = []
        
        health = self.strategy_health[strategy_name]
        
        # Apply decay to historical performance
        health['total_pnl'] *= self.performance_decay
        
        # Update with new performance
        health['total_pnl'] += pnl
        health['signals_count'] += 1
        
        # Update peak PnL
        if health['total_pnl'] > health['peak_pnl']:
            health['peak_pnl'] = health['total_pnl']
        
        # Calculate drawdown
        health['current_drawdown'] = (health['peak_pnl'] - health['total_pnl']) / (abs(health['peak_pnl']) + 1) if health['peak_pnl'] != 0 else 0
        
        # Update win/loss count
        if pnl > 0:
            health['win_count'] += 1
            health['consecutive_losses'] = 0
        else:
            health['consecutive_losses'] += 1
            
        # Update average signal confidence
        health['avg_signal_confidence'] = (
            (health['avg_signal_confidence'] * (health['signals_count'] - 1) + signal.confidence) / 
            health['signals_count']
        )
        
        health['last_signal_time'] = datetime.now()
        
        # Evaluate health status
        health['is_healthy'] = self._evaluate_health(strategy_name)
        
        # Add to history
        self.strategy_signals_history[strategy_name].append({
            'timestamp': datetime.now(),
            'pnl': pnl,
            'confidence': signal.confidence,
            'signal_type': signal.signal_type
        })
        
        # Keep history to last 100 entries
        if len(self.strategy_signals_history[strategy_name]) > 100:
            self.strategy_signals_history[strategy_name] = self.strategy_signals_history[strategy_name][-100:]
        
        # Log if strategy health changed significantly
        if not health['is_healthy']:
            logger.warning(f"Strategy {strategy_name} is no longer healthy. Drawdown: {health['current_drawdown']:.3f}, "
                          f"Consecutive losses: {health['consecutive_losses']}, Total PnL: {health['total_pnl']:.4f}")
    
    def _evaluate_health(self, strategy_name: str) -> bool:
        """Evaluate if a strategy is healthy based on various metrics"""
        health = self.strategy_health[strategy_name]
        
        # Check drawdown
        if health['current_drawdown'] > self.max_drawdown_threshold:
            return False
            
        # Check overall performance
        if health['total_pnl'] < self.min_profit_threshold and health['signals_count'] > 10:
            return False
            
        # Check excessive consecutive losses
        if health['consecutive_losses'] > 5:
            return False
            
        # Check signal activity (not too long without signals)
        time_since_last = datetime.now() - health['last_signal_time']
        if time_since_last > timedelta(hours=24) and health['signals_count'] > 5:
            # No signals in 24 hours for a mature strategy
            return False
            
        return True
    
    def get_strategy_health_status(self, strategy_name: str) -> Dict:
        """Get detailed health status for a strategy"""
        if strategy_name not in self.strategy_health:
            return {
                'is_healthy': True,
                'reasons': ['Strategy not yet evaluated']
            }
        
        health = self.strategy_health[strategy_name]
        reasons = []
        
        if health['current_drawdown'] > self.max_drawdown_threshold:
            reasons.append(f"Drawdown too high: {health['current_drawdown']:.3f} > {self.max_drawdown_threshold}")
            
        if health['total_pnl'] < self.min_profit_threshold and health['signals_count'] > 10:
            reasons.append(f"Performance below threshold: {health['total_pnl']:.4f} < {self.min_profit_threshold}")
            
        if health['consecutive_losses'] > 5:
            reasons.append(f"Too many consecutive losses: {health['consecutive_losses']}")
            
        if not reasons:
            reasons.append("All health metrics within acceptable ranges")
        
        return {
            'is_healthy': health['is_healthy'],
            'total_pnl': health['total_pnl'],
            'current_drawdown': health['current_drawdown'],
            'signals_count': health['signals_count'],
            'win_rate': health['win_count'] / health['signals_count'] if health['signals_count'] > 0 else 0,
            'consecutive_losses': health['consecutive_losses'],
            'avg_signal_confidence': health['avg_signal_confidence'],
            'last_signal_time': health['last_signal_time'],
            'reasons': reasons
        }
    
    def get_unhealthy_strategies(self) -> List[str]:
        """Get all strategies that are currently unhealthy"""
        unhealthy = []
        for strategy, health in self.strategy_health.items():
            if not health['is_healthy']:
                unhealthy.append(strategy)
        return unhealthy
    
    def get_overall_health_score(self) -> float:
        """Get an overall health score for all strategies (0-1 scale)"""
        if not self.strategy_health:
            return 1.0
            
        healthy_count = sum(1 for health in self.strategy_health.values() if health['is_healthy'])
        return healthy_count / len(self.strategy_health)
    
    def should_disable_strategy(self, strategy_name: str) -> bool:
        """Determine if a strategy should be disabled based on health"""
        if strategy_name not in self.strategy_health:
            return False
            
        health = self.strategy_health[strategy_name]
        
        # Check if drawdown exceeds threshold
        if health['current_drawdown'] >= self.max_drawdown_threshold:
            return True
            
        # Check if performance is very poor
        if health['total_pnl'] < (self.min_profit_threshold * 2) and health['signals_count'] > 20:
            return True
            
        # Check for excessive consecutive losses
        if health['consecutive_losses'] > 10:
            return True
            
        return False
    
    def auto_heal_strategies(self, performance_benchmark: float = 0.0) -> List[str]:
        """Attempt to auto-heal strategies with poor performance"""
        recovered_strategies = []
        
        for strategy_name, health in self.strategy_health.items():
            if not health['is_healthy']:
                # Check if the strategy has improved recently
                recent_pnl = self._calculate_recent_performance(strategy_name)
                
                if recent_pnl > performance_benchmark:
                    # Strategy is showing improvement, mark as healthy again
                    health['is_healthy'] = True
                    health['consecutive_losses'] = 0
                    recovered_strategies.append(strategy_name)
                    logger.info(f"Auto-healed strategy {strategy_name} based on recent improvement")
        
        return recovered_strategies
    
    def _calculate_recent_performance(self, strategy_name: str, lookback: int = 10) -> float:
        """Calculate recent performance for a strategy"""
        signals = self.strategy_signals_history.get(strategy_name, [])
        if len(signals) < lookback:
            lookback = len(signals)
            
        if lookback == 0:
            return 0.0
            
        recent_pnl = sum(signal['pnl'] for signal in signals[-lookback:])
        return recent_pnl / lookback if lookback > 0 else 0.0
    
    def reset_strategy_health(self, strategy_name: str):
        """Reset health metrics for a strategy"""
        if strategy_name in self.strategy_health:
            self.strategy_health[strategy_name] = {
                'total_pnl': 0.0,
                'peak_pnl': 0.0,
                'current_drawdown': 0.0,
                'signals_count': 0,
                'win_count': 0,
                'last_signal_time': datetime.now(),
                'is_healthy': True,
                'consecutive_losses': 0,
                'avg_signal_confidence': 0.0
            }
            self.strategy_signals_history[strategy_name] = []
            logger.info(f"Reset health metrics for strategy {strategy_name}")