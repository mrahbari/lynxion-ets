"""
Strategy Kill-Switch Engine - Dynamic strategy monitoring and disabling system
based on performance metrics and risk thresholds.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import time

from shared.logger import EnhancedLogger


class StrategyStatus(Enum):
    """Enumeration for strategy status."""
    ACTIVE = "active"
    DISABLED = "disabled"
    MONITORING = "monitoring"
    RECOVERING = "recovering"


@dataclass
class StrategyMetrics:
    """Data class to hold strategy performance metrics."""
    rolling_sharpe: float
    rolling_dd: float
    expectancy: float
    trade_count: int
    win_rate: float
    profit_factor: float
    avg_return: float
    timestamp: datetime


class StrategyKillSwitchEngine:
    """
    Dynamic strategy monitoring and disabling system that enforces risk thresholds
    and manages strategy lifecycle based on performance metrics.
    """
    
    def __init__(self, 
                 rolling_window_days: int = 30,
                 sharpe_threshold: float = -0.2,
                 drawdown_limit: float = 0.10,
                 expectancy_threshold: float = 0.0,
                 min_trade_count: int = 10,
                 recovery_threshold: float = 0.1,
                 check_interval_minutes: int = 60):
        
        self.rolling_window_days = rolling_window_days
        self.sharpe_threshold = sharpe_threshold
        self.drawdown_limit = drawdown_limit
        self.expectancy_threshold = expectancy_threshold
        self.min_trade_count = min_trade_count
        self.recovery_threshold = recovery_threshold
        self.check_interval_minutes = check_interval_minutes
        
        self.logger = EnhancedLogger("StrategyKillSwitchEngine")
        
        # Strategy state tracking
        self.strategy_states: Dict[str, StrategyStatus] = {}
        self.strategy_metrics: Dict[str, List[StrategyMetrics]] = {}
        self.strategy_performance_log: Dict[str, List[Dict[str, Any]]] = {}
        
        # Threading for continuous monitoring
        self.monitoring_thread = None
        self.monitoring_active = False
        
    def initialize_strategies(self, strategy_names: List[str]):
        """Initialize tracking for given strategy names."""
        for strategy_name in strategy_names:
            if strategy_name not in self.strategy_states:
                self.strategy_states[strategy_name] = StrategyStatus.ACTIVE
                self.strategy_metrics[strategy_name] = []
                self.strategy_performance_log[strategy_name] = []
                self.logger.info(f"Initialized tracking for strategy: {strategy_name}")
    
    def update_strategy_metrics(self, 
                              strategy_name: str, 
                              metrics: Dict[str, Any],
                              timestamp: datetime = None):
        """Update metrics for a strategy."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create StrategyMetrics object
        strategy_metrics = StrategyMetrics(
            rolling_sharpe=metrics.get('rolling_sharpe', 0),
            rolling_dd=metrics.get('rolling_dd', 0),
            expectancy=metrics.get('expectancy', 0),
            trade_count=metrics.get('trade_count', 0),
            win_rate=metrics.get('win_rate', 0),
            profit_factor=metrics.get('profit_factor', 1.0),
            avg_return=metrics.get('avg_return', 0),
            timestamp=timestamp
        )
        
        # Add to metrics history
        if strategy_name not in self.strategy_metrics:
            self.strategy_metrics[strategy_name] = []
        self.strategy_metrics[strategy_name].append(strategy_metrics)
        
        # Keep only recent metrics (within rolling window)
        cutoff_time = timestamp - timedelta(days=self.rolling_window_days)
        self.strategy_metrics[strategy_name] = [
            m for m in self.strategy_metrics[strategy_name] 
            if m.timestamp >= cutoff_time
        ]
        
        # Log performance
        self._log_performance(strategy_name, strategy_metrics)
    
    def _log_performance(self, strategy_name: str, metrics: StrategyMetrics):
        """Log strategy performance for tracking."""
        log_entry = {
            'timestamp': metrics.timestamp,
            'rolling_sharpe': metrics.rolling_sharpe,
            'rolling_dd': metrics.rolling_dd,
            'expectancy': metrics.expectancy,
            'trade_count': metrics.trade_count,
            'win_rate': metrics.win_rate,
            'profit_factor': metrics.profit_factor,
            'avg_return': metrics.avg_return,
            'status': self.strategy_states.get(strategy_name, StrategyStatus.ACTIVE).value
        }
        
        if strategy_name not in self.strategy_performance_log:
            self.strategy_performance_log[strategy_name] = []
        self.strategy_performance_log[strategy_name].append(log_entry)
    
    def evaluate_strategy_status(self, strategy_name: str) -> StrategyStatus:
        """Evaluate and update the status of a strategy based on current metrics."""
        if strategy_name not in self.strategy_metrics:
            return StrategyStatus.ACTIVE
        
        # Get recent metrics
        recent_metrics = self.strategy_metrics[strategy_name]
        if not recent_metrics:
            return StrategyStatus.ACTIVE
        
        # Get the most recent metrics
        latest_metrics = recent_metrics[-1]
        
        current_status = self.strategy_states.get(strategy_name, StrategyStatus.ACTIVE)
        
        # Decision logic based on current status
        if current_status == StrategyStatus.ACTIVE:
            # Check if strategy should be disabled
            should_disable = self._should_disable_strategy(latest_metrics)
            
            if should_disable:
                new_status = StrategyStatus.DISABLED
                self.logger.warning(f"Disabling strategy {strategy_name} due to poor performance: "
                                  f"Sharpe: {latest_metrics.rolling_sharpe:.3f}, "
                                  f"DD: {latest_metrics.rolling_dd:.3f}, "
                                  f"Expectancy: {latest_metrics.expectancy:.3f}")
            else:
                new_status = StrategyStatus.ACTIVE
        
        elif current_status == StrategyStatus.DISABLED:
            # Check if strategy should be re-enabled
            should_enable = self._should_enable_strategy(latest_metrics)
            
            if should_enable:
                new_status = StrategyStatus.RECOVERING
                self.logger.info(f"Re-enabling strategy {strategy_name} - showing signs of recovery")
            else:
                new_status = StrategyStatus.DISABLED
        
        elif current_status == StrategyStatus.RECOVERING:
            # Monitor recovery period
            if self._is_recovery_successful(latest_metrics):
                new_status = StrategyStatus.ACTIVE
                self.logger.info(f"Strategy {strategy_name} successfully recovered")
            elif self._should_disable_strategy(latest_metrics):
                new_status = StrategyStatus.DISABLED
                self.logger.warning(f"Strategy {strategy_name} failed recovery, disabling again")
            else:
                new_status = StrategyStatus.RECOVERING
        
        else:  # MONITORING
            new_status = current_status
        
        # Update status if changed
        if new_status != current_status:
            self.strategy_states[strategy_name] = new_status
            self._log_status_change(strategy_name, current_status, new_status)
        
        return new_status
    
    def _should_disable_strategy(self, metrics: StrategyMetrics) -> bool:
        """Determine if a strategy should be disabled."""
        # Check rolling Sharpe ratio
        if metrics.rolling_sharpe < self.sharpe_threshold:
            return True
        
        # Check drawdown
        if abs(metrics.rolling_dd) > self.drawdown_limit:
            return True
        
        # Check expectancy
        if metrics.expectancy < self.expectancy_threshold:
            return True
        
        # Check minimum trade count for reliable metrics
        if metrics.trade_count < self.min_trade_count:
            # If insufficient trades but negative metrics, disable
            if (metrics.rolling_sharpe < self.sharpe_threshold or 
                abs(metrics.rolling_dd) > self.drawdown_limit or 
                metrics.expectancy < self.expectancy_threshold):
                return True
        
        return False
    
    def _should_enable_strategy(self, metrics: StrategyMetrics) -> bool:
        """Determine if a disabled strategy should be re-enabled."""
        # Check if strategy is showing improvement
        if (metrics.rolling_sharpe >= self.sharpe_threshold and 
            abs(metrics.rolling_dd) <= self.drawdown_limit and 
            metrics.expectancy >= self.expectancy_threshold and
            metrics.trade_count >= self.min_trade_count):
            return True
        
        # Check for positive momentum in metrics
        if len(self.strategy_metrics.get(metrics, [])) >= 3:
            recent_metrics = self.strategy_metrics[metrics][-3:]
            improving_sharpe = all(m.rolling_sharpe > prev.rolling_sharpe 
                                 for m, prev in zip(recent_metrics[1:], recent_metrics[:-1]))
            
            if improving_sharpe and recent_metrics[-1].rolling_sharpe > -0.1:
                return True
        
        return False
    
    def _is_recovery_successful(self, metrics: StrategyMetrics) -> bool:
        """Determine if a recovering strategy has successfully recovered."""
        return (metrics.rolling_sharpe >= self.recovery_threshold and 
                metrics.expectancy >= 0.05 and  # Positive expectancy
                metrics.win_rate >= 0.4 and     # At least 40% win rate
                metrics.profit_factor >= 1.2)   # Profit factor > 1.2
    
    def _log_status_change(self, strategy_name: str, old_status: StrategyStatus, new_status: StrategyStatus):
        """Log strategy status changes."""
        self.logger.info(f"Strategy {strategy_name} status changed: {old_status.value} -> {new_status.value}")
    
    def get_strategy_status(self, strategy_name: str) -> StrategyStatus:
        """Get the current status of a strategy."""
        return self.strategy_states.get(strategy_name, StrategyStatus.MONITORING)
    
    def get_active_strategies(self) -> List[str]:
        """Get list of currently active strategies."""
        return [name for name, status in self.strategy_states.items() 
                if status in [StrategyStatus.ACTIVE, StrategyStatus.RECOVERING]]
    
    def get_disabled_strategies(self) -> List[str]:
        """Get list of currently disabled strategies."""
        return [name for name, status in self.strategy_states.items() 
                if status == StrategyStatus.DISABLED]
    
    def get_strategy_health_report(self) -> Dict[str, Dict[str, Any]]:
        """Generate a health report for all strategies."""
        report = {}

        for strategy_name in self.strategy_states.keys():
            if strategy_name in self.strategy_metrics and self.strategy_metrics[strategy_name]:
                latest_metrics = self.strategy_metrics[strategy_name][-1]

                report[strategy_name] = {
                    'status': self.strategy_states[strategy_name].value,
                    'rolling_sharpe': latest_metrics.rolling_sharpe,
                    'rolling_dd': latest_metrics.rolling_dd,
                    'expectancy': latest_metrics.expectancy,
                    'trade_count': latest_metrics.trade_count,
                    'win_rate': latest_metrics.win_rate,
                    'profit_factor': latest_metrics.profit_factor,
                    'avg_return': latest_metrics.avg_return,
                    'last_updated': latest_metrics.timestamp.isoformat()
                }
            else:
                report[strategy_name] = {
                    'status': self.strategy_states[strategy_name].value,
                    'error': 'No metrics available'
                }

        return report

    def get_kill_switch_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations from the kill switch engine."""
        health_report = self.get_strategy_health_report()
        recommendations = []

        for strategy_name, metrics in health_report.items():
            if metrics['status'] == 'disabled':
                recommendations.append({
                    'strategy': strategy_name,
                    'action': 'monitor',
                    'reason': f'Strategy disabled due to poor performance metrics'
                })
            elif metrics['status'] == 'active':
                # Check if metrics are approaching thresholds
                sharpe = metrics.get('rolling_sharpe', 0)
                dd = abs(metrics.get('rolling_dd', 0))
                expectancy = metrics.get('expectancy', 0)

                if sharpe < self.sharpe_threshold + 0.05:  # Within 0.05 of threshold
                    recommendations.append({
                        'strategy': strategy_name,
                        'action': 'caution',
                        'reason': f'Sharpe ratio approaching threshold ({sharpe:.3f})'
                    })
                elif dd > self.drawdown_limit - 0.02:  # Within 0.02 of threshold
                    recommendations.append({
                        'strategy': strategy_name,
                        'action': 'caution',
                        'reason': f'Drawdown approaching limit ({dd:.3f})'
                    })
                elif expectancy < self.expectancy_threshold + 0.01:  # Within 0.01 of threshold
                    recommendations.append({
                        'strategy': strategy_name,
                        'action': 'caution',
                        'reason': f'Expectancy approaching threshold ({expectancy:.3f})'
                    })

        return recommendations
    
    def start_monitoring(self, strategy_names: List[str] = None):
        """Start continuous monitoring of strategies."""
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        if strategy_names:
            self.initialize_strategies(strategy_names)
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("Strategy kill-switch monitoring started")
    
    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)  # Wait up to 2 seconds for thread to finish
        
        self.logger.info("Strategy kill-switch monitoring stopped")
    
    def _monitor_loop(self):
        """Internal monitoring loop."""
        while self.monitoring_active:
            try:
                # Evaluate all strategies
                for strategy_name in list(self.strategy_states.keys()):
                    self.evaluate_strategy_status(strategy_name)
                
                # Sleep for the specified interval
                time.sleep(self.check_interval_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def force_strategy_status(self, strategy_name: str, status: StrategyStatus):
        """Force a strategy to a specific status (for manual intervention)."""
        old_status = self.strategy_states.get(strategy_name, StrategyStatus.MONITORING)
        self.strategy_states[strategy_name] = status
        self._log_status_change(strategy_name, old_status, status)
        
        self.logger.info(f"Manually set strategy {strategy_name} to {status.value}")


class PortfolioRiskController:
    """
    Portfolio-level risk controller that coordinates strategy kill switches
    and manages overall portfolio risk exposure.
    """
    
    def __init__(self, 
                 max_portfolio_drawdown: float = 0.15,
                 max_strategy_correlation: float = 0.7,
                 max_strategy_allocation: float = 0.30):
        
        self.max_portfolio_drawdown = max_portfolio_drawdown
        self.max_strategy_correlation = max_strategy_correlation
        self.max_strategy_allocation = max_strategy_allocation
        
        self.logger = EnhancedLogger("PortfolioRiskController")
        self.kill_switch_engine = StrategyKillSwitchEngine()
        
        # Portfolio metrics
        self.portfolio_metrics = {
            'total_equity': 0.0,
            'portfolio_drawdown': 0.0,
            'total_allocated_capital': 0.0,
            'active_strategies_count': 0
        }
    
    def update_portfolio_metrics(self, 
                               strategy_results: Dict[str, Dict[str, Any]],
                               capital_allocations: Dict[str, float]):
        """Update portfolio-level metrics."""
        # Calculate portfolio metrics based on strategy results and allocations
        total_equity = 0.0
        total_allocated = 0.0
        active_strategies = 0
        
        for strategy_name, allocation in capital_allocations.items():
            if strategy_name in strategy_results:
                strategy_result = strategy_results[strategy_name]
                # Calculate strategy contribution to portfolio
                strategy_return = strategy_result.get('total_return', 0)
                strategy_equity = allocation * (1 + strategy_return)
                total_equity += strategy_equity
                total_allocated += allocation
                active_strategies += 1
        
        self.portfolio_metrics.update({
            'total_equity': total_equity,
            'total_allocated_capital': total_allocated,
            'active_strategies_count': active_strategies
        })
    
    def assess_portfolio_risk(self) -> Dict[str, Any]:
        """Assess overall portfolio risk and return recommendations."""
        risk_assessment = {
            'portfolio_drawdown_risk': self.portfolio_metrics['portfolio_drawdown'] > self.max_portfolio_drawdown,
            'strategy_diversification_risk': self._assess_diversification_risk(),
            'capital_allocation_risk': self._assess_allocation_risk(),
            'recommendations': []
        }
        
        # Add recommendations based on risk assessment
        if risk_assessment['portfolio_drawdown_risk']:
            risk_assessment['recommendations'].append(
                "Portfolio drawdown exceeds threshold, consider reducing exposure"
            )
        
        if risk_assessment['strategy_diversification_risk']:
            risk_assessment['recommendations'].append(
                "High correlation between strategies detected, consider diversification"
            )
        
        if risk_assessment['capital_allocation_risk']:
            risk_assessment['recommendations'].append(
                "Over-allocation to single strategies detected, rebalance allocations"
            )
        
        return risk_assessment
    
    def _assess_diversification_risk(self) -> bool:
        """Assess if strategies are too correlated."""
        # This would typically involve calculating correlation between strategy returns
        # For now, we'll return False as a placeholder
        return False
    
    def _assess_allocation_risk(self) -> bool:
        """Assess if capital allocation is too concentrated."""
        # This would check if any single strategy has allocation > max_strategy_allocation
        # For now, we'll return False as a placeholder
        return False
    
    def get_kill_switch_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations from the kill switch engine."""
        health_report = self.kill_switch_engine.get_strategy_health_report()
        recommendations = []
        
        for strategy_name, metrics in health_report.items():
            if metrics['status'] == 'disabled':
                recommendations.append({
                    'strategy': strategy_name,
                    'action': 'monitor',
                    'reason': f'Strategy disabled due to poor performance metrics'
                })
            elif metrics['status'] == 'active':
                # Check if metrics are approaching thresholds
                sharpe = metrics.get('rolling_sharpe', 0)
                dd = abs(metrics.get('rolling_dd', 0))
                expectancy = metrics.get('expectancy', 0)
                
                if sharpe < self.kill_switch_engine.sharpe_threshold + 0.05:  # Within 0.05 of threshold
                    recommendations.append({
                        'strategy': strategy_name,
                        'action': 'caution',
                        'reason': f'Sharpe ratio approaching threshold ({sharpe:.3f})'
                    })
                elif dd > self.kill_switch_engine.drawdown_limit - 0.02:  # Within 0.02 of threshold
                    recommendations.append({
                        'strategy': strategy_name,
                        'action': 'caution',
                        'reason': f'Drawdown approaching limit ({dd:.3f})'
                    })
                elif expectancy < self.kill_switch_engine.expectancy_threshold + 0.01:  # Within 0.01 of threshold
                    recommendations.append({
                        'strategy': strategy_name,
                        'action': 'caution',
                        'reason': f'Expectancy approaching threshold ({expectancy:.3f})'
                    })
        
        return recommendations


def create_kill_switch_from_backtest_results(backtest_results: Dict[str, Any]) -> StrategyKillSwitchEngine:
    """
    Create and initialize a kill switch engine from backtest results.
    """
    logger = EnhancedLogger("KillSwitchInitializer")
    
    # Extract strategy names from backtest results
    strategy_names = []
    
    if 'multi_strategy_results' in backtest_results:
        strategy_names = list(backtest_results['multi_strategy_results'].keys())
    elif 'strategy_rankings' in backtest_results:
        strategy_names = [item['strategy'] for item in backtest_results['strategy_rankings']]
    elif 'individual_results' in backtest_results:
        strategy_names = list(backtest_results['individual_results'].keys())
    else:
        logger.warning("Could not extract strategy names from backtest results")
        return None
    
    # Initialize kill switch engine
    kill_switch = StrategyKillSwitchEngine()
    kill_switch.initialize_strategies(strategy_names)
    
    # Update metrics for each strategy if available in results
    if 'individual_results' in backtest_results:
        for strategy_name, strategy_results in backtest_results['individual_results'].items():
            # Aggregate metrics across all symbols for this strategy
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
                
                # Update strategy metrics
                metrics = {
                    'rolling_sharpe': sharpe,
                    'rolling_dd': max_dd,
                    'expectancy': expectancy,
                    'trade_count': len(all_pnl),
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'avg_return': avg_return
                }
                
                kill_switch.update_strategy_metrics(strategy_name, metrics)
    
    logger.info(f"Initialized kill switch engine with {len(strategy_names)} strategies")
    
    return kill_switch