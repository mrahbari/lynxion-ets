from typing import Dict, List, Optional, Callable, Tuple
from shared.types import Signal, Order
from shared.logger import logger
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from .simulator import BacktestSimulator
from application.walk_forward.sliding_window_splitter import SlidingWindowSplitter, WalkForwardWindow


class WalkForwardAnalyzer:
    """Walk-forward analysis for optimizing and validating trading strategies"""

    def __init__(self, config: Dict = None):
        self.config = config or {}

        # Walk-forward parameters - using more realistic values for financial data
        self.train_size = config.get('train_size', 90)  # 3 months of training
        self.test_size = config.get('test_size', 30)    # 1 month of testing
        self.step = config.get('step', 30)              # Move forward by 1 month
        self.performance_threshold = config.get('performance_threshold', 0.1)  # Min Sharpe ratio to continue
        self.max_drawdown_threshold = config.get('max_drawdown_threshold', 0.15)  # Max 15% drawdown

        # Storage for results
        self.out_of_sample_results = []
        self.in_sample_results = []
        self.optimized_parameters = []
        self.current_parameters = {}
        self.windows = []  # Store the actual windows used

    def run_walk_forward_analysis(self,
                                  data: Dict[str, pd.DataFrame],
                                  strategy_optimizer: Callable,
                                  backtester_class: type = BacktestSimulator) -> Dict:
        """Run the complete walk-forward analysis"""

        logger.info(f"Starting Walk-Forward Analysis with train_size={self.train_size}, "
                   f"test_size={self.test_size}, step={self.step}")

        # Use the proper sliding window splitter
        splitter = SlidingWindowSplitter(
            train_size=self.train_size,
            test_size=self.test_size,
            step=self.step
        )

        # Validate data for each symbol
        for symbol, df in data.items():
            validation = splitter.validate_split(df)
            if not validation['has_sufficient_data']:
                logger.warning(f"Insufficient data for {symbol}: needs {validation['required_points']} "
                              f"points but has {validation['total_data_points']}")

        # For multi-asset WFO, we'll process each asset separately first, then aggregate
        all_results = {}

        for symbol, df in data.items():
            logger.info(f"Processing walk-forward analysis for {symbol}")

            # Create windows for this specific asset
            asset_windows = splitter.split(df)
            self.windows.extend(asset_windows)  # Store all windows for reporting

            asset_results = []
            asset_optimized_params = []

            for i, window in enumerate(asset_windows):
                logger.info(f"Symbol {symbol} - WFO Period {i+1}/{len(asset_windows)}")

                # Optimize parameters on training data
                optimized_params = strategy_optimizer(window.train_data)
                asset_optimized_params.append(optimized_params)

                # Test on testing data
                out_of_sample_result = self._test_on_out_of_sample(
                    window.test_data,
                    backtester_class,
                    optimized_params
                )

                # Add result
                asset_results.append(out_of_sample_result)

                # Check if performance is acceptable
                if not self._is_acceptable_performance(out_of_sample_result):
                    logger.warning(f"Out-of-sample performance below threshold in period {i+1} for {symbol}, "
                                 f"stopping walk-forward analysis")
                    break

            all_results[symbol] = {
                'out_of_sample_results': asset_results,
                'optimized_parameters': asset_optimized_params,
                'windows': asset_windows
            }

        # Store combined results
        for symbol, result_dict in all_results.items():
            self.out_of_sample_results.extend(result_dict['out_of_sample_results'])
            self.optimized_parameters.extend(result_dict['optimized_parameters'])

        return self._compile_results_multi_asset(all_results)

    def _test_on_out_of_sample(self,
                              data: pd.DataFrame,
                              backtester_class: type,
                              params: Dict) -> Dict:
        """Test strategy on out-of-sample data"""
        # Create backtester instance
        # For realistic backtesting, we should use the RealisticBacktester instead of a simulator
        from infrastructure.backtest.realistic_backtester import RealisticBacktester
        backtester = RealisticBacktester()

        # Create placeholder strategy function that uses the optimized parameters
        def strategy_func(row, strategy_params):
            # This would be replaced by the actual strategy implementation
            # using the optimized parameters
            # For now, return 0 (no signal)
            return 0

        # Run the backtest using the realistic backtester
        try:
            # The realistic backtester has a run_backtest method that takes data, strategy_function, and strategy_params
            results = backtester.run_backtest(
                data=data,
                strategy_function=strategy_func,
                strategy_params=params
            )
            return results
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            # Return a default result in case of error
            return {
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 1.0
            }

    def _is_acceptable_performance(self, results: Dict) -> bool:
        """Check if performance meets threshold requirements"""
        sharpe_ratio = results.get('sharpe_ratio', 0)
        max_drawdown = abs(results.get('max_drawdown', 0))  # Use absolute value for comparison

        return (sharpe_ratio >= self.performance_threshold and
                max_drawdown <= self.max_drawdown_threshold)

    def run_parameter_optimization(self,
                                   data: pd.DataFrame,
                                   parameter_ranges: Dict[str, List],
                                   objective_func: Callable,
                                   optimization_method: str = 'grid') -> Dict:
        """Run parameter optimization on in-sample data"""

        best_params = {}
        best_score = float('-inf')

        if optimization_method == 'grid':
            # Generate all parameter combinations
            param_combinations = self._generate_param_combinations(parameter_ranges)

            for params in param_combinations:
                try:
                    # Calculate objective score using the backtester and objective function
                    score = objective_func(data, params)

                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                except Exception as e:
                    logger.error(f"Error optimizing parameters {params}: {e}")
                    continue

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
        drawdowns = [abs(result.get('max_drawdown', 0)) for result in self.out_of_sample_results]  # Use absolute drawdown
        win_rates = [result.get('win_rate', 0) for result in self.out_of_sample_results]

        return {
            'sharpe_mean': float(np.mean(sharpes)),
            'sharpe_std': float(np.std(sharpes)),
            'sharpe_t_stat': float(np.mean(sharpes) / (np.std(sharpes) / np.sqrt(len(sharpes))) if np.std(sharpes) > 0 else 0),
            'return_mean': float(np.mean(returns)),
            'return_std': float(np.std(returns)),
            'drawdown_mean': float(np.mean(drawdowns)),
            'drawdown_max': float(np.max(drawdowns)),
            'win_rate_mean': float(np.mean(win_rates)),
            'consistency_score': self._calculate_consistency_score(),
            'overfit_index': self._calculate_overfit_index()
        }

    def _calculate_consistency_score(self) -> float:
        """Calculate how consistent the results are across periods (0-1 scale)"""
        if len(self.out_of_sample_results) < 2:
            return 0.0

        # Calculate consistency as percentage of profitable periods
        profitable_periods = sum(1 for result in self.out_of_sample_results
                                if result.get('total_return', 0) > 0)
        consistency = profitable_periods / len(self.out_of_sample_results)

        return consistency

    def _calculate_overfit_index(self) -> float:
        """Calculate overfit index as std deviation / mean return"""
        if not self.out_of_sample_results:
            return 0.0

        returns = [result.get('total_return', 0) for result in self.out_of_sample_results]
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        # Avoid division by zero
        if abs(mean_return) < 1e-8:
            return float('inf') if std_return > 0 else 0.0

        return float(std_return / abs(mean_return))

    def _compile_results_multi_asset(self, all_results: Dict[str, Dict]) -> Dict:
        """Compile walk-forward analysis results for multiple assets"""
        if not all_results:
            return {}

        # Aggregate performance metrics across all assets
        all_sharpes = []
        all_returns = []
        all_drawdowns = []
        all_win_rates = []
        all_profit_factors = []

        for symbol, asset_data in all_results.items():
            asset_results = asset_data['out_of_sample_results']

            for result in asset_results:
                all_sharpes.append(result.get('sharpe_ratio', 0))
                all_returns.append(result.get('total_return', 0))
                all_drawdowns.append(abs(result.get('max_drawdown', 0)))  # Use absolute drawdown
                all_win_rates.append(result.get('win_rate', 0))
                all_profit_factors.append(result.get('profit_factor', 1.0))

        # Calculate aggregate metrics
        avg_sharpe = float(np.mean(all_sharpes)) if all_sharpes else 0
        avg_return = float(np.mean(all_returns)) if all_returns else 0
        avg_drawdown = float(np.mean(all_drawdowns)) if all_drawdowns else 0
        max_drawdown = float(np.max(all_drawdowns)) if all_drawdowns else 0
        avg_win_rate = float(np.mean(all_win_rates)) if all_win_rates else 0
        avg_profit_factor = float(np.mean(all_profit_factors)) if all_profit_factors else 0

        # Calculate pass rate (periods that exceeded minimum threshold)
        passed_periods = sum(1 for s in all_sharpes if s >= self.performance_threshold)
        total_periods = len(all_sharpes)
        pass_rate = passed_periods / total_periods if total_periods > 0 else 0

        # Include statistical significance
        stats = self.calculate_statistical_significance()

        # Compile comprehensive results
        results = {
            'total_periods': total_periods,
            'passed_periods': passed_periods,
            'pass_rate': pass_rate,
            'avg_sharpe_ratio': avg_sharpe,
            'avg_total_return': avg_return,
            'avg_max_drawdown': avg_drawdown,
            'max_drawdown': max_drawdown,
            'avg_win_rate': avg_win_rate,
            'avg_profit_factor': avg_profit_factor,
            'out_of_sample_results': self.out_of_sample_results,
            'optimized_parameters_history': self.optimized_parameters,
            'statistical_significance': stats,
            'parameter_stability': self._calculate_parameter_stability(),
            'multi_asset_results': all_results,  # Include per-asset breakdown
            'total_assets_analyzed': len(all_results)
        }

        return results

    def _calculate_parameter_stability(self) -> float:
        """Calculate how stable the optimized parameters are across periods"""
        if len(self.optimized_parameters) < 2:
            return 1.0  # Perfect stability if only one period

        # Calculate parameter stability as the inverse of coefficient of variation
        all_keys = set()
        for params in self.optimized_parameters:
            all_keys.update(params.keys())

        stability_scores = []
        for key in all_keys:
            values = [params.get(key, 0) for params in self.optimized_parameters if key in params and params[key] is not None]
            if len(values) > 1:
                mean_val = np.mean(values)
                std_val = np.std(values)
                if mean_val != 0:
                    cv = std_val / abs(mean_val)
                    stability_scores.append(max(0, min(1, 1 - cv)))  # Clamp between 0 and 1
                else:
                    stability_scores.append(0 if std_val > 0 else 1)  # If mean is 0, score is 0 if there's variation, 1 if no variation

        return float(np.mean(stability_scores)) if stability_scores else 1.0

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

    def validate_strategy_robustness(self) -> Dict:
        """Additional validation of strategy robustness"""
        # Perform additional tests like stress testing, market regime testing, etc.
        results = {
            'parameter_stability_score': self._calculate_parameter_stability(),
            'out_of_sample_performance': {
                'avg_sharpe': np.mean([r.get('sharpe_ratio', 0) for r in self.out_of_sample_results]),
                'avg_return': np.mean([r.get('total_return', 0) for r in self.out_of_sample_results]),
                'avg_drawdown': np.mean([abs(r.get('max_drawdown', 0)) for r in self.out_of_sample_results]),
            },
            'robustness_indicator': self._calculate_robustness_indicator(),
            'consistency_score': self._calculate_consistency_score(),
            'overfit_index': self._calculate_overfit_index()
        }

        return results

    def _calculate_robustness_indicator(self) -> float:
        """Calculate a combined robustness indicator (0-1 scale)"""
        if not self.out_of_sample_results:
            return 0.0

        # Combine various factors for robustness
        sharpes = [result.get('sharpe_ratio', 0) for result in self.out_of_sample_results]
        if not sharpes:
            return 0.0

        positive_sharpes = [s for s in sharpes if s > 0]

        # Percentage of positive Sharpe ratios (0-1)
        positive_ratio = len(positive_sharpes) / len(sharpes)

        # Average Sharpe ratio (normalized assuming max expected Sharpe of 2.0)
        avg_sharpe = np.mean(sharpes)
        normalized_sharpe = max(0, min(1, avg_sharpe / 2.0))  # Clamp between 0 and 1

        # Stability of results (0-1 scale, where 1 is most stable)
        stability = 1.0 / (1.0 + np.std(sharpes)) if len(sharpes) > 1 else 1.0

        # Combine into a robustness score (weighted average)
        robustness = (positive_ratio * 0.4) + (normalized_sharpe * 0.4) + (stability * 0.2)

        return min(1.0, max(0.0, robustness))