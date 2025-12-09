"""Hyperopt adapter for use with Walk-Forward Optimization."""

from typing import Dict, Any, Callable
from hyperopt import fmin, tpe, Trials
from infrastructure.optimization.hyperopt_objective import HyperoptObjective
import pandas as pd


class HyperoptAdapter:
    """Adapter to connect hyperopt with walk-forward optimization."""
    
    def __init__(self, 
                 strategy_or_function: Any = None,
                 risk_config: Dict[str, Any] = None,
                 max_evals: int = 50):
        """
        Initialize the hyperopt adapter.
        
        Args:
            strategy_or_function: Strategy class or function to optimize
            risk_config: Risk configuration parameters
            max_evals: Maximum number of hyperopt evaluations
        """
        self.strategy_or_function = strategy_or_function
        self.risk_config = risk_config or {}
        self.max_evals = max_evals
        self.objective_handler = HyperoptObjective()
        
    def optimize(self, 
                 data: pd.DataFrame, 
                 parameter_space: Dict[str, Any],
                 optimization_objectives: list = None) -> Dict[str, Any]:
        """
        Optimize parameters using hyperopt on the given data.
        
        Args:
            data: DataFrame with OHLCV data for optimization
            parameter_space: Hyperopt parameter space
            optimization_objectives: List of objectives to optimize
            
        Returns:
            Dictionary of best parameters
        """
        # Create objective function for this specific dataset
        objective_fn = self.objective_handler.create_objective_function(
            {'data': data},  # Wrap in dict as expected by objective function
            self.risk_config,
            self.strategy_or_function,
            optimization_objectives or ['sharpe_ratio']
        )
        
        # Run optimization
        trials = Trials()
        
        try:
            best = fmin(
                fn=objective_fn,
                space=parameter_space,
                algo=tpe.suggest,
                max_evals=self.max_evals,
                trials=trials,
                verbose=False
            )
            
            # Convert numpy types to basic Python types for compatibility
            return self._convert_types(best)
        
        except Exception as e:
            print(f"Error during hyperopt optimization: {e}")
            return {}

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
    """Adapter for multi-asset hyperparameter optimization."""
    
    def __init__(self, 
                 strategy_or_function: Any = None,
                 risk_config: Dict[str, Any] = None,
                 max_evals: int = 50):
        """
        Initialize the multi-asset hyperopt adapter.
        
        Args:
            strategy_or_function: Strategy class or function to optimize
            risk_config: Risk configuration parameters
            max_evals: Maximum number of hyperopt evaluations per asset
        """
        self.strategy_or_function = strategy_or_function
        self.risk_config = risk_config or {}
        self.max_evals = max_evals
        
    def optimize(self, 
                 multi_asset_data: Dict[str, pd.DataFrame], 
                 parameter_space: Dict[str, Any],
                 optimization_objectives: list = None) -> Dict[str, Dict[str, Any]]:
        """
        Optimize parameters for multiple assets.
        
        Args:
            multi_asset_data: Dictionary mapping asset names to DataFrames
            parameter_space: Hyperopt parameter space
            optimization_objectives: List of objectives to optimize
            
        Returns:
            Dictionary mapping asset names to best parameters
        """
        results = {}
        
        for asset_name, df in multi_asset_data.items():
            print(f"Optimizing for asset: {asset_name}")
            
            adapter = HyperoptAdapter(
                strategy_or_function=self.strategy_or_function,
                risk_config=self.risk_config,
                max_evals=self.max_evals
            )
            
            best_params = adapter.optimize(df, parameter_space, optimization_objectives)
            results[asset_name] = best_params
            
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