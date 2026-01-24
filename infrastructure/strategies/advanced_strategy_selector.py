"""
Advanced Strategy Selection with performance-ranking, risk-adjustment, and regime-compatibility features.
Implements promotion/demotion/suspension rules with scoring formula.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import statistics
import warnings
warnings.filterwarnings('ignore')


class StrategyStatus(Enum):
    """Strategy status enumeration"""
    ACTIVE = "active"
    DEMOTED = "demoted"
    SUSPENDED = "suspended"
    PROMOTED = "promoted"


@dataclass
class StrategyMetrics:
    """Container for strategy metrics"""
    name: str
    performance_score: float
    risk_adjusted_return: float
    win_rate: float
    avg_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    correlation_with_portfolio: float
    regime_compatibility_score: float
    status: StrategyStatus
    last_updated: datetime


class AdvancedStrategySelector:
    """
    Advanced strategy selection with:
    - Performance ranking
    - Regime compatibility
    - Risk adjustment
    - Promotion/demotion/suspension rules
    """
    
    def __init__(self,
                 performance_decay_factor: float = 0.95,
                 risk_free_rate: float = 0.02,  # Annual risk-free rate
                 max_drawdown_threshold: float = 0.15,  # 15% max drawdown
                 min_win_rate: float = 0.4,  # 40% minimum win rate
                 correlation_threshold: float = 0.7,  # Max correlation with portfolio
                 performance_window: int = 30,  # Days for performance calculation
                 ranking_window: int = 7,  # Days for ranking recalculation
                 suspension_threshold: float = -0.1,  # Suspend if performance below this
                 demotion_threshold: float = 0.0,  # Demote if performance below this
                 promotion_threshold: float = 0.05):  # Promote if performance above this
        
        self.performance_decay_factor = performance_decay_factor
        self.risk_free_rate = risk_free_rate
        self.max_drawdown_threshold = max_drawdown_threshold
        self.min_win_rate = min_win_rate
        self.correlation_threshold = correlation_threshold
        self.performance_window = performance_window
        self.ranking_window = ranking_window
        self.suspension_threshold = suspension_threshold
        self.demotion_threshold = demotion_threshold
        self.promotion_threshold = promotion_threshold
        
        # Track strategy performance
        self.strategy_performance: Dict[str, List[Dict[str, Any]]] = {}
        self.strategy_correlations: Dict[str, float] = {}
        self.strategy_regime_compatibility: Dict[str, Dict[str, float]] = {}
        self.strategy_status: Dict[str, StrategyStatus] = {}
        self.strategy_rankings: List[Tuple[str, float]] = []
        self.last_ranking_update = datetime.now()
        
        # Track regime context
        self.current_regime: Optional[str] = None

    def update_strategy_performance(self, 
                                 strategy_name: str, 
                                 returns: List[float],
                                 win_rate: float,
                                 max_drawdown: float,
                                 volatility: float,
                                 correlation_with_portfolio: float,
                                 regime_context: Optional[str] = None,
                                 timestamp: Optional[datetime] = None):
        """Update performance data for a strategy."""
        if timestamp is None:
            timestamp = datetime.now()
            
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = []
            
        # Calculate additional metrics
        avg_return = np.mean(returns) if returns else 0
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        risk_adjusted_return = self._calculate_risk_adjusted_return(returns, volatility)
        
        performance_record = {
            'returns': returns,
            'avg_return': avg_return,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'risk_adjusted_return': risk_adjusted_return,
            'correlation_with_portfolio': correlation_with_portfolio,
            'regime_context': regime_context,
            'timestamp': timestamp
        }
        
        self.strategy_performance[strategy_name].append(performance_record)
        
        # Update correlation
        self.strategy_correlations[strategy_name] = correlation_with_portfolio
        
        # Update regime compatibility if regime context is provided
        if regime_context:
            if strategy_name not in self.strategy_regime_compatibility:
                self.strategy_regime_compatibility[strategy_name] = {}
            if regime_context not in self.strategy_regime_compatibility[strategy_name]:
                self.strategy_regime_compatibility[strategy_name][regime_context] = []
            
            # Add performance score for this regime
            self.strategy_regime_compatibility[strategy_name][regime_context].append(avg_return)
            
            # Keep only recent data
            cutoff = timestamp - timedelta(days=60)
            self.strategy_regime_compatibility[strategy_name][regime_context] = [
                score for score in self.strategy_regime_compatibility[strategy_name][regime_context][-30:]
            ]
        
        # Keep only recent performance data
        cutoff = timestamp - timedelta(days=self.performance_window)
        self.strategy_performance[strategy_name] = [
            record for record in self.strategy_performance[strategy_name]
            if record['timestamp'] >= cutoff
        ]

    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio."""
        if not returns or len(returns) < 2:
            return 0.0
            
        avg_return = np.mean(returns)
        volatility = np.std(returns)
        
        if volatility == 0:
            return 0.0
            
        # Convert to annualized Sharpe ratio
        excess_return = avg_return - (self.risk_free_rate / 252)  # Daily risk-free rate
        sharpe = excess_return / volatility if volatility > 0 else 0.0
        
        return sharpe * np.sqrt(252)  # Annualize

    def _calculate_risk_adjusted_return(self, returns: List[float], volatility: float) -> float:
        """Calculate risk-adjusted return."""
        if not returns:
            return 0.0
            
        avg_return = np.mean(returns)
        
        if volatility == 0:
            return avg_return
            
        # Risk-adjusted return = return / volatility (similar to Sharpe but simpler)
        return avg_return / volatility if volatility > 0 else avg_return

    def calculate_strategy_score(self, strategy_name: str) -> float:
        """Calculate comprehensive score for a strategy."""
        if strategy_name not in self.strategy_performance:
            return 0.0
            
        # Get recent performance data
        recent_data = self.strategy_performance[strategy_name][-10:]  # Last 10 records
        if not recent_data:
            return 0.0
            
        # Calculate weighted average of recent performance
        total_weight = 0.0
        weighted_score = 0.0
        
        for i, record in enumerate(reversed(recent_data)):
            weight = (self.performance_decay_factor ** i)  # More recent = higher weight
            performance_component = self._calculate_performance_component(record)
            risk_component = self._calculate_risk_component(record)
            correlation_component = self._calculate_correlation_component(strategy_name)
            regime_component = self._calculate_regime_component(strategy_name, record.get('regime_context'))
            
            # Combine components
            strategy_score = (0.4 * performance_component + 
                            0.3 * risk_component + 
                            0.2 * correlation_component + 
                            0.1 * regime_component)
            
            weighted_score += strategy_score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
            
        final_score = weighted_score / total_weight
        
        # Apply status-based adjustments
        status = self.strategy_status.get(strategy_name, StrategyStatus.ACTIVE)
        if status == StrategyStatus.DEMOTED:
            final_score *= 0.8  # Reduce score for demoted strategies
        elif status == StrategyStatus.SUSPENDED:
            final_score *= 0.1  # Severely reduce score for suspended strategies
        
        return final_score

    def _calculate_performance_component(self, record: Dict[str, Any]) -> float:
        """Calculate performance-based component of score."""
        # Normalize components to 0-1 range
        avg_return_norm = max(0, min(1, (record['avg_return'] + 0.02) * 20))  # Assuming -2% to +3% range maps to 0-1
        win_rate_norm = max(0, min(1, record['win_rate']))
        sharpe_norm = max(0, min(1, (record['sharpe_ratio'] + 2) / 6))  # Assuming -2 to 4 range maps to 0-1
        
        # Weighted combination
        return (0.5 * avg_return_norm + 0.3 * win_rate_norm + 0.2 * sharpe_norm)

    def _calculate_risk_component(self, record: Dict[str, Any]) -> float:
        """Calculate risk-based component of score."""
        # Lower drawdown and volatility = higher score
        drawdown_score = max(0, min(1, (self.max_drawdown_threshold - record['max_drawdown']) / self.max_drawdown_threshold))
        volatility_score = max(0, min(1, (0.05 - record['volatility']) / 0.05)) if record['volatility'] <= 0.05 else 0
        
        return (0.6 * drawdown_score + 0.4 * volatility_score)

    def _calculate_correlation_component(self, strategy_name: str) -> float:
        """Calculate correlation-based component of score."""
        correlation = self.strategy_correlations.get(strategy_name, 0.5)
        # Lower correlation = higher score
        correlation_score = max(0, min(1, (self.correlation_threshold - correlation) / self.correlation_threshold))
        return correlation_score

    def _calculate_regime_component(self, strategy_name: str, regime_context: Optional[str]) -> float:
        """Calculate regime compatibility component of score."""
        if not regime_context or strategy_name not in self.strategy_regime_compatibility:
            return 0.5  # Neutral score if no regime data
            
        if regime_context not in self.strategy_regime_compatibility[strategy_name]:
            return 0.5  # Neutral score if no data for this regime
            
        # Calculate average performance in this regime
        regime_returns = self.strategy_regime_compatibility[strategy_name][regime_context]
        if not regime_returns:
            return 0.5
            
        avg_regime_performance = np.mean(regime_returns)
        # Normalize to 0-1 range
        regime_score = max(0, min(1, (avg_regime_performance + 0.02) * 20))  # Similar to performance component
        return regime_score

    def update_strategy_status(self, strategy_name: str) -> StrategyStatus:
        """Update strategy status based on performance."""
        score = self.calculate_strategy_score(strategy_name)
        
        # Check for suspension criteria
        if strategy_name in self.strategy_performance:
            recent_data = self.strategy_performance[strategy_name][-5:]  # Last 5 records
            if recent_data:
                # Check if consistently underperforming
                recent_scores = [self._calculate_performance_component(rd) for rd in recent_data]
                avg_recent_score = np.mean(recent_scores) if recent_scores else 0
                
                if avg_recent_score < self.suspension_threshold and score < self.suspension_threshold:
                    new_status = StrategyStatus.SUSPENDED
                elif score < self.demotion_threshold:
                    new_status = StrategyStatus.DEMOTED
                elif score > self.promotion_threshold:
                    new_status = StrategyStatus.PROMOTED
                else:
                    new_status = StrategyStatus.ACTIVE
            else:
                new_status = StrategyStatus.ACTIVE
        else:
            new_status = StrategyStatus.ACTIVE
        
        self.strategy_status[strategy_name] = new_status
        return new_status

    def get_strategy_rankings(self) -> List[Tuple[str, float]]:
        """Get current strategy rankings."""
        # Update rankings if needed
        if datetime.now() - self.last_ranking_update > timedelta(days=self.ranking_window):
            self._recalculate_rankings()
            
        return self.strategy_rankings

    def _recalculate_rankings(self):
        """Recalculate strategy rankings."""
        if not self.strategy_performance:
            self.strategy_rankings = []
            return
            
        # Calculate scores for all strategies
        scores = []
        for strategy_name in self.strategy_performance.keys():
            score = self.calculate_strategy_score(strategy_name)
            scores.append((strategy_name, score))
        
        # Sort by score (descending)
        self.strategy_rankings = sorted(scores, key=lambda x: x[1], reverse=True)
        self.last_ranking_update = datetime.now()

    def select_best_strategy(self, available_strategies: List[str], regime_context: Optional[str] = None) -> Optional[str]:
        """Select the best strategy based on current conditions."""
        if not available_strategies:
            return None
            
        # Set current regime context
        self.current_regime = regime_context
        
        # Get rankings
        rankings = self.get_strategy_rankings()
        
        # Filter to available strategies and get the best one
        available_rankings = [(name, score) for name, score in rankings if name in available_strategies]
        
        if not available_rankings:
            # If no ranked strategies are available, return the first available one
            return available_strategies[0]
        
        # Return the highest-ranked available strategy
        best_strategy, _ = available_rankings[0]
        return best_strategy

    def get_strategy_metrics(self, strategy_name: str) -> Optional[StrategyMetrics]:
        """Get detailed metrics for a strategy."""
        if strategy_name not in self.strategy_performance:
            return None
            
        recent_data = self.strategy_performance[strategy_name][-1] if self.strategy_performance[strategy_name] else None
        if not recent_data:
            return None
            
        score = self.calculate_strategy_score(strategy_name)
        status = self.strategy_status.get(strategy_name, StrategyStatus.ACTIVE)
        
        return StrategyMetrics(
            name=strategy_name,
            performance_score=score,
            risk_adjusted_return=recent_data['risk_adjusted_return'],
            win_rate=recent_data['win_rate'],
            avg_return=recent_data['avg_return'],
            sharpe_ratio=recent_data['sharpe_ratio'],
            max_drawdown=recent_data['max_drawdown'],
            volatility=recent_data['volatility'],
            correlation_with_portfolio=self.strategy_correlations.get(strategy_name, 0.0),
            regime_compatibility_score=self._calculate_regime_compatibility_score(strategy_name, recent_data.get('regime_context')),
            status=status,
            last_updated=recent_data['timestamp']
        )

    def _calculate_regime_compatibility_score(self, strategy_name: str, regime_context: Optional[str]) -> float:
        """Calculate regime compatibility score."""
        if not regime_context or strategy_name not in self.strategy_regime_compatibility:
            return 0.5
            
        if regime_context not in self.strategy_regime_compatibility[strategy_name]:
            return 0.5
            
        regime_returns = self.strategy_regime_compatibility[strategy_name][regime_context]
        if not regime_returns:
            return 0.5
            
        avg_performance = np.mean(regime_returns)
        # Normalize to 0-1 range
        return max(0, min(1, (avg_performance + 0.02) * 20))

    def get_promotion_demotion_candidates(self) -> Dict[str, List[str]]:
        """Get candidates for promotion, demotion, and suspension."""
        candidates = {
            'promotion': [],
            'demotion': [],
            'suspension': []
        }
        
        for strategy_name in self.strategy_performance.keys():
            score = self.calculate_strategy_score(strategy_name)
            status = self.strategy_status.get(strategy_name, StrategyStatus.ACTIVE)
            
            # Only consider active strategies for promotion/demotion
            if status == StrategyStatus.ACTIVE:
                if score > self.promotion_threshold:
                    candidates['promotion'].append(strategy_name)
                elif score < self.demotion_threshold:
                    candidates['demotion'].append(strategy_name)
            elif status == StrategyStatus.SUSPENDED:
                # Check if suspended strategy has improved enough to be reconsidered
                if score > self.demotion_threshold:
                    candidates['suspension'].append(strategy_name)
        
        return candidates

    def apply_promotion_demotion_rules(self):
        """Apply promotion/demotion rules."""
        candidates = self.get_promotion_demotion_candidates()
        
        # Promote strategies
        for strategy in candidates['promotion']:
            self.strategy_status[strategy] = StrategyStatus.PROMOTED
            print(f"Promoting strategy: {strategy}")
        
        # Demote strategies
        for strategy in candidates['demotion']:
            self.strategy_status[strategy] = StrategyStatus.DEMOTED
            print(f"Demoting strategy: {strategy}")
        
        # Consider reactivating suspended strategies
        for strategy in candidates['suspension']:
            # Only reactivate if performance has significantly improved
            score = self.calculate_strategy_score(strategy)
            if score > self.promotion_threshold * 0.5:  # Half the promotion threshold
                self.strategy_status[strategy] = StrategyStatus.ACTIVE
                print(f"Reactivating suspended strategy: {strategy}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of strategy performance."""
        if not self.strategy_performance:
            return {}
        
        summary = {}
        for strategy_name in self.strategy_performance.keys():
            recent_data = self.strategy_performance[strategy_name][-1] if self.strategy_performance[strategy_name] else None
            if recent_data:
                summary[strategy_name] = {
                    'avg_return': recent_data['avg_return'],
                    'win_rate': recent_data['win_rate'],
                    'sharpe_ratio': recent_data['sharpe_ratio'],
                    'max_drawdown': recent_data['max_drawdown'],
                    'volatility': recent_data['volatility'],
                    'correlation': self.strategy_correlations.get(strategy_name, 0.0),
                    'status': self.strategy_status.get(strategy_name, StrategyStatus.ACTIVE).value,
                    'score': self.calculate_strategy_score(strategy_name)
                }
        
        return summary


class StrategySelectionService:
    """Service to manage strategy selection operations."""
    
    def __init__(self):
        self.selector = AdvancedStrategySelector()
        self.selection_history: List[Dict[str, Any]] = []
    
    def select_and_execute(self, 
                          available_strategies: List[str], 
                          market_data: Dict[str, Any],
                          regime_context: Optional[str] = None) -> Optional[str]:
        """Select strategy and record selection."""
        selected_strategy = self.selector.select_best_strategy(available_strategies, regime_context)
        
        # Record selection
        selection_record = {
            'timestamp': datetime.now(),
            'selected_strategy': selected_strategy,
            'available_strategies': available_strategies,
            'regime_context': regime_context,
            'rankings': self.selector.get_strategy_rankings()[:5]  # Top 5
        }
        self.selection_history.append(selection_record)
        
        return selected_strategy
    
    def update_strategy_feedback(self, 
                               strategy_name: str,
                               realized_returns: List[float],
                               win_rate: float,
                               max_drawdown: float,
                               volatility: float,
                               correlation_with_portfolio: float,
                               regime_context: Optional[str] = None):
        """Update strategy with realized performance."""
        self.selector.update_strategy_performance(
            strategy_name=strategy_name,
            returns=realized_returns,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            volatility=volatility,
            correlation_with_portfolio=correlation_with_portfolio,
            regime_context=regime_context
        )
        
        # Update strategy status
        self.selector.update_strategy_status(strategy_name)
        
        # Apply promotion/demotion rules periodically
        if len(self.selection_history) % 10 == 0:  # Every 10 updates
            self.selector.apply_promotion_demotion_rules()
    
    def get_selection_analysis(self) -> Dict[str, Any]:
        """Get analysis of strategy selection performance."""
        if not self.selection_history:
            return {}
        
        # Get recent selections
        recent_selections = self.selection_history[-20:]  # Last 20 selections
        
        # Count strategy selections
        strategy_counts = {}
        for record in recent_selections:
            strategy = record['selected_strategy']
            if strategy:
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            'total_selections': len(self.selection_history),
            'recent_selections_count': len(recent_selections),
            'strategy_selection_frequency': strategy_counts,
            'current_rankings': self.selector.get_strategy_rankings()[:10],  # Top 10
            'performance_summary': self.selector.get_performance_summary()
        }


# Global instance
strategy_selector = AdvancedStrategySelector()
strategy_selection_service = StrategySelectionService()