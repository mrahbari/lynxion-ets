"""
Monte Carlo Risk Simulation Module - Advanced risk analysis for trading strategies
using bootstrap resampling and trade order randomization.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from scipy import stats
from scipy.stats import skew, kurtosis
import warnings
warnings.filterwarnings('ignore')

from shared.logger import EnhancedLogger


class MonteCarloRiskSimulator:
    """
    Advanced Monte Carlo risk simulator for evaluating trading strategy robustness
    through trade order randomization and bootstrap resampling.
    """
    
    def __init__(self, num_simulations: int = 1000, confidence_level: float = 0.95):
        self.num_simulations = num_simulations
        self.confidence_level = confidence_level
        self.logger = EnhancedLogger("MonteCarloRiskSimulator")
        
    def run_monte_carlo_simulation(self, 
                                 trade_history: List[Dict[str, Any]], 
                                 initial_capital: float = 10000.0) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation using trade order randomization.
        
        Args:
            trade_history: List of trades with 'pnl', 'timestamp', 'size', 'price' fields
            initial_capital: Starting capital for simulation
            
        Returns:
            Dictionary with Monte Carlo results
        """
        if not trade_history:
            return {"error": "No trade history provided"}
        
        # Extract PnL values
        pnl_values = [trade.get('pnl', 0) for trade in trade_history if 'pnl' in trade]
        
        if not pnl_values:
            return {"error": "No PnL values found in trade history"}
        
        # Run Monte Carlo simulations
        simulation_results = []
        
        for i in range(self.num_simulations):
            # Randomly shuffle trade order
            shuffled_pnl = np.random.choice(pnl_values, size=len(pnl_values), replace=False)
            
            # Calculate equity curve for this simulation
            equity_curve = [initial_capital]
            current_equity = initial_capital
            
            for pnl in shuffled_pnl:
                current_equity += pnl
                equity_curve.append(current_equity)
            
            # Calculate metrics for this simulation
            simulation_metrics = self._calculate_equity_metrics(equity_curve, initial_capital)
            simulation_results.append(simulation_metrics)
        
        # Aggregate simulation results
        aggregated_results = self._aggregate_simulation_results(simulation_results)
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(simulation_results)
        
        # Calculate confidence intervals
        confidence_intervals = self._calculate_confidence_intervals(simulation_results)
        
        results = {
            'num_simulations': self.num_simulations,
            'original_trade_count': len(trade_history),
            'simulation_results': simulation_results,
            'aggregated_metrics': aggregated_results,
            'risk_metrics': risk_metrics,
            'confidence_intervals': confidence_intervals,
            'worst_case_scenario': self._get_worst_case_scenario(simulation_results),
            'best_case_scenario': self._get_best_case_scenario(simulation_results)
        }
        
        self.logger.info(f"Monte Carlo simulation completed with {self.num_simulations} iterations")
        
        return results
    
    def run_bootstrap_simulation(self, 
                               trade_history: List[Dict[str, Any]], 
                               initial_capital: float = 10000.0) -> Dict[str, Any]:
        """
        Run bootstrap simulation using sampling with replacement.
        
        Args:
            trade_history: List of trades with 'pnl', 'timestamp', 'size', 'price' fields
            initial_capital: Starting capital for simulation
            
        Returns:
            Dictionary with bootstrap results
        """
        if not trade_history:
            return {"error": "No trade history provided"}
        
        # Extract PnL values
        pnl_values = [trade.get('pnl', 0) for trade in trade_history if 'pnl' in trade]
        
        if not pnl_values:
            return {"error": "No PnL values found in trade history"}
        
        # Run bootstrap simulations
        simulation_results = []
        
        for i in range(self.num_simulations):
            # Sample with replacement
            sampled_pnl = np.random.choice(pnl_values, size=len(pnl_values), replace=True)
            
            # Calculate equity curve for this simulation
            equity_curve = [initial_capital]
            current_equity = initial_capital
            
            for pnl in sampled_pnl:
                current_equity += pnl
                equity_curve.append(current_equity)
            
            # Calculate metrics for this simulation
            simulation_metrics = self._calculate_equity_metrics(equity_curve, initial_capital)
            simulation_results.append(simulation_metrics)
        
        # Aggregate simulation results
        aggregated_results = self._aggregate_simulation_results(simulation_results)
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(simulation_results)
        
        # Calculate confidence intervals
        confidence_intervals = self._calculate_confidence_intervals(simulation_results)
        
        results = {
            'num_simulations': self.num_simulations,
            'original_trade_count': len(trade_history),
            'simulation_results': simulation_results,
            'aggregated_metrics': aggregated_results,
            'risk_metrics': risk_metrics,
            'confidence_intervals': confidence_intervals,
            'worst_case_scenario': self._get_worst_case_scenario(simulation_results),
            'best_case_scenario': self._get_best_case_scenario(simulation_results)
        }
        
        self.logger.info(f"Bootstrap simulation completed with {self.num_simulations} iterations")
        
        return results
    
    def _calculate_equity_metrics(self, equity_curve: List[float], initial_capital: float) -> Dict[str, float]:
        """Calculate equity curve metrics for a single simulation."""
        equity_array = np.array(equity_curve)
        
        # Calculate returns
        returns = np.diff(equity_array) / equity_array[:-1]
        
        # Total return
        total_return = (equity_array[-1] - initial_capital) / initial_capital
        
        # Calculate Sharpe ratio (assuming daily returns)
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0.0
        
        # Calculate maximum drawdown
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - running_max) / running_max
        max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0
        
        # Win rate
        positive_returns = np.sum(returns > 0)
        total_returns = len(returns)
        win_rate = positive_returns / total_returns if total_returns > 0 else 0.0
        
        # Profit factor
        gains = returns[returns > 0]
        losses = returns[returns < 0]
        total_gain = np.sum(gains) if len(gains) > 0 else 0
        total_loss = abs(np.sum(losses)) if len(losses) > 0 else 0
        profit_factor = total_gain / total_loss if total_loss > 0 else float('inf')
        
        # Calculate other metrics
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0  # Annualized
        sortino_ratio = self._calculate_sortino_ratio(returns)
        calmar_ratio = total_return / abs(max_drawdown) if abs(max_drawdown) > 0 else 0.0
        
        return {
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'profit_factor': float(profit_factor),
            'volatility': float(volatility),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio),
            'final_equity': float(equity_array[-1]),
            'max_equity': float(np.max(equity_array)),
            'min_equity': float(np.min(equity_array)),
            'total_trades': len(returns)
        }
    
    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sortino ratio using downside deviation."""
        if len(returns) <= 1:
            return 0.0
        
        # Calculate downside deviation
        negative_returns = returns[returns < 0]
        if len(negative_returns) == 0:
            downside_dev = 0.0
        else:
            downside_dev = np.sqrt(np.mean(negative_returns ** 2))
        
        # Calculate Sortino ratio
        avg_return = np.mean(returns)
        if downside_dev > 0:
            sortino_ratio = avg_return / downside_dev * np.sqrt(252)  # Annualized
        else:
            sortino_ratio = np.sign(avg_return) * float('inf') if avg_return != 0 else 0.0
        
        return float(sortino_ratio)
    
    def _aggregate_simulation_results(self, simulation_results: List[Dict[str, float]]) -> Dict[str, float]:
        """Aggregate results across all simulations."""
        if not simulation_results:
            return {}
        
        # Extract metric names
        metric_names = list(simulation_results[0].keys())
        
        # Calculate aggregate metrics
        aggregates = {}
        for metric in metric_names:
            values = [result[metric] for result in simulation_results if metric in result]
            if values:
                aggregates[f'avg_{metric}'] = float(np.mean(values))
                aggregates[f'max_{metric}'] = float(np.max(values))
                aggregates[f'min_{metric}'] = float(np.min(values))
                aggregates[f'std_{metric}'] = float(np.std(values))
        
        return aggregates
    
    def _calculate_risk_metrics(self, simulation_results: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate risk metrics from simulation results."""
        if not simulation_results:
            return {}
        
        # Extract final equity values
        final_equities = [result['final_equity'] for result in simulation_results]
        total_returns = [result['total_return'] for result in simulation_results]
        max_drawdowns = [result['max_drawdown'] for result in simulation_results]
        
        # Probability of ruin (final equity < some threshold, e.g., 70% of initial)
        initial_capital = simulation_results[0].get('final_equity', 10000) / (1 + simulation_results[0].get('total_return', 0))
        ruin_threshold = initial_capital * 0.7  # 70% of initial capital
        prob_ruin = sum(1 for eq in final_equities if eq < ruin_threshold) / len(final_equities)
        
        # Maximum equity stagnation (time spent below certain threshold)
        # For simplicity, we'll calculate percentage of simulations with negative returns
        neg_return_count = sum(1 for ret in total_returns if ret < 0)
        prob_negative = neg_return_count / len(total_returns)
        
        # Worst case drawdown
        worst_dd = min(max_drawdowns) if max_drawdowns else 0.0
        
        # Value at Risk (VaR) at confidence level
        var_percentile = (1 - self.confidence_level) * 100
        var_return = np.percentile(total_returns, var_percentile) if total_returns else 0.0
        
        # Expected shortfall (Conditional VaR)
        if total_returns:
            var_threshold = np.percentile(total_returns, var_percentile)
            es_returns = [ret for ret in total_returns if ret <= var_threshold]
            expected_shortfall = np.mean(es_returns) if es_returns else var_return
        else:
            expected_shortfall = 0.0
        
        return {
            'probability_of_ruin': float(prob_ruin),
            'probability_of_negative_return': float(prob_negative),
            'worst_case_drawdown': float(worst_dd),
            'value_at_risk': float(var_return),
            'expected_shortfall': float(expected_shortfall),
            'ruin_threshold': float(ruin_threshold),
            'confidence_level': float(self.confidence_level)
        }
    
    def _calculate_confidence_intervals(self, simulation_results: List[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """Calculate confidence intervals for key metrics."""
        if not simulation_results:
            return {}
        
        # Extract metric names
        metric_names = list(simulation_results[0].keys())
        
        # Calculate confidence intervals for each metric
        confidence_intervals = {}
        alpha = 1 - self.confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        for metric in metric_names:
            values = [result[metric] for result in simulation_results if metric in result]
            if values:
                lower_bound = np.percentile(values, lower_percentile)
                upper_bound = np.percentile(values, upper_percentile)
                
                confidence_intervals[metric] = {
                    'lower_bound': float(lower_bound),
                    'upper_bound': float(upper_bound),
                    'confidence_level': float(self.confidence_level)
                }
        
        return confidence_intervals
    
    def _get_worst_case_scenario(self, simulation_results: List[Dict[str, float]]) -> Dict[str, float]:
        """Get the worst case scenario from simulations."""
        if not simulation_results:
            return {}
        
        # Find simulation with worst total return
        worst_idx = np.argmin([result['total_return'] for result in simulation_results])
        return simulation_results[worst_idx]
    
    def _get_best_case_scenario(self, simulation_results: List[Dict[str, float]]) -> Dict[str, float]:
        """Get the best case scenario from simulations."""
        if not simulation_results:
            return {}
        
        # Find simulation with best total return
        best_idx = np.argmax([result['total_return'] for result in simulation_results])
        return simulation_results[best_idx]
    
    def run_enhanced_monte_carlo_analysis(self, 
                                        trade_history: List[Dict[str, Any]], 
                                        initial_capital: float = 10000.0) -> Dict[str, Any]:
        """
        Run enhanced Monte Carlo analysis with multiple risk perspectives.
        """
        if not trade_history:
            return {"error": "No trade history provided"}
        
        # Run both Monte Carlo and Bootstrap simulations
        mc_results = self.run_monte_carlo_simulation(trade_history, initial_capital)
        bs_results = self.run_bootstrap_simulation(trade_history, initial_capital)
        
        # Combine results
        combined_results = {
            'monte_carlo_results': mc_results,
            'bootstrap_results': bs_results,
            'combined_analysis': self._compare_simulation_methods(mc_results, bs_results)
        }
        
        return combined_results
    
    def _compare_simulation_methods(self, mc_results: Dict, bs_results: Dict) -> Dict[str, Any]:
        """Compare Monte Carlo vs Bootstrap results."""
        comparison = {}
        
        # Compare key metrics
        mc_agg = mc_results.get('aggregated_metrics', {})
        bs_agg = bs_results.get('aggregated_metrics', {})
        
        for metric in ['avg_total_return', 'avg_max_drawdown', 'avg_sharpe_ratio', 'avg_win_rate']:
            mc_val = mc_agg.get(metric, 0)
            bs_val = bs_agg.get(metric, 0)
            
            comparison[f'{metric}_difference'] = mc_val - bs_val
            comparison[f'{metric}_mc'] = mc_val
            comparison[f'{metric}_bs'] = bs_val
        
        # Compare risk metrics
        mc_risk = mc_results.get('risk_metrics', {})
        bs_risk = bs_results.get('risk_metrics', {})
        
        for risk_metric in ['probability_of_ruin', 'worst_case_drawdown', 'value_at_risk']:
            mc_val = mc_risk.get(risk_metric, 0)
            bs_val = bs_risk.get(risk_metric, 0)
            
            comparison[f'{risk_metric}_difference'] = mc_val - bs_val
            comparison[f'{risk_metric}_mc'] = mc_val
            comparison[f'{risk_metric}_bs'] = bs_val
        
        return comparison


def run_monte_carlo_analysis_from_backtest_results(backtest_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run Monte Carlo analysis on backtest results.
    
    Args:
        backtest_results: Results from a backtest run containing trade history
        
    Returns:
        Dictionary with Monte Carlo analysis results
    """
    logger = EnhancedLogger("MonteCarloAnalysis")
    
    # Extract trade history from backtest results
    # This assumes the backtest results contain a 'trades' field
    all_trades = []
    
    # Handle different backtest result structures
    if 'multi_strategy_results' in backtest_results:
        # Multi-strategy results
        for strategy_name, strategy_results in backtest_results['multi_strategy_results'].items():
            if 'backtest_results' in strategy_results:
                for symbol, symbol_results in strategy_results['backtest_results'].items():
                    if 'trades' in symbol_results:
                        all_trades.extend(symbol_results['trades'])
    elif 'backtest_results' in backtest_results:
        # Single strategy results
        for symbol, symbol_results in backtest_results['backtest_results'].items():
            if 'trades' in symbol_results:
                all_trades.extend(symbol_results['trades'])
    elif 'individual_results' in backtest_results:
        # Portfolio backtest results
        for strategy_name, strategy_results in backtest_results['individual_results'].items():
            for symbol, symbol_results in strategy_results.items():
                if 'trades' in symbol_results:
                    all_trades.extend(symbol_results['trades'])
    
    if not all_trades:
        logger.warning("No trade history found in backtest results")
        return {"error": "No trade history found in backtest results"}
    
    # Get initial capital from backtest results
    initial_capital = backtest_results.get('initial_capital', 10000.0)
    
    # Run Monte Carlo analysis
    simulator = MonteCarloRiskSimulator(num_simulations=1000, confidence_level=0.95)
    results = simulator.run_enhanced_monte_carlo_analysis(all_trades, initial_capital)
    
    logger.info("Monte Carlo analysis completed on backtest results")
    
    return results