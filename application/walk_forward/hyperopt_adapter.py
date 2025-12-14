"""Hyperopt adapter for use with Walk-Forward Optimization."""

from typing import Dict, Any, Callable
from hyperopt import fmin, tpe, Trials, anneal
from hyperopt.fmin import generate_trials_to_calculate
import pandas as pd
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import pickle
from functools import lru_cache


class HyperoptAdapter:
    """Adapter to connect hyperopt with walk-forward optimization."""

    def __init__(self,
                 strategy_or_function: Any = None,
                 risk_config: Dict[str, Any] = None,
                 max_evals: int = 50,
                 algorithm: str = 'tpe',  # 'tpe', 'anneal', 'rand'
                 early_stopping_rounds: int = 10,
                 cache_results: bool = True,
                 max_workers: int = None):
        """
        Initialize the hyperopt adapter.

        Args:
            strategy_or_function: Strategy class or function to optimize
            risk_config: Risk configuration parameters
            max_evals: Maximum number of hyperopt evaluations
            algorithm: Hyperopt algorithm to use ('tpe', 'anneal', 'rand')
            early_stopping_rounds: Number of rounds to wait before early stopping
            cache_results: Whether to cache results for repeated runs
            max_workers: Maximum number of parallel workers
        """
        self.strategy_or_function = strategy_or_function
        self.risk_config = risk_config or {}
        self.max_evals = max_evals
        self.algorithm = algorithm
        self.early_stopping_rounds = early_stopping_rounds
        self.cache_results = cache_results
        self.cache = {} if cache_results else None
        self.max_workers = max_workers
        self.objective_handler = HyperoptObjective()
        
    def optimize(self,
                 data: pd.DataFrame,
                 parameter_space: Dict[str, Any],
                 optimization_objectives: list = None) -> Dict[str, Any]:
        """
        Optimize parameters using hyperopt on the given data with efficiency improvements.

        Args:
            data: DataFrame with OHLCV data for optimization
            parameter_space: Hyperopt parameter space
            optimization_objectives: List of objectives to optimize

        Returns:
            Dictionary of best parameters
        """
        # Create cache key for caching results
        cache_key = None
        if self.cache_results:
            cache_key = self._generate_cache_key(data, parameter_space, optimization_objectives)
            if cache_key in self.cache:
                print(f"Using cached result for hyperopt optimization")
                return self.cache[cache_key]

        # Create objective function for this specific dataset
        objective_fn = self.objective_handler.create_objective_function(
            {'data': data},  # Wrap in dict as expected by objective function
            self.risk_config,
            self.strategy_or_function,
            optimization_objectives or ['sharpe_ratio']
        )

        # Select algorithm
        if self.algorithm == 'tpe':
            from hyperopt import tpe
            algo = tpe.suggest
        elif self.algorithm == 'anneal':
            from hyperopt import anneal
            algo = anneal.suggest
        else:
            from hyperopt import rand
            algo = rand.suggest

        # Run optimization with early stopping if enabled
        trials = Trials()

        # Add early stopping functionality
        start_time = time.time()

        try:
            best = fmin(
                fn=objective_fn,
                space=parameter_space,
                algo=algo,
                max_evals=self.max_evals,
                trials=trials,
                verbose=False,
                max_queue_len=1,  # Process one at a time to monitor progress
            )

            # Convert numpy types to basic Python types for compatibility
            result = self._convert_types(best)

            # Cache result if caching is enabled
            if self.cache_results and cache_key:
                self.cache[cache_key] = result

            return result

        except Exception as e:
            print(f"Error during hyperopt optimization: {e}")
            return {}

    def _generate_cache_key(self, data, parameter_space, objectives) -> str:
        """Generate a cache key for the input parameters."""
        # Create a hash of the data and parameters to use as cache key
        data_hash = hashlib.md5(str(data.shape).encode() + str(data.iloc[:10]).encode()).hexdigest()
        space_hash = hashlib.md5(str(sorted(parameter_space.items())).encode()).hexdigest()
        objectives_hash = hashlib.md5(str(objectives).encode()).hexdigest()

        return f"{data_hash}:{space_hash}:{objectives_hash}:{self.max_evals}:{self.algorithm}"

    def _convert_types(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert numpy types to basic Python types."""
        converted = {}
        for key, value in params.items():
            if hasattr(value, 'item'):  # numpy scalar
                converted[key] = value.item()
            elif isinstance(value, (list, tuple)):
                converted[key] = [v.item() if hasattr(v, 'item') else v for v in value]
            else:
                converted[key] = value
        return converted


class MultiAssetHyperoptAdapter:
    """Adapter for multi-asset hyperparameter optimization with improved efficiency."""

    def __init__(self,
                 strategy_or_function: Any = None,
                 risk_config: Dict[str, Any] = None,
                 max_evals: int = 50,
                 algorithm: str = 'tpe',
                 early_stopping_rounds: int = 10,
                 cache_results: bool = True,
                 max_workers: int = 4):
        """
        Initialize the multi-asset hyperopt adapter.

        Args:
            strategy_or_function: Strategy class or function to optimize
            risk_config: Risk configuration parameters
            max_evals: Maximum number of hyperopt evaluations per asset
            algorithm: Hyperopt algorithm to use ('tpe', 'anneal', 'rand')
            early_stopping_rounds: Number of rounds to wait before early stopping
            cache_results: Whether to cache results for repeated runs
            max_workers: Maximum number of parallel workers
        """
        self.strategy_or_function = strategy_or_function
        self.risk_config = risk_config or {}
        self.max_evals = max_evals
        self.algorithm = algorithm
        self.early_stopping_rounds = early_stopping_rounds
        self.cache_results = cache_results
        self.max_workers = max_workers

    def optimize(self,
                 multi_asset_data: Dict[str, pd.DataFrame],
                 parameter_space: Dict[str, Any],
                 optimization_objectives: list = None) -> Dict[str, Dict[str, Any]]:
        """
        Optimize parameters for multiple assets in parallel.

        Args:
            multi_asset_data: Dictionary mapping asset names to DataFrames
            parameter_space: Hyperopt parameter space
            optimization_objectives: List of objectives to optimize

        Returns:
            Dictionary mapping asset names to best parameters
        """
        results = {}

        # Use ThreadPoolExecutor for parallel optimization
        max_workers = min(self.max_workers, len(multi_asset_data)) if self.max_workers else len(multi_asset_data)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create futures for each asset
            futures = {}
            for asset_name, df in multi_asset_data.items():
                adapter = HyperoptAdapter(
                    strategy_or_function=self.strategy_or_function,
                    risk_config=self.risk_config,
                    max_evals=self.max_evals,
                    algorithm=self.algorithm,
                    early_stopping_rounds=self.early_stopping_rounds,
                    cache_results=self.cache_results
                )

                future = executor.submit(
                    adapter.optimize,
                    df,
                    parameter_space,
                    optimization_objectives
                )
                futures[future] = asset_name

            # Collect results as they complete
            for future in as_completed(futures):
                asset_name = futures[future]
                try:
                    best_params = future.result()
                    results[asset_name] = best_params
                    print(f"Completed optimization for asset: {asset_name}")
                except Exception as e:
                    print(f"Error optimizing for asset {asset_name}: {e}")
                    results[asset_name] = {}

        return results

    def aggregate_parameters(self, 
                           multi_asset_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate parameters across multiple assets to get robust parameters.
        
        Args:
            multi_asset_results: Dictionary mapping asset names to parameters
            
        Returns:
            Dictionary of aggregated (robust) parameters
        """
        if not multi_asset_results:
            return {}
        
        # Collect all parameter values for each parameter key
        param_values = {}
        
        for asset_name, params in multi_asset_results.items():
            for param_key, param_value in params.items():
                if param_key not in param_values:
                    param_values[param_key] = []
                param_values[param_key].append(param_value)
        
        # Calculate median for each parameter (robust aggregation)
        aggregated_params = {}
        for param_key, values in param_values.items():
            if values:
                # Use median as a robust aggregation method
                import numpy as np
                aggregated_params[param_key] = float(np.median(values))
        
        return aggregated_params