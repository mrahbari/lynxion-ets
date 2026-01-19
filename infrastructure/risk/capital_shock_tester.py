"""
Capital Shock Testing Module - Test portfolio resilience under sudden capital reductions
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
import json
import os

from infrastructure.portfolio.comprehensive_portfolio_backtester import ComprehensivePortfolioBacktester, load_sample_strategies
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
from shared.logger import EnhancedLogger


class CapitalShockTester:
    """
    System for testing portfolio resilience under sudden capital reductions.
    Simulates scenarios like -20% or -30% capital shocks to ensure 
    position sizing adapts correctly.
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.logger = EnhancedLogger("CapitalShockTester")
    
    def simulate_capital_shock(self, 
                              shock_percentage: float, 
                              baseline_results: Dict[str, Any],
                              data_dict: Dict[str, pd.DataFrame],
                              strategy_functions: Dict[str, callable]) -> Dict[str, Any]:
        """
        Simulate a capital shock and measure portfolio adaptation.
        
        Args:
            shock_percentage: Percentage of capital reduction (e.g., -0.2 for -20%)
            baseline_results: Baseline portfolio results before shock
            data_dict: Market data dictionary
            strategy_functions: Strategy functions to test
            
        Returns:
            Dictionary with shock test results
        """
        shocked_capital = self.initial_capital * (1 + shock_percentage)
        
        self.logger.info(f"Simulating capital shock: {shock_percentage:.1%} -> ${shocked_capital:,.2f}")
        
        # Create new backtester with shocked capital
        shocked_backtester = ComprehensivePortfolioBacktester(
            initial_capital=shocked_capital,
            fee_rate=baseline_results.get('fee_rate', 0.001),
            slippage_factor=baseline_results.get('slippage_factor', 0.0005)
        )
        
        # Run backtest with shocked capital
        shocked_results = shocked_backtester.run_comprehensive_backtest(
            symbols=baseline_results.get('symbols', []),
            strategy_functions=strategy_functions,
            start_date=datetime.fromisoformat(baseline_results['date_range']['start']),
            end_date=datetime.fromisoformat(baseline_results['date_range']['end'])
        )
        
        # Calculate metrics comparison
        comparison_metrics = self.compare_results(baseline_results, shocked_results, shock_percentage)
        
        return {
            'shock_percentage': shock_percentage,
            'original_capital': self.initial_capital,
            'shocked_capital': shocked_capital,
            'baseline_results': baseline_results,
            'shocked_results': shocked_results,
            'comparison_metrics': comparison_metrics,
            'timestamp': datetime.now().isoformat()
        }
    
    def compare_results(self, baseline: Dict[str, Any], shocked: Dict[str, Any], shock_pct: float) -> Dict[str, Any]:
        """Compare baseline and shocked results to measure resilience."""
        
        comparison = {
            'capital_efficiency': {},
            'risk_metrics': {},
            'performance_metrics': {},
            'allocation_changes': {}
        }
        
        # Compare admission metrics
        baseline_admission = baseline.get('admission_metrics', {})
        shocked_admission = shocked.get('admission_metrics', {})
        
        for strategy_name in baseline_admission.keys():
            if strategy_name in shocked_admission:
                baseline_metrics = baseline_admission[strategy_name]
                shocked_metrics = shocked_admission[strategy_name]
                
                comparison['performance_metrics'][strategy_name] = {
                    'return_change': shocked_metrics.get('avg_return', 0) - baseline_metrics.get('avg_return', 0),
                    'sharpe_change': shocked_metrics.get('avg_sharpe', 0) - baseline_metrics.get('avg_sharpe', 0),
                    'drawdown_change': shocked_metrics.get('avg_drawdown', 0) - baseline_metrics.get('avg_drawdown', 0)
                }
        
        # Compare capital allocation changes
        baseline_weights = baseline.get('capital_weights', {})
        shocked_weights = shocked.get('capital_weights', {})
        
        for strategy_name in baseline_weights.keys():
            if strategy_name in shocked_weights:
                baseline_weight = baseline_weights[strategy_name]
                shocked_weight = shocked_weights[strategy_name]
                
                comparison['allocation_changes'][strategy_name] = {
                    'baseline_weight': baseline_weight,
                    'shocked_weight': shocked_weight,
                    'weight_change': shocked_weight - baseline_weight,
                    'weight_change_pct': (shocked_weight - baseline_weight) / baseline_weight if baseline_weight != 0 else 0
                }
        
        # Calculate resilience score
        resilience_metrics = []
        
        # Allocation stability (should remain relatively stable despite capital shock)
        weight_changes = [abs(change['weight_change']) for change in comparison['allocation_changes'].values()]
        avg_weight_change = np.mean(weight_changes) if weight_changes else 0
        allocation_stability_score = max(0, 1 - avg_weight_change)  # Higher is better
        
        # Performance consistency (returns should scale proportionally)
        return_changes = [abs(metrics['return_change']) for metrics in comparison['performance_metrics'].values()]
        avg_return_change = np.mean(return_changes) if return_changes else 0
        performance_consistency_score = max(0, 1 - avg_return_change)  # Higher is better
        
        comparison['resilience_score'] = {
            'allocation_stability': float(allocation_stability_score),
            'performance_consistency': float(performance_consistency_score),
            'overall_resilience': float((allocation_stability_score + performance_consistency_score) / 2)
        }
        
        return comparison
    
    def run_comprehensive_shock_test(self,
                                   symbols: List[str],
                                   shock_scenarios: List[float] = [-0.2, -0.3, -0.5],
                                   start_date: datetime = None,
                                   end_date: datetime = None) -> Dict[str, Any]:
        """
        Run comprehensive capital shock testing across multiple scenarios.
        
        Args:
            symbols: List of symbols to test
            shock_scenarios: List of shock percentages to test
            start_date: Start date for testing
            end_date: End date for testing
            
        Returns:
            Dictionary with comprehensive shock test results
        """
        self.logger.info(f"Starting comprehensive capital shock testing for {symbols}")
        
        # Load data
        data_loader = CSVHistoryLoaderAdapter()
        data_dict = {}
        
        for symbol in symbols:
            try:
                df = data_loader.load(symbol=symbol)
                if not df.empty:
                    data_dict[symbol] = df
            except Exception as e:
                self.logger.error(f"Error loading data for {symbol}: {e}")
        
        if not data_dict:
            return {"error": "No data available for shock testing"}
        
        # Load strategy functions
        strategy_functions = load_sample_strategies()
        
        # Run baseline test
        baseline_backtester = ComprehensivePortfolioBacktester(initial_capital=self.initial_capital)
        
        baseline_results = baseline_backtester.run_comprehensive_backtest(
            symbols=symbols,
            strategy_functions=strategy_functions,
            start_date=start_date,
            end_date=end_date
        )
        
        if 'error' in baseline_results:
            return {"error": f"Baseline test failed: {baseline_results['error']}"}
        
        # Run shock tests for each scenario
        shock_results = {}
        for shock_pct in shock_scenarios:
            shock_result = self.simulate_capital_shock(
                shock_percentage=shock_pct,
                baseline_results=baseline_results,
                data_dict=data_dict,
                strategy_functions=strategy_functions
            )
            shock_results[f"shock_{shock_pct:.0%}"] = shock_result
        
        # Compile comprehensive results
        comprehensive_results = {
            'baseline_results': baseline_results,
            'shock_scenarios': shock_scenarios,
            'shock_results': shock_results,
            'symbols': symbols,
            'initial_capital': self.initial_capital,
            'timestamp': datetime.now().isoformat(),
            'summary': self._compile_shock_summary(shock_results)
        }
        
        self.logger.info("Comprehensive capital shock testing completed")
        
        return comprehensive_results
    
    def _compile_shock_summary(self, shock_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile summary statistics from shock test results."""
        
        summary = {
            'average_resilience_scores': {},
            'critical_thresholds': [],
            'recommendations': []
        }
        
        resilience_scores = []
        for scenario_name, result in shock_results.items():
            if 'comparison_metrics' in result:
                resilience = result['comparison_metrics'].get('resilience_score', {})
                overall_resilience = resilience.get('overall_resilience', 0)
                resilience_scores.append(overall_resilience)
        
        if resilience_scores:
            summary['average_resilience_scores'] = {
                'mean': float(np.mean(resilience_scores)),
                'std': float(np.std(resilience_scores)),
                'min': float(np.min(resilience_scores)),
                'max': float(np.max(resilience_scores))
            }
        
        # Identify critical thresholds (scenarios where resilience drops below acceptable levels)
        for scenario_name, result in shock_results.items():
            resilience = result['comparison_metrics'].get('resilience_score', {}).get('overall_resilience', 0)
            if resilience < 0.5:  # Below 50% resilience
                shock_pct = result['shock_percentage']
                summary['critical_thresholds'].append({
                    'scenario': scenario_name,
                    'shock_percentage': shock_pct,
                    'resilience_score': resilience
                })
        
        # Generate recommendations
        avg_resilience = summary['average_resilience_scores'].get('mean', 0) if summary['average_resilience_scores'] else 0
        
        if avg_resilience > 0.8:
            summary['recommendations'].append("Portfolio shows excellent resilience to capital shocks")
        elif avg_resilience > 0.6:
            summary['recommendations'].append("Portfolio shows moderate resilience to capital shocks")
        else:
            summary['recommendations'].append("Portfolio shows poor resilience to capital shocks - consider diversification improvements")
        
        return summary


def run_capital_shock_test(symbols: List[str], 
                          initial_capital: float = 100000.0,
                          shock_scenarios: List[float] = [-0.2, -0.3, -0.5]) -> Dict[str, Any]:
    """Convenience function to run capital shock testing."""
    tester = CapitalShockTester(initial_capital=initial_capital)
    return tester.run_comprehensive_shock_test(symbols=symbols, shock_scenarios=shock_scenarios)