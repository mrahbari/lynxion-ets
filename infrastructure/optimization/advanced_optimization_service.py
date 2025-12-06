"""Advanced optimization service with multiple algorithms and multi-objective support."""

from typing import Dict, Any, List, Callable
import pandas as pd
from hyperopt import fmin, tpe, rand, anneal, Trials, STATUS_OK
from hyperopt import space_eval
import numpy as np
from datetime import datetime

from shared.logger import EnhancedLogger
from infrastructure.optimization.hyperopt_objective import HyperoptObjective


class AdvancedOptimizationService:
    """Advanced optimization service with multiple algorithms and enhanced features."""

    def __init__(self):
        self.logger = EnhancedLogger("AdvancedOptimizationService")
        self.objective_handler = HyperoptObjective()
        
        # Map algorithm names to hyperopt functions
        self.algorithms = {
            'tpe': tpe.suggest,
            'random': rand.suggest,
            'anneal': anneal.suggest
        }

    def optimize_with_multiple_algorithms(self,
                                        strategy_name: str,
                                        data_dict: Dict[str, pd.DataFrame],
                                        param_space: Dict[str, Any],
                                        risk_config: Dict[str, Any],
                                        algorithms: List[str] = None,
                                        max_evals_per_algo: int = 25,
                                        optimization_objectives: List[str] = None) -> Dict[str, Any]:
        """
        Run optimization using multiple algorithms and combine results.
        
        Args:
            strategy_name: Name of the strategy to optimize
            data_dict: Dictionary of asset data
            param_space: Parameter space for optimization
            risk_config: Risk configuration parameters  
            algorithms: List of algorithm names to use (default: all available)
            max_evals_per_algo: Maximum evaluations per algorithm
            optimization_objectives: List of objectives to optimize
        """
        if algorithms is None:
            algorithms = list(self.algorithms.keys())
        
        if optimization_objectives is None:
            optimization_objectives = ['sharpe_ratio']
        
        results = {}
        best_overall_loss = float('inf')
        best_overall_params = None
        
        # Create objective function
        objective_fn = self.objective_handler.create_objective_function(
            data_dict, risk_config, optimization_objectives=optimization_objectives
        )
        
        for algo_name in algorithms:
            if algo_name not in self.algorithms:
                self.logger.warning(f"Algorithm {algo_name} not supported, skipping")
                continue
                
            self.logger.info(f"Running optimization with {algo_name} algorithm")
            
            trials = Trials()
            
            try:
                # Run optimization with this algorithm
                best = fmin(
                    fn=objective_fn,
                    space=param_space,
                    algo=self.algorithms[algo_name],
                    max_evals=max_evals_per_algo,
                    trials=trials,
                    verbose=False
                )
                
                # Calculate stats for this algorithm
                losses = [trial['result'].get('loss', float('inf')) for trial in trials.trials]
                avg_loss = sum(losses) / len(losses) if losses else float('inf')
                best_loss_for_algo = min(losses) if losses else float('inf')
                
                results[algo_name] = {
                    'best_params': best,
                    'trials_completed': len(trials),
                    'best_loss': best_loss_for_algo,
                    'avg_loss': avg_loss,
                    'all_losses': losses
                }
                
                # Update overall best if this algorithm found a better solution
                if best_loss_for_algo < best_overall_loss:
                    best_overall_loss = best_loss_for_algo
                    best_overall_params = best
                
                self.logger.info(f"{algo_name} completed - Best loss: {best_loss_for_algo:.6f}")
                
            except Exception as e:
                self.logger.error(f"Error running {algo_name} optimization: {e}")
                results[algo_name] = {'error': str(e)}
        
        # Final result combining all algorithms
        final_result = {
            'best_params': best_overall_params,
            'best_loss': best_overall_loss,
            'algorithm_results': results,
            'recommendations': self._analyze_algorithm_performance(results),
            'timestamp': datetime.now().isoformat()
        }
        
        return final_result

    def _analyze_algorithm_performance(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Analyze which algorithms performed best."""
        valid_results = {k: v for k, v in results.items() if 'error' not in v and 'best_loss' in v}
        
        if not valid_results:
            return {'message': 'No valid algorithm results to analyze'}
        
        # Find best performing algorithm
        best_algo = min(valid_results, key=lambda k: valid_results[k]['best_loss'])
        best_loss = valid_results[best_algo]['best_loss']
        
        analysis = {
            'best_performing_algorithm': best_algo,
            'best_algorithm_loss': best_loss,
            'summary': f"Algorithm {best_algo} performed best with loss of {best_loss:.6f}"
        }
        
        # Add relative performance analysis
        for algo_name, result in valid_results.items():
            if result['best_loss'] != best_loss:
                improvement = ((result['best_loss'] - best_loss) / abs(best_loss)) * 100
                analysis[f'{algo_name}_vs_best'] = f"{improvement:.2f}% worse than best"
        
        return analysis

    def multi_objective_optimize(self,
                               data_dict: Dict[str, pd.DataFrame],
                               param_space: Dict[str, Any],
                               risk_config: Dict[str, Any],
                               objectives_weights: Dict[str, float] = None,
                               algorithm: str = 'tpe',
                               max_evals: int = 100) -> Dict[str, Any]:
        """
        Perform multi-objective optimization using weighted combination of objectives.
        
        Args:
            data_dict: Dictionary of asset data
            param_space: Parameter space for optimization
            risk_config: Risk configuration parameters
            objectives_weights: Dictionary of objective names to weights (default: equal weights)
            algorithm: Algorithm to use for optimization
            max_evals: Maximum number of evaluations
        """
        if objectives_weights is None:
            # Default to standard finance metrics with reasonable weights
            objectives_weights = {
                'sharpe_ratio': 0.4,
                'total_return': 0.3,
                'max_drawdown': 0.2,  # Negative value, so higher is better
                'win_rate': 0.1
            }
        
        def weighted_objective(params: Dict[str, Any]) -> Dict[str, Any]:
            """Objective function that combines multiple objectives with weights."""
            # Create an objective function that returns detailed metrics
            # instead of just the loss
            objective_fn = self.objective_handler.create_objective_function(
                data_dict, risk_config, optimization_objectives=list(objectives_weights.keys())
            )
            
            result = objective_fn(params)
            
            # Recalculate as weighted combination
            try:
                # Get metrics for this parameter set
                from infrastructure.backtest.realistic_backtester import RealisticBacktester
                backtester = RealisticBacktester(
                    initial_capital=risk_config.get('initial_capital', 10000.0),
                    fee_rate=risk_config.get('fee_rate', 0.001),
                    slippage_factor=risk_config.get('slippage_factor', 0.0005)
                )
                
                # Calculate metrics across all assets
                composite_metrics = {}
                for obj in objectives_weights.keys():
                    composite_metrics[obj] = 0
                
                asset_count = 0
                for asset_name, df in data_dict.items():
                    if len(df) < 2:
                        continue
                    
                    # Run a simple backtest to get metrics (this is a simplified approach)
                    # In a real implementation, this would use the proper strategy evaluation
                    metrics = self._get_simple_metrics(df, params)
                    
                    for obj in objectives_weights.keys():
                        if obj in metrics:
                            composite_metrics[obj] += metrics[obj]
                    asset_count += 1
                
                if asset_count > 0:
                    for obj in objectives_weights.keys():
                        composite_metrics[obj] /= asset_count  # Average across assets
                
                # Calculate weighted score
                weighted_score = 0
                for obj, weight in objectives_weights.items():
                    value = composite_metrics.get(obj, 0)
                    # For drawdown, higher (less negative) is better, so we might need to flip the sign
                    if obj == 'max_drawdown':
                        value = -value  # Invert so that less negative drawdown scores higher
                    weighted_score += weight * value
                
                result['loss'] = -weighted_score  # Negate because hyperopt minimizes
                result['composite_metrics'] = composite_metrics
                result['weighted_objective'] = weighted_score
                
            except Exception as e:
                self.logger.error(f"Error in weighted objective calculation: {e}")
                result['loss'] = float('inf')
                result['status'] = 'error'
            
            return result

        # Run optimization
        trials = Trials()
        
        try:
            best = fmin(
                fn=weighted_objective,
                space=param_space,
                algo=self.algorithms.get(algorithm, tpe.suggest),
                max_evals=max_evals,
                trials=trials
            )
            
            # Get final metrics for the best parameters
            final_objective_result = weighted_objective(best)
            
            return {
                'best_params': best,
                'trials_completed': len(trials),
                'best_loss': final_objective_result.get('loss', float('inf')),
                'composite_metrics': final_objective_result.get('composite_metrics', {}),
                'weighted_objective_score': final_objective_result.get('weighted_objective', 0),
                'objectives_weights': objectives_weights,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Multi-objective optimization failed: {e}")
            return {'error': str(e)}

    def _get_simple_metrics(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, float]:
        """Calculate simple performance metrics for evaluation."""
        # This is a simplified metrics calculation for demonstration
        # In a real system, this would run the actual strategy backtest
        if len(df) < 2:
            return {
                'sharpe_ratio': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'win_rate': 0
            }
        
        # Calculate simple returns
        if 'close' in df.columns:
            returns = df['close'].pct_change().dropna()
            
            if len(returns) > 1:
                # Calculate basic metrics
                avg_return = returns.mean()
                std_return = returns.std()
                total_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1 if df['close'].iloc[0] != 0 else 0
                
                # Sharpe ratio (assuming risk-free rate of 0)
                sharpe_ratio = avg_return / std_return if std_return != 0 else 0
                
                # Drawdown calculation
                cumulative = (1 + returns).cumprod()
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = drawdown.min()
                
                # Win rate
                win_rate = (returns > 0).sum() / len(returns)
                
                return {
                    'sharpe_ratio': sharpe_ratio,
                    'total_return': total_return,
                    'max_drawdown': max_drawdown,
                    'win_rate': win_rate
                }
        
        # Default values if metrics can't be calculated
        return {
            'sharpe_ratio': 0,
            'total_return': 0,
            'max_drawdown': 0,
            'win_rate': 0
        }

    def optimize_with_early_stopping(self,
                                   data_dict: Dict[str, pd.DataFrame],
                                   param_space: Dict[str, Any],
                                   risk_config: Dict[str, Any],
                                   algorithm: str = 'tpe',
                                   max_evals: int = 100,
                                   early_stopping_rounds: int = 10,
                                   min_improvement: float = 0.0001) -> Dict[str, Any]:
        """
        Optimize with early stopping based on improvement plateau.
        
        Args:
            data_dict: Dictionary of asset data
            param_space: Parameter space for optimization
            risk_config: Risk configuration parameters
            algorithm: Algorithm to use for optimization
            max_evals: Maximum number of evaluations
            early_stopping_rounds: Number of rounds without improvement before stopping
            min_improvement: Minimum improvement to qualify as progress
        """
        # Create objective function
        optimization_objectives = ['sharpe_ratio']  # Default to sharpe ratio
        objective_fn = self.objective_handler.create_objective_function(
            data_dict, risk_config, optimization_objectives=optimization_objectives
        )
        
        # Custom optimization loop with early stopping
        trials = Trials()
        best_loss = float('inf')
        rounds_without_improvement = 0
        actual_evals = 0
        
        for i in range(max_evals):
            if rounds_without_improvement >= early_stopping_rounds:
                self.logger.info(f"Early stopping triggered after {actual_evals} evaluations")
                break
            
            # Use hyperopt's fmin for each step, but check for improvement
            try:
                # Get next parameter suggestion
                from hyperopt import base
                new_trials = Trials()
                
                # Run just one more evaluation
                best = fmin(
                    fn=objective_fn,
                    space=param_space,
                    algo=self.algorithms.get(algorithm, tpe.suggest),
                    max_evals=i+1,  # Incrementally increase
                    trials=trials if i > 0 else new_trials,
                    verbose=False
                )
                
                # Get the latest loss
                if len(trials.trials) > 0:
                    latest_loss = trials.trials[-1]['result'].get('loss', float('inf'))
                    
                    # Check for improvement
                    if best_loss - latest_loss > min_improvement:
                        best_loss = latest_loss
                        rounds_without_improvement = 0
                    else:
                        rounds_without_improvement += 1
                    
                    actual_evals += 1
                    
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                break
        
        # Return results
        if len(trials.trials) > 0:
            # Find the best trial
            valid_trials = [t for t in trials.trials if t['result'].get('status') == 'ok']
            if valid_trials:
                best_trial = min(valid_trials, key=lambda x: x['result'].get('loss', float('inf')))
                best_params = space_eval(param_space, best_trial['misc']['vals'])
                
                return {
                    'best_params': best_params,
                    'best_loss': best_trial['result'].get('loss', float('inf')),
                    'trials_completed': len(valid_trials),
                    'actual_evaluations': actual_evals,
                    'early_stopped': rounds_without_improvement >= early_stopping_rounds,
                    'algorithm_used': algorithm,
                    'timestamp': datetime.now().isoformat()
                }
        
        return {
            'error': 'No valid trials completed',
            'trials_completed': 0,
            'actual_evaluations': actual_evals,
            'timestamp': datetime.now().isoformat()
        }