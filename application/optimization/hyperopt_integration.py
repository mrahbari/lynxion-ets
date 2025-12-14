"""
Real hyperopt integration for the enterprise hedge fund trading system.
Implements proper hyperparameter optimization using the actual hyperopt library.
"""
from typing import Dict, List, Any, Optional, Callable
import pandas as pd
import numpy as np
from hyperopt import fmin, tpe, hp, STATUS_OK, STATUS_FAIL, Trials, space_eval
from hyperopt.pyll.base import Apply
import traceback
from datetime import datetime
from dataclasses import dataclass

from domain.entities.trading_entities import Signal, Order
from domain.value_objects import Symbol, Money, Percentage
from shared.logger import logger


@dataclass
class OptimizationResult:
    """Result of a hyperparameter optimization run"""
    best_params: Dict[str, Any]
    best_value: float
    total_evaluations: int
    execution_time: float
    all_trials: List[Dict[str, Any]]


class RealHyperoptAdapter:
    """Real hyperopt adapter implementing the actual hyperopt library with proper error handling and monitoring."""

    def __init__(self,
                 max_evals: int = 100,
                 algorithm: str = 'tpe',  # Options: 'tpe', 'random', 'anneal', 'atpe'
                 timeout_seconds: Optional[int] = None,
                 early_stopping_rounds: Optional[int] = 15,
                 seed: Optional[int] = 42):
        """
        Initialize the real hyperopt adapter.

        Args:
            max_evals: Maximum number of function evaluations
            algorithm: Hyperopt algorithm ('tpe', 'random', 'anneal', 'atpe')
            timeout_seconds: Optional timeout in seconds
            early_stopping_rounds: Optional early stopping after N rounds without improvement
            seed: Random seed for reproducible results
        """
        self.max_evals = max_evals
        self.algorithm = self._get_hyperopt_algorithm(algorithm)
        self.timeout_seconds = timeout_seconds
        self.early_stopping_rounds = early_stopping_rounds
        self.seed = seed
        self.trials = Trials()

    def _get_hyperopt_algorithm(self, algorithm_name: str) -> Callable:
        """Get the hyperopt algorithm function by name"""
        algorithms = {
            'tpe': tpe.suggest,
            'random': lambda *args, **kwargs: hp.choice('_', [hp.uniform('random_choice', 0, 1)]),
            'anneal': anneal.suggest,
            # Note: atpe requires special installation
        }
        
        if algorithm_name in algorithms:
            return algorithms[algorithm_name]
        else:
            logger.warning(f"Algorithm {algorithm_name} not recognized, defaulting to TPE")
            return tpe.suggest

    def optimize(self,
                 objective_function: Callable,
                 parameter_space: Dict[str, Any],
                 minimize: bool = True) -> OptimizationResult:
        """
        Execute hyperparameter optimization using real hyperopt.

        Args:
            objective_function: Function to minimize/maximize
            parameter_space: Hyperopt parameter space (e.g., hp.uniform('param', 0, 1))
            minimize: If True, minimizes the function; if False, maximizes (by negating)

        Returns:
            OptimizationResult containing best parameters and metrics
        """
        start_time = datetime.now()
        self.trials = Trials()  # Reset trials for new optimization

        # Wrap the objective function to handle maximize/minimize and errors
        def wrapped_objective(params):
            try:
                result = objective_function(params)

                # Validate result format
                if isinstance(result, dict):
                    # Expected format from hyperopt: {'loss': value, 'status': STATUS_OK, ...}
                    if 'loss' not in result and 'status' not in result:
                        # Assume it's a simple value
                        loss_value = float(result)
                    else:
                        loss_value = float(result.get('loss', result.get('value', 0)))
                    
                    # Apply direction adjustment if maximizing
                    if not minimize:
                        loss_value = -loss_value
                        
                    return {
                        'loss': loss_value,
                        'status': result.get('status', STATUS_OK),
                        **{k: v for k, v in result.items() if k not in ['loss', 'status']}
                    }
                else:
                    # Simple value returned
                    loss_value = float(result)
                    if not minimize:
                        loss_value = -loss_value
                    
                    return {
                        'loss': loss_value,
                        'status': STATUS_OK
                    }
                    
            except Exception as e:
                logger.error(f"Error in objective function: {e}\n{traceback.format_exc()}")
                return {
                    'loss': float('inf') if minimize else float('-inf'),
                    'status': STATUS_FAIL,
                    'error': str(e),
                    'params': params
                }

        try:
            # Set up optimization options
            optimization_kwargs = {
                'fn': wrapped_objective,
                'space': parameter_space,
                'algo': self.algorithm,
                'max_evals': self.max_evals,
                'trials': self.trials
            }
            
            if self.seed is not None:
                optimization_kwargs['rstate'] = np.random.RandomState(self.seed)

            # Perform optimization
            best = fmin(**optimization_kwargs)

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Process the optimization results
            best_params = space_eval(parameter_space, best)
            
            # Identify best value from the trials
            trial_losses = [trial.get('result', {}).get('loss', float('inf')) 
                          for trial in self.trials.trials if trial['result']['status'] == STATUS_OK]
            
            best_value = min(trial_losses) if minimize and trial_losses else (max(trial_losses) if not minimize and trial_losses else float('inf'))
            
            if not minimize:
                best_value = -best_value  # Revert the negation for maximization problems

            # Extract all results from successful trials
            all_results = []
            for trial in self.trials.trials:
                if trial['result']['status'] == STATUS_OK:
                    result_data = {
                        'params': trial['misc']['vals'],
                        'loss': trial['result'].get('loss'),
                        'status': trial['result']['status']
                    }
                    # Add any additional metrics from the result
                    result_data.update({
                        k: v for k, v in trial['result'].items() 
                        if k not in ['loss', 'status', 'params']
                    })
                    all_results.append(result_data)

            logger.info(f"Hyperopt optimization completed in {execution_time:.2f}s")
            logger.info(f"Best parameters: {best_params}")
            logger.info(f"Best value: {best_value}")

            return OptimizationResult(
                best_params=best_params,
                best_value=best_value,
                total_evaluations=len(self.trials.trials),
                execution_time=execution_time,
                all_trials=all_results
            )

        except Exception as e:
            logger.error(f"Error during hyperopt optimization: {e}\n{traceback.format_exc()}")
            raise

    def optimize_strategy_parameters(self,
                                   strategy_class,
                                   data: pd.DataFrame,
                                   parameter_space: Dict[str, Any],
                                   target_metric: str = 'sharpe_ratio',
                                   minimize: bool = False) -> OptimizationResult:
        """
        Optimize parameters for a specific trading strategy.

        Args:
            strategy_class: The strategy class to optimize
            data: Market data for backtesting
            parameter_space: Hyperopt parameter space
            target_metric: Which metric to optimize ('sharpe_ratio', 'total_return', 'max_drawdown', etc.)
            minimize: Whether to minimize (True) or maximize (False) the target metric

        Returns:
            OptimizationResult containing the best parameters
        """
        def strategy_objective(params):
            try:
                # Create strategy instance with parameters
                strategy = strategy_class(**params)
                
                # Execute backtest with the strategy
                backtest_result = self._execute_strategy_backtest(strategy, data)
                
                # Extract the target metric from results
                metric_value = backtest_result.get(target_metric, 0)
                
                # Handle special cases for metrics that should be minimized
                if target_metric == 'max_drawdown':
                    # Max drawdown should be minimized (closer to 0 is better)
                    minimize_override = True
                    metric_value = abs(metric_value)  # Make positive for minimization
                else:
                    minimize_override = minimize
                
                result = {
                    'loss': -metric_value if minimize_override else metric_value,
                    'status': STATUS_OK,
                    'params': params,
                    'metrics': backtest_result
                }
                
                logger.info(f"Evaluated params: {params}, {target_metric}: {metric_value}, loss: {result['loss']}")
                return result
                
            except Exception as e:
                logger.error(f"Error evaluating strategy with params {params}: {e}")
                return {
                    'loss': float('inf') if not minimize else float('-inf'),
                    'status': STATUS_FAIL,
                    'params': params,
                    'error': str(e)
                }

        return self.optimize(
            objective_function=strategy_objective,
            parameter_space=parameter_space,
            minimize=minimize
        )

    def _execute_strategy_backtest(self, strategy, data: pd.DataFrame) -> Dict[str, float]:
        """
        Execute a backtest for a given strategy and data.

        Args:
            strategy: Strategy instance to backtest
            data: Market data for backtesting

        Returns:
            Dictionary with backtesting results and metrics
        """
        # This would call the real backtesting service
        # For now, we'll return mock results as a placeholder
        # In a real implementation, this would connect to the backtesting service
        
        # Create mock backtest results based on strategy and data
        # In a real implementation, this would be replaced with actual backtesting
        mock_returns = np.random.normal(0.001, 0.02, len(data))  # Daily returns
        cumulative_returns = np.cumprod(1 + mock_returns) - 1
        
        # Calculate various performance metrics
        total_return = cumulative_returns[-1] if len(cumulative_returns) > 0 else 0
        num_trades = len(data) // 10  # Mock number of trades
        win_rate = 0.55 + np.random.uniform(-0.1, 0.1)  # Mock win rate around 55%
        
        # Calculate Sharpe ratio (simplified)
        avg_return = np.mean(mock_returns) if len(mock_returns) > 0 else 0
        volatility = np.std(mock_returns) if len(mock_returns) > 0 else 0.01
        sharpe_ratio = (avg_return / volatility) * np.sqrt(252) if volatility > 0 else 0  # Annualized
        
        # Calculate max drawdown
        rolling_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - rolling_max)
        max_drawdown = min(drawdowns) if len(drawdowns) > 0 else 0.0
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'profit_factor': 1.8 + np.random.uniform(-0.2, 0.2),  # Mock profit factor
            'average_win': 0.02 + np.random.uniform(-0.005, 0.005),  # Mock average win
            'average_loss': -0.015 + np.random.uniform(-0.003, 0.003)  # Mock average loss
        }

    def get_trial_history(self) -> List[Dict[str, Any]]:
        """Get the history of all optimization trials"""
        return [trial for trial in self.trials.trials]

    def get_best_trial(self) -> Optional[Dict[str, Any]]:
        """Get the best performing trial from the optimization"""
        if not self.trials.trials:
            return None
        
        successful_trials = [
            trial for trial in self.trials.trials
            if trial['result']['status'] == STATUS_OK
        ]
        
        if not successful_trials:
            return None
        
        # Find the trial with the best (lowest) loss
        best_trial = min(successful_trials, key=lambda t: t['result'].get('loss', float('inf')))
        return best_trial


class MultiObjectiveHyperoptAdapter(RealHyperoptAdapter):
    """Hyperopt adapter for multi-objective optimization."""

    def optimize_multi_objective(self,
                               objective_functions: List[Callable],
                                 weights: List[float],
                                 parameter_space: Dict[str, Any]) -> OptimizationResult:
        """
        Optimize multiple objectives simultaneously.

        Args:
            objective_functions: List of objective functions to optimize
            weights: Weights for each objective function
            parameter_space: Hyperopt parameter space

        Returns:
            OptimizationResult containing the best parameters
        """
        if len(objective_functions) != len(weights):
            raise ValueError("Number of objective functions must match number of weights")

        def combined_objective(params):
            try:
                # Evaluate each objective function
                values = []
                for obj_func in objective_functions:
                    result = obj_func(params)
                    if isinstance(result, dict):
                        value = result.get('loss', result.get('value', 0))
                    else:
                        value = float(result)
                    values.append(value)

                # Weighted combination of objectives
                combined_value = sum(w * v for w, v in zip(weights, values))

                return {
                    'loss': combined_value,
                    'status': STATUS_OK,
                    'params': params,
                    'individual_values': values
                }
            except Exception as e:
                logger.error(f"Error in multi-objective function: {e}")
                return {
                    'loss': float('inf'),
                    'status': STATUS_FAIL,
                    'params': params,
                    'error': str(e)
                }

        return self.optimize(
            objective_function=combined_objective,
            parameter_space=parameter_space,
            minimize=True
        )