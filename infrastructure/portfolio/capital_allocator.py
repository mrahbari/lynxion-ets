"""
Capital Allocator - Dynamic capital allocation system based on strategy performance metrics,
market regime, correlation, and risk factors.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from shared.logger import EnhancedLogger


@dataclass
class StrategyPerformance:
    """Data class to hold strategy performance metrics."""
    rolling_sharpe: float
    expectancy: float
    regime_match_score: float
    correlation_penalty: float
    drawdown_penalty: float
    trade_count: int
    win_rate: float
    profit_factor: float
    timestamp: datetime


class CapitalAllocator:
    """
    Dynamic capital allocation system that distributes capital based on strategy performance,
    market regime alignment, correlation penalties, and risk factors.
    """
    
    def __init__(self, 
                 total_capital: float = 100000.0,
                 min_allocation: float = 0.01,  # 1% minimum allocation
                 max_allocation: float = 0.30,  # 30% maximum allocation per strategy
                 regime_weights: Dict[str, float] = None):
        
        self.total_capital = total_capital
        self.min_allocation = min_allocation
        self.max_allocation = max_allocation
        
        # Default regime weights if not provided
        if regime_weights is None:
            self.regime_weights = {
                'TREND': 0.40,        # 40% capital for trending markets
                'RANGE': 0.30,        # 30% capital for ranging markets
                'HIGH_VOL': 0.20,     # 20% capital for high volatility
                'LOW_VOL': 0.10       # 10% capital for low volatility
            }
        else:
            self.regime_weights = regime_weights
        
        self.logger = EnhancedLogger("CapitalAllocator")
        
        # Strategy performance tracking
        self.strategy_performance: Dict[str, List[StrategyPerformance]] = {}
        self.current_allocations: Dict[str, float] = {}
        self.regime_classification: Dict[str, str] = {}
        
    def update_strategy_performance(self, 
                                  strategy_name: str, 
                                  performance_metrics: Dict[str, Any],
                                  timestamp: datetime = None):
        """Update performance metrics for a strategy."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create StrategyPerformance object
        perf = StrategyPerformance(
            rolling_sharpe=performance_metrics.get('rolling_sharpe', 0),
            expectancy=performance_metrics.get('expectancy', 0),
            regime_match_score=performance_metrics.get('regime_match_score', 0.5),
            correlation_penalty=performance_metrics.get('correlation_penalty', 0),
            drawdown_penalty=performance_metrics.get('drawdown_penalty', 0),
            trade_count=performance_metrics.get('trade_count', 0),
            win_rate=performance_metrics.get('win_rate', 0),
            profit_factor=performance_metrics.get('profit_factor', 1.0),
            timestamp=timestamp
        )
        
        # Add to performance history
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = []
        self.strategy_performance[strategy_name].append(perf)
        
        # Keep only recent performance data (last 30 days)
        cutoff_time = timestamp - pd.Timedelta(days=30)
        self.strategy_performance[strategy_name] = [
            p for p in self.strategy_performance[strategy_name]
            if p.timestamp >= cutoff_time
        ]
    
    def update_regime_classification(self, symbol_regimes: Dict[str, str]):
        """Update market regime classifications."""
        self.regime_classification.update(symbol_regimes)
        self.logger.info(f"Updated regime classifications for {len(symbol_regimes)} symbols")
    
    def calculate_base_weights(self, strategy_names: List[str]) -> Dict[str, float]:
        """Calculate base weights based on performance metrics."""
        if not strategy_names:
            return {}
        
        # Get latest performance for each strategy
        base_weights = {}
        
        for strategy_name in strategy_names:
            if strategy_name in self.strategy_performance and self.strategy_performance[strategy_name]:
                latest_perf = self.strategy_performance[strategy_name][-1]
                
                # Calculate composite score based on multiple factors
                # Normalize each factor to 0-1 scale
                normalized_sharpe = max(0, min(1, (latest_perf.rolling_sharpe + 2) / 4))  # Assuming -2 to 2 range
                normalized_expectancy = max(0, min(1, (latest_perf.expectancy + 0.1) / 0.5))  # Assuming -0.1 to 0.4 range
                normalized_win_rate = latest_perf.win_rate
                normalized_pf = max(0, min(1, (latest_perf.profit_factor - 0.5) / 2.5))  # Assuming 0.5 to 3.0 range
                
                # Composite score
                composite_score = (
                    normalized_sharpe * 0.3 +
                    normalized_expectancy * 0.3 +
                    normalized_win_rate * 0.2 +
                    normalized_pf * 0.2
                )
                
                base_weights[strategy_name] = max(0, composite_score)
            else:
                # Default weight for strategies without performance data
                base_weights[strategy_name] = 0.1  # Low default weight
        
        # Normalize weights to sum to 1
        total_weight = sum(base_weights.values())
        if total_weight > 0:
            for strategy_name in base_weights:
                base_weights[strategy_name] /= total_weight
        else:
            # Equal weights if all scores are zero
            for strategy_name in base_weights:
                base_weights[strategy_name] = 1.0 / len(base_weights)
        
        return base_weights
    
    def apply_correlation_penalties(self, 
                                  base_weights: Dict[str, float], 
                                  correlation_matrix: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """Apply correlation penalties to base weights."""
        if correlation_matrix is None or correlation_matrix.empty:
            return base_weights
        
        # Apply penalties based on correlation with other strategies
        penalized_weights = base_weights.copy()
        
        for strategy_name in penalized_weights:
            # Find correlations with other strategies
            if strategy_name in correlation_matrix.columns:
                other_strategies = [col for col in correlation_matrix.columns if col != strategy_name]
                
                if other_strategies:
                    correlations = []
                    for other_strategy in other_strategies:
                        if other_strategy in correlation_matrix.index:
                            corr_val = correlation_matrix.loc[strategy_name, other_strategy]
                            if not pd.isna(corr_val):
                                correlations.append(abs(corr_val))
                    
                    if correlations:
                        avg_correlation = np.mean(correlations)
                        # Apply penalty for high correlation (reduce weight)
                        penalty_factor = max(0.1, 1.0 - avg_correlation)
                        penalized_weights[strategy_name] *= penalty_factor
        
        # Renormalize after applying penalties
        total_weight = sum(penalized_weights.values())
        if total_weight > 0:
            for strategy_name in penalized_weights:
                penalized_weights[strategy_name] /= total_weight
        else:
            # Fallback to equal weights
            for strategy_name in penalized_weights:
                penalized_weights[strategy_name] = 1.0 / len(penalized_weights)
        
        return penalized_weights
    
    def apply_regime_adjustments(self, 
                               weights: Dict[str, float], 
                               strategy_regime_preferences: Dict[str, List[str]] = None) -> Dict[str, float]:
        """Apply regime-based adjustments to weights."""
        if not self.regime_classification:
            return weights
        
        # Determine dominant regime from symbol classifications
        regime_counts = {}
        for regime_info in self.regime_classification.values():
            # regime_info is a dict, we need the 'regime' value from it
            if isinstance(regime_info, dict) and 'regime' in regime_info:
                regime = regime_info['regime']
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
            else:
                # If it's not a dict or doesn't have 'regime', treat as string
                regime = regime_info if isinstance(regime_info, str) else 'unknown'
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        if not regime_counts:
            return weights
        
        dominant_regime = max(regime_counts, key=regime_counts.get)
        regime_weight = self.regime_weights.get(dominant_regime, 0.5)  # Default to 50%
        
        # Apply regime adjustments based on strategy preferences if provided
        adjusted_weights = weights.copy()
        
        if strategy_regime_preferences:
            for strategy_name, preferred_regimes in strategy_regime_preferences.items():
                if strategy_name in adjusted_weights:
                    if dominant_regime in preferred_regimes:
                        # Boost weight for strategies that match current regime
                        boost_factor = 1.2  # 20% boost
                    else:
                        # Reduce weight for strategies that don't match current regime
                        boost_factor = 0.8  # 20% reduction
                    
                    adjusted_weights[strategy_name] *= boost_factor
        
        # Renormalize after regime adjustments
        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            for strategy_name in adjusted_weights:
                adjusted_weights[strategy_name] /= total_weight
        else:
            # Fallback to equal weights
            for strategy_name in adjusted_weights:
                adjusted_weights[strategy_name] = 1.0 / len(adjusted_weights)
        
        return adjusted_weights
    
    def apply_drawdown_penalties(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Apply penalties based on recent drawdowns."""
        penalized_weights = weights.copy()
        
        for strategy_name in penalized_weights:
            if strategy_name in self.strategy_performance and self.strategy_performance[strategy_name]:
                latest_perf = self.strategy_performance[strategy_name][-1]
                
                # Apply penalty based on drawdown
                drawdown_penalty = latest_perf.drawdown_penalty
                penalized_weights[strategy_name] *= (1 - drawdown_penalty)
        
        # Renormalize after applying penalties
        total_weight = sum(penalized_weights.values())
        if total_weight > 0:
            for strategy_name in penalized_weights:
                penalized_weights[strategy_name] = max(
                    self.min_allocation,
                    min(self.max_allocation, penalized_weights[strategy_name] / total_weight)
                )
        
        # Ensure weights sum to 1 and respect bounds
        return self._enforce_constraints(penalized_weights)
    
    def _enforce_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Enforce minimum and maximum allocation constraints."""
        # First, ensure no weight is below minimum
        for strategy_name in weights:
            weights[strategy_name] = max(self.min_allocation, weights[strategy_name])
        
        # If any weights exceed maximum, clip them and redistribute
        excess = 0
        for strategy_name in weights:
            if weights[strategy_name] > self.max_allocation:
                excess += weights[strategy_name] - self.max_allocation
                weights[strategy_name] = self.max_allocation
        
        # Redistribute excess proportionally among strategies that are below max
        if excess > 0:
            eligible_strategies = [name for name, weight in weights.items() 
                                 if weight < self.max_allocation]
            if eligible_strategies:
                redistribution = excess / len(eligible_strategies)
                for strategy_name in eligible_strategies:
                    new_weight = min(self.max_allocation, weights[strategy_name] + redistribution)
                    weights[strategy_name] = new_weight
                    # Update excess if we hit the max
                    if new_weight == self.max_allocation:
                        excess -= (new_weight - weights[strategy_name])
        
        # Final normalization to ensure sum is approximately 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            for strategy_name in weights:
                weights[strategy_name] /= total_weight
        
        # Final check to ensure constraints are met
        for strategy_name in weights:
            weights[strategy_name] = max(self.min_allocation, 
                                       min(self.max_allocation, weights[strategy_name]))
        
        return weights
    
    def calculate_allocations(self, 
                            strategy_names: List[str],
                            correlation_matrix: Optional[pd.DataFrame] = None,
                            strategy_regime_preferences: Dict[str, List[str]] = None) -> Dict[str, float]:
        """Calculate final capital allocations for strategies."""
        
        # Step 1: Calculate base weights based on performance
        base_weights = self.calculate_base_weights(strategy_names)
        
        # Step 2: Apply correlation penalties
        correlation_adjusted = self.apply_correlation_penalties(base_weights, correlation_matrix)
        
        # Step 3: Apply regime adjustments
        regime_adjusted = self.apply_regime_adjustments(correlation_adjusted, strategy_regime_preferences)
        
        # Step 4: Apply drawdown penalties
        final_weights = self.apply_drawdown_penalties(regime_adjusted)
        
        # Convert weights to dollar amounts
        allocations = {}
        for strategy_name, weight in final_weights.items():
            allocations[strategy_name] = weight * self.total_capital
        
        # Store current allocations
        self.current_allocations = allocations.copy()
        
        self.logger.info(f"Calculated allocations for {len(strategy_names)} strategies")
        
        return allocations
    
    def get_allocation_summary(self) -> Dict[str, Any]:
        """Get a summary of current allocations."""
        total_allocated = sum(self.current_allocations.values())
        
        summary = {
            'total_capital': self.total_capital,
            'total_allocated': total_allocated,
            'allocation_efficiency': total_allocated / self.total_capital if self.total_capital > 0 else 0,
            'strategy_count': len(self.current_allocations),
            'allocations': self.current_allocations.copy(),
            'weights': {k: v/self.total_capital for k, v in self.current_allocations.items()}
        }
        
        return summary
    
    def rebalance_if_needed(self, 
                          strategy_names: List[str],
                          correlation_matrix: Optional[pd.DataFrame] = None,
                          strategy_regime_preferences: Dict[str, List[str]] = None,
                          rebalance_threshold: float = 0.05) -> Dict[str, float]:
        """Rebalance allocations if changes exceed threshold."""
        
        # Calculate new allocations
        new_allocations = self.calculate_allocations(
            strategy_names, 
            correlation_matrix, 
            strategy_regime_preferences
        )
        
        # Check if rebalancing is needed
        max_change = 0
        for strategy_name in new_allocations:
            old_alloc = self.current_allocations.get(strategy_name, 0)
            new_alloc = new_allocations[strategy_name]
            alloc_change = abs(new_alloc - old_alloc) / self.total_capital
            
            if alloc_change > max_change:
                max_change = alloc_change
        
        if max_change > rebalance_threshold:
            self.logger.info(f"Rebalancing triggered - max change: {max_change:.2%}")
            return new_allocations
        else:
            self.logger.info(f"No rebalancing needed - max change: {max_change:.2%} < threshold {rebalance_threshold:.2%}")
            return self.current_allocations


def create_capital_allocator_from_backtest_results(
    backtest_results: Dict[str, Any], 
    total_capital: float = 100000.0
) -> CapitalAllocator:
    """
    Create and initialize a capital allocator from backtest results.
    """
    logger = EnhancedLogger("CapitalAllocatorInitializer")
    
    # Initialize capital allocator
    allocator = CapitalAllocator(total_capital=total_capital)
    
    # Extract strategy names and performance metrics from backtest results
    strategy_names = []
    
    if 'individual_results' in backtest_results:
        # Portfolio backtest results
        for strategy_name, strategy_results in backtest_results['individual_results'].items():
            strategy_names.append(strategy_name)
            
            # Aggregate performance metrics across all symbols for this strategy
            total_return = 0
            total_trades = 0
            total_pnl = 0
            all_pnl = []
            
            for symbol, result in strategy_results.items():
                if 'total_return' in result:
                    total_return += result['total_return']
                if 'total_trades' in result:
                    total_trades += result['total_trades']
                if 'trades' in result:
                    for trade in result['trades']:
                        if 'pnl' in trade:
                            all_pnl.append(trade['pnl'])
                            total_pnl += trade['pnl']
            
            if all_pnl:
                # Calculate derived metrics
                avg_return = total_return / len(strategy_results) if strategy_results else 0
                expectancy = np.mean(all_pnl) if all_pnl else 0
                win_rate = sum(1 for pnl in all_pnl if pnl > 0) / len(all_pnl) if all_pnl else 0
                profit_factor = (sum(pnl for pnl in all_pnl if pnl > 0) / 
                               abs(sum(pnl for pnl in all_pnl if pnl < 0))) if all_pnl else 1.0
                
                # Calculate Sharpe ratio (simplified)
                returns = [pnl for pnl in all_pnl if pnl != 0]  # Non-zero returns
                if len(returns) > 1:
                    avg_return_calc = np.mean(returns)
                    std_return = np.std(returns)
                    sharpe = avg_return_calc / std_return if std_return != 0 else 0
                else:
                    sharpe = 0
                
                # Calculate max drawdown (simplified)
                cumulative = np.cumsum(all_pnl)
                if len(cumulative) > 0:
                    running_max = np.maximum.accumulate(cumulative)
                    drawdowns = cumulative - running_max
                    max_dd = np.min(drawdowns) / abs(cumulative[0]) if cumulative[0] != 0 else 0
                else:
                    max_dd = 0
                
                # Calculate penalties (simplified)
                correlation_penalty = 0.1  # Placeholder
                drawdown_penalty = max(0, min(0.5, abs(max_dd) / 0.2))  # Penalty increases with drawdown
                
                # Regime match score (placeholder)
                regime_match_score = 0.7  # Placeholder
                
                # Update strategy performance
                performance_metrics = {
                    'rolling_sharpe': sharpe,
                    'expectancy': expectancy,
                    'regime_match_score': regime_match_score,
                    'correlation_penalty': correlation_penalty,
                    'drawdown_penalty': drawdown_penalty,
                    'trade_count': len(all_pnl),
                    'win_rate': win_rate,
                    'profit_factor': profit_factor
                }
                
                allocator.update_strategy_performance(strategy_name, performance_metrics)
    
    elif 'strategy_rankings' in backtest_results:
        # Ranking-based results
        for ranking in backtest_results['strategy_rankings']:
            strategy_name = ranking['strategy']
            strategy_names.append(strategy_name)
            
            # Use ranking metrics as performance indicators
            performance_metrics = {
                'rolling_sharpe': ranking.get('avg_sharpe', 0),
                'expectancy': ranking.get('avg_return', 0) * ranking.get('avg_win_rate', 0.5),  # Simplified expectancy
                'regime_match_score': 0.7,  # Placeholder
                'correlation_penalty': 0.1,  # Placeholder
                'drawdown_penalty': max(0, min(0.5, abs(ranking.get('avg_drawdown', 0)) / 0.2)),  # Penalty increases with drawdown
                'trade_count': 50,  # Placeholder
                'win_rate': ranking.get('avg_win_rate', 0.5),
                'profit_factor': 1.5  # Placeholder
            }
            
            allocator.update_strategy_performance(strategy_name, performance_metrics)
    
    # Update regime classification if available
    if 'regime_classification' in backtest_results:
        allocator.update_regime_classification(backtest_results['regime_classification'])
    
    logger.info(f"Initialized capital allocator with {len(strategy_names)} strategies")
    
    return allocator