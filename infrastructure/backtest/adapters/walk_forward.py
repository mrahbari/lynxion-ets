from typing import Dict, List, Optional, Callable, Tuple
from shared.types import Signal, Order
from shared.logger import logger
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from .simulator import BacktestSimulator


class WalkForwardAnalyzer:
    """Walk-forward analysis for optimizing and validating trading strategies"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Walk-forward parameters
        self.in_sample_size = config.get('in_sample_size', 252)  # 1 year of data for optimization
        self.out_of_sample_size = config.get('out_of_sample_size', 63)  # 3 months for validation
        self.walk_forward_count = config.get('walk_forward_count', 10)  # Number of walk-forward periods
        self.reoptimization_frequency = config.get('reoptimization_frequency', 21)  # Re-optimize every 21 days
        self.performance_threshold = config.get('performance_threshold', 0.05)  # Min Sharpe ratio to continue
        self.max_drawdown_threshold = config.get('max_drawdown_threshold', 0.20)  # Max 20% drawdown
        
        # Storage for results
        self.out_of_sample_results = []
        self.in_sample_results = []
        self.optimized_parameters = []
        self.current_parameters = {}
        
    def run_walk_forward_analysis(self, 
                                  data: Dict[str, pd.DataFrame], 
                                  strategy_optimizer: Callable,
                                  backtester_class: type = BacktestSimulator) -> Dict:
        """Run the complete walk-forward analysis"""
        
        # Split data into walk-forward periods
        periods = self._create_walk_forward_periods(data)
        
        for i, (in_sample_data, out_of_sample_data) in enumerate(periods):
            logger.info(f"Walk-forward period {i+1}/{len(periods)}")
            
            # Optimize parameters on in-sample data
            optimized_params = strategy_optimizer(in_sample_data)
            self.optimized_parameters.append(optimized_params)
            
            # Test on out-of_sample data
            out_of_sample_result = self._test_on_out_of_sample(
                out_of_sample_data, 
                backtester_class, 
                optimized_params
            )
            
            # Add results
            self.out_of_sample_results.append(out_of_sample_result)
            
            # Check if performance is acceptable
            if not self._is_acceptable_performance(out_of_sample_result):
                logger.warning(f"Out-of-sample performance below threshold in period {i+1}, stopping walk-forward analysis")
                break
        
        return self._compile_results()
    
    def _create_walk_forward_periods(self, data: Dict[str, pd.DataFrame]) -> List[Tuple[Dict, Dict]]:
        """Create in-sample and out-of-sample data periods for walk-forward analysis"""
        periods = []
        
        # Find the minimum common date range across all symbols
        start_dates = [df.index.min() for df in data.values() if not df.empty]
        end_dates = [df.index.max() for df in data.values() if not df.empty]
        
        if not start_dates or not end_dates:
            raise ValueError("No valid data provided")
        
        common_start = max(start_dates)
        common_end = min(end_dates)
        
        # Create walk-forward periods
        current_date = common_start
        
        while current_date + timedelta(days=self.in_sample_size + self.out_of_sample_size) <= common_end:
            # In-sample period
            in_sample_start = current_date
            in_sample_end = current_date + timedelta(days=self.in_sample_size)
            
            # Out-of-sample period
            out_of_sample_start = in_sample_end
            out_of_sample_end = out_of_sample_start + timedelta(days=self.out_of_sample_size)
            
            # Extract data for both periods
            in_sample_data = {}
            out_of_sample_data = {}
            
            for symbol, df in data.items():
                in_sample_mask = (df.index >= in_sample_start) & (df.index < in_sample_end)
                out_of_sample_mask = (df.index >= out_of_sample_start) & (df.index < out_of_sample_end)
                
                in_sample_data[symbol] = df[in_sample_mask]
                out_of_sample_data[symbol] = df[out_of_sample_mask]
            
            periods.append((in_sample_data, out_of_sample_data))
            
            # Move to next period (could overlap or be consecutive)
            current_date += timedelta(days=self.reoptimization_frequency)
        
        return periods
    
    def _test_on_out_of_sample(self, 
                              data: Dict[str, pd.DataFrame], 
                              backtester_class: type, 
                              params: Dict) -> Dict:
        """Test strategy on out-of-sample data"""
        # Create backtester instance
        backtester = backtester_class(params)
        backtester.load_market_data(data)
        
        # Create placeholder strategy function that uses the optimized parameters
        def strategy_func(signal, backtester_state):
            # This would be replaced by the actual strategy implementation
            # using the optimized parameters
            return None  # Placeholder
        
        # Run the backtest
        results = backtester.run_backtest(
            signal_generator=lambda data: [],  # Placeholder
            strategy_func=strategy_func
        )
        
        return results
    
    def _is_acceptable_performance(self, results: Dict) -> bool:
        """Check if performance meets threshold requirements"""
        sharpe_ratio = results.get('sharpe_ratio', 0)
        max_drawdown = results.get('max_drawdown', 0)
        
        return (sharpe_ratio >= self.performance_threshold and 
                max_drawdown <= self.max_drawdown_threshold)
    
    def run_parameter_optimization(self, 
                                   data: Dict[str, pd.DataFrame], 
                                   parameter_ranges: Dict[str, List],
                                   objective_func: Callable) -> Dict:
        """Run parameter optimization on in-sample data"""
        
        best_params = {}
        best_score = float('-inf')
        
        # Generate all parameter combinations
        param_combinations = self._generate_param_combinations(parameter_ranges)
        
        for params in param_combinations:
            # Create and run backtester with these parameters
            backtester = BacktestSimulator(params)
            backtester.load_market_data(data)
            
            # Run backtest with these parameters
            results = backtester.run_backtest(
                signal_generator=lambda data: [],  # Placeholder
                strategy_func=lambda signal, state: None  # Placeholder
            )
            
            # Calculate objective score
            score = objective_func(results)
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
        
        logger.info(f"Optimization completed. Best parameters: {best_params}, Score: {best_score}")
        return best_params
    
    def _generate_param_combinations(self, param_ranges: Dict[str, List]) -> List[Dict]:
        """Generate all combinations of parameters"""
        import itertools
        
        keys = list(param_ranges.keys())
        values = list(param_ranges.values())
        
        combinations = []
        for combination in itertools.product(*values):
            combo_dict = dict(zip(keys, combination))
            combinations.append(combo_dict)
        
        return combinations
    
    def calculate_statistical_significance(self) -> Dict:
        """Calculate statistical significance of results"""
        if not self.out_of_sample_results:
            return {}
        
        # Extract key metrics
        sharpes = [result.get('sharpe_ratio', 0) for result in self.out_of_sample_results]
        returns = [result.get('total_return', 0) for result in self.out_of_sample_results]
        drawdowns = [result.get('max_drawdown', 0) for result in self.out_of_sample_results]
        
        return {
            'sharpe_mean': np.mean(sharpes),
            'sharpe_std': np.std(sharpes),
            'sharpe_t_stat': np.mean(sharpes) / (np.std(sharpes) / np.sqrt(len(sharpes))) if np.std(sharpes) > 0 else 0,
            'return_mean': np.mean(returns),
            'return_std': np.std(returns),
            'drawdown_mean': np.mean(drawdowns),
            'drawdown_max': np.max(drawdowns),
            'consistency_score': self._calculate_consistency_score()
        }
    
    def _calculate_consistency_score(self) -> float:
        """Calculate how consistent the results are across periods"""
        if len(self.out_of_sample_results) < 2:
            return 0.0
        
        # Calculate the standard deviation of returns relative to mean
        returns = [result.get('total_return', 0) for result in self.out_of_sample_results]
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Consistency is inversely related to coefficient of variation
        if mean_return == 0:
            return 0.0
            
        cv = std_return / abs(mean_return)
        consistency_score = max(0, 1 - cv)  # Higher score for lower variation
        
        return consistency_score
    
    def _compile_results(self) -> Dict:
        """Compile all walk-forward analysis results"""
        if not self.out_of_sample_results:
            return {}
        
        # Aggregate performance metrics
        total_returns = [result.get('total_return', 0) for result in self.out_of_sample_results]
        sharpes = [result.get('sharpe_ratio', 0) for result in self.out_of_sample_results]
        drawdowns = [result.get('max_drawdown', 0) for result in self.out_of_sample_results]
        
        # Calculate aggregate metrics
        avg_return = np.mean(total_returns) if total_returns else 0
        avg_sharpe = np.mean(sharpes) if sharpes else 0
        avg_drawdown = np.mean(drawdowns) if drawdowns else 0
        max_drawdown = np.max(drawdowns) if drawdowns else 0
        
        # Calculate pass rate (periods that exceeded minimum threshold)
        passed_periods = sum(1 for s in sharpes if s >= self.performance_threshold)
        pass_rate = passed_periods / len(sharpes) if sharpes else 0
        
        # Include statistical significance
        stats = self.calculate_statistical_significance()
        
        # Compile comprehensive results
        results = {
            'total_periods': len(self.out_of_sample_results),
            'passed_periods': passed_periods,
            'pass_rate': pass_rate,
            'avg_total_return': avg_return,
            'avg_sharpe_ratio': avg_sharpe,
            'avg_max_drawdown': avg_drawdown,
            'max_drawdown': max_drawdown,
            'out_of_sample_results': self.out_of_sample_results,
            'optimized_parameters_history': self.optimized_parameters,
            'statistical_significance': stats,
            'parameter_stability': self._calculate_parameter_stability()
        }
        
        return results
    
    def _calculate_parameter_stability(self) -> float:
        """Calculate how stable the optimized parameters are across periods"""
        if len(self.optimized_parameters) < 2:
            return 1.0  # Perfect stability if only one period
        
        # Calculate parameter stability as the inverse of coefficient of variation
        # For simplicity, we'll just look at the keys that change
        all_keys = set()
        for params in self.optimized_parameters:
            all_keys.update(params.keys())
        
        stability_scores = []
        for key in all_keys:
            values = [params.get(key, 0) for params in self.optimized_parameters if key in params]
            if len(values) > 1:
                mean_val = np.mean(values)
                std_val = np.std(values)
                if mean_val != 0:
                    cv = std_val / abs(mean_val)
                    stability_scores.append(max(0, 1 - cv))  # Higher stability for lower variation
        
        return np.mean(stability_scores) if stability_scores else 1.0
    
    def get_parameter_evolution(self) -> Dict[str, List]:
        """Get the evolution of optimized parameters over time"""
        if not self.optimized_parameters:
            return {}
        
        # Extract parameter values over time
        param_evolution = {}
        all_keys = set()
        for params in self.optimized_parameters:
            all_keys.update(params.keys())
        
        for key in all_keys:
            param_evolution[key] = [
                params.get(key, None) for params in self.optimized_parameters
            ]
        
        return param_evolution
    
    def validate_strategy_robustness(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """Additional validation of strategy robustness"""
        # Perform additional tests like stress testing, market regime testing, etc.
        results = {
            'parameter_stability_score': self._calculate_parameter_stability(),
            'out_of_sample_performance': {
                'avg_sharpe': np.mean([r.get('sharpe_ratio', 0) for r in self.out_of_sample_results]),
                'avg_return': np.mean([r.get('total_return', 0) for r in self.out_of_sample_results]),
            },
            'robustness_indicator': self._calculate_robustness_indicator()
        }
        
        return results
    
    def _calculate_robustness_indicator(self) -> float:
        """Calculate a combined robustness indicator"""
        if not self.out_of_sample_results:
            return 0.0
        
        # Combine various factors for robustness
        sharpes = [result.get('sharpe_ratio', 0) for result in self.out_of_sample_results]
        positive_sharpes = [s for s in sharpes if s > 0]
        
        # Percentage of positive Sharpe ratios
        positive_ratio = len(positive_sharpes) / len(sharpes)
        
        # Average Sharpe ratio
        avg_sharpe = np.mean(sharpes)
        
        # Stability of results (inverse of standard deviation)
        stability = 1 / (1 + np.std(sharpes))
        
        # Combine into a robustness score
        robustness = (positive_ratio * 0.4) + (max(0, avg_sharpe) * 0.4) + (stability * 0.2)
        
        return min(1.0, max(0.0, robustness))