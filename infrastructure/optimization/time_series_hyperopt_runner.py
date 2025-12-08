"""Enhanced hyperopt runner with time series splitting and best practices."""

import json
import pickle
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
from datetime import datetime

from sklearn.model_selection import TimeSeriesSplit
from hyperopt import fmin, tpe, Trials
from shared.logger import EnhancedLogger

from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
from infrastructure.optimization.hyperopt_objective import HyperoptObjective
from infrastructure.optimization.improved_hyperopt_service import ImprovedHyperoptService


class TimeSeriesHyperoptRunner:
    """Hyperopt runner with proper time series splitting to prevent look-ahead bias."""

    def __init__(self,
                 strategy_name: str,
                 base_dir: str = "data/ts_hyperopt_results"):
        self.strategy_name = strategy_name
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.logger = EnhancedLogger(f"TimeSeriesHyperoptRunner_{strategy_name}")

        # Initialize components
        self.param_space = HyperoptParameterSpace()
        self.objective_handler = HyperoptObjective()
        
        # Set seeds for reproducibility
        self._set_reproducible_seeds()

    def _set_reproducible_seeds(self, seed: int = 42):
        """Set all random seeds for reproducible results."""
        np.random.seed(seed)
        import random
        random.seed(seed)

    def prepare_time_series_data_splits(self,
                                      df: pd.DataFrame,
                                      n_splits: int = 5,
                                      min_train_size: int = 50,
                                      test_size: float = 0.2) -> List[Dict[str, Any]]:
        """
        Prepare time series splits to prevent data leakage.
        Each split contains train and validation data with no overlap.
        """
        if len(df) < min_train_size:
            raise ValueError(f"Insufficient data: need at least {min_train_size} rows, got {len(df)}")

        # Use TimeSeriesSplit for proper temporal cross-validation
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        splits = []
        for train_idx, val_idx in tscv.split(df):
            train_data = df.iloc[train_idx].copy()
            val_data = df.iloc[val_idx].copy()
            
            splits.append({
                "train": train_data,
                "validation": val_data,
                "train_size": len(train_data),
                "val_size": len(val_data)
            })
        
        self.logger.info(f"Created {len(splits)} time series splits")
        return splits

    def create_time_series_objective(self,
                                   data_splits: List[Dict[str, Any]],
                                   risk_config: Dict[str, Any],
                                   optimization_objective: str = 'sharpe_ratio',
                                   strategy_function=None) -> callable:
        """
        Create objective function that evaluates on time series validation splits.
        This prevents overfitting to the training data.
        """
        def ts_objective(params: Dict[str, Any]) -> Dict[str, Any]:
            """Objective function using time series validation."""
            try:
                validation_scores = []
                
                # Evaluate on each validation split
                for split_data in data_splits:
                    train_df = split_data["train"]
                    val_df = split_data["validation"]
                    
                    # Calculate metrics on validation data (not training!)
                    metrics = self.objective_handler._calculate_metrics_for_asset(
                        params, val_df, risk_config, strategy_function
                    )
                    
                    # Get the optimization objective value
                    score = metrics.get(optimization_objective, 0)
                    validation_scores.append(score)
                
                # Calculate average performance across splits
                avg_score = np.mean(validation_scores) if validation_scores else 0
                std_score = np.std(validation_scores) if validation_scores else 0
                
                # Apply penalty for high variance (sign of overfitting)
                penalty = std_score * 0.2  # Adjust penalty factor as needed
                final_score = avg_score - penalty
                
                # Hyperopt minimizes, so we return negative of our maximization objective
                loss = -final_score
                
                return {
                    "loss": loss,
                    "status": "ok",
                    "validation_avg_score": avg_score,
                    "validation_std_score": std_score,
                    "penalty": penalty,
                    "raw_validation_scores": validation_scores
                }
            
            except Exception as e:
                self.logger.error(f"Error in time series objective: {e}")
                return {
                    "loss": float("inf"),
                    "status": "error",
                    "error": str(e)
                }
        
        return ts_objective

    def run_optimization_with_cv(self,
                               data_dict: Dict[str, Any],
                               risk_config: Dict[str, Any],
                               max_evals: int = 50,
                               n_cv_splits: int = 3,
                               optimization_objective: str = 'sharpe_ratio',
                               algorithm: str = 'tpe') -> Dict[str, Any]:
        """
        Run optimization with time series cross-validation.
        """
        self.logger.info(f"Starting time series CV optimization for {self.strategy_name}")
        
        # Combine data from all symbols for multi-asset optimization
        all_splits = []
        for symbol, df in data_dict.items():
            try:
                splits = self.prepare_time_series_data_splits(df, n_cv_splits)
                # Add symbol info to each split
                for split in splits:
                    split["symbol"] = symbol
                all_splits.extend(splits)
            except ValueError as e:
                self.logger.warning(f"Skipping {symbol} due to: {e}")
        
        if not all_splits:
            raise ValueError("No valid data splits created for any asset")
        
        self.logger.info(f"Created {len(all_splits)} total splits across all assets")
        
        # Create objective function using validation splits
        objective_fn = self.create_time_series_objective(
            all_splits, risk_config, optimization_objective
        )
        
        # Get parameter space for strategy
        space = self.param_space.get_space(self.strategy_name)
        
        # Initialize trials
        trials = Trials()
        
        # Run optimization
        self.logger.info(f"Starting optimization with {max_evals} evaluations")
        best = fmin(
            fn=objective_fn,
            space=space,
            algo=tpe.suggest if algorithm == 'tpe' else algorithm,
            max_evals=max_evals,
            trials=trials
        )
        
        # Evaluate final metrics on best parameters
        final_result = objective_fn(best)
        
        # Create comprehensive results
        results = {
            "best_params": best,
            "best_loss": final_result.get("loss", float("inf")),
            "trials_completed": len(trials.trials),
            "optimization_objective": optimization_objective,
            "algorithm_used": algorithm,
            "final_objective_result": final_result,
            "total_splits_used": len(all_splits),
            "cv_splits": n_cv_splits,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save results with proper logging structure
        self._save_results_with_logging(results, data_dict.keys())
        
        self.logger.info(f"Optimization completed. Best loss: {results['best_loss']:.6f}")
        return results

    def _save_results_with_logging(self, results: Dict[str, Any], symbols: List[str]):
        """Save results following proper logging structure."""
        # Create directory structure for this run
        run_dir = self.base_dir / self.strategy_name / datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save best parameters
        with open(run_dir / "best.json", 'w') as f:
            json.dump(results["best_params"], f, indent=4, default=str)
        
        # Save trial results
        with open(run_dir / "trials.json", 'w') as f:
            # Save simplified trial data - in real implementation you might want to save more details
            trial_data = {
                "trials_completed": results["trials_completed"],
                "optimization_objective": results["optimization_objective"],
                "algorithm_used": results["algorithm_used"],
                "total_splits_used": results["total_splits_used"],
                "cv_splits": results["cv_splits"],
                "timestamp": results["timestamp"],
                "best_loss": results["best_loss"]
            }
            json.dump(trial_data, f, indent=4, default=str)
        
        # Save parameters used for reference
        with open(run_dir / "params_used.json", 'w') as f:
            json.dump({
                "strategy_name": self.strategy_name,
                "symbols": list(symbols),
                "optimization_objective": results["optimization_objective"],
                "algorithm_used": results["algorithm_used"],
                "n_cv_splits": results["cv_splits"]
            }, f, indent=4, default=str)
        
        self.logger.info(f"Results saved to {run_dir}")

    def run_single_asset_optimization(self,
                                    df: pd.DataFrame,
                                    symbol: str,
                                    risk_config: Dict[str, Any],
                                    max_evals: int = 20) -> Dict[str, Any]:
        """
        Run optimization for a single asset with train/validation split.
        """
        self.logger.info(f"Starting single asset optimization for {symbol}")
        
        # Split into train and validation (no shuffling!)
        split_idx = int(len(df) * 0.8)  # 80% train, 20% validation
        train_df = df.iloc[:split_idx].copy()
        val_df = df.iloc[split_idx:].copy()
        
        if len(train_df) < 20 or len(val_df) < 10:
            raise ValueError(f"Insufficient data for train ({len(train_df)}) or validation ({len(val_df)})")
        
        # Create objective function using validation data
        def single_asset_objective(params: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Calculate metrics on validation data (not training!)
                metrics = self.objective_handler._calculate_metrics_for_asset(
                    params, val_df, risk_config
                )
                
                # Optimize for sharpe ratio (higher is better)
                sharpe_ratio = metrics.get('sharpe_ratio', 0)
                
                # Apply penalties for poor metrics
                max_drawdown = metrics.get('max_drawdown', 0)
                win_rate = metrics.get('win_rate', 0)
                
                # Penalty for excessive drawdown
                drawdown_penalty = 0
                if max_drawdown < -0.15:  # More than 15% drawdown
                    drawdown_penalty = abs(max_drawdown) * 2
                
                # Penalty for poor win rate
                win_rate_penalty = 0
                if win_rate < 0.4:  # Less than 40% win rate
                    win_rate_penalty = (0.4 - win_rate) * 2
                
                # Adjust score with penalties
                adjusted_score = sharpe_ratio - drawdown_penalty - win_rate_penalty
                
                return {
                    "loss": -adjusted_score,  # Negative because hyperopt minimizes
                    "status": "ok",
                    "metrics": metrics,
                    "adjusted_score": adjusted_score,
                    "drawdown_penalty": drawdown_penalty,
                    "win_rate_penalty": win_rate_penalty
                }
            except Exception as e:
                self.logger.error(f"Error in single asset objective: {e}")
                return {
                    "loss": float("inf"),
                    "status": "error",
                    "error": str(e)
                }
        
        # Get parameter space for strategy
        space = self.param_space.get_space(self.strategy_name)
        
        # Initialize and run optimization
        trials = Trials()
        best = fmin(
            fn=single_asset_objective,
            space=space,
            algo=tpe.suggest,
            max_evals=max_evals,
            trials=trials
        )
        
        # Get final metrics
        final_result = single_asset_objective(best)
        
        results = {
            "best_params": best,
            "best_loss": final_result.get("loss", float("inf")),
            "trials_completed": len(trials.trials),
            "final_metrics": final_result.get("metrics", {}),
            "adjusted_score": final_result.get("adjusted_score", 0),
            "symbol": symbol,
            "train_size": len(train_df),
            "validation_size": len(val_df),
            "timestamp": datetime.now().isoformat()
        }
        
        # Create logging directory for single asset
        run_dir = self.base_dir / self.strategy_name / "single_asset" / symbol / datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save results
        with open(run_dir / "best.json", 'w') as f:
            json.dump(results["best_params"], f, indent=4, default=str)
        
        with open(run_dir / "metrics.json", 'w') as f:
            json.dump(results["final_metrics"], f, indent=4, default=str)
        
        self.logger.info(f"Single asset optimization completed for {symbol}")
        return results


def run_time_series_hyperopt_example():
    """Example of how to use the time series hyperopt runner."""
    # Create sample data
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
    prices = 100 + np.cumsum(np.random.randn(200) * 0.5)
    
    sample_df = pd.DataFrame({
        'open': prices + np.random.randn(200) * 0.1,
        'high': prices + abs(np.random.randn(200)) * 0.2,
        'low': prices - abs(np.random.randn(200)) * 0.2,
        'close': prices,
        'volume': np.abs(np.random.randn(200)) * 1000
    }, index=dates)
    
    data_dict = {"SAMPLE": sample_df}
    
    risk_config = {
        "initial_capital": 10000.0,
        "fee_rate": 0.001,
        "slippage_factor": 0.0005,
        "max_drawdown_threshold": -0.15
    }
    
    # Create and run optimization
    runner = TimeSeriesHyperoptRunner(
        strategy_name="crypto_breakout",
        base_dir="data/ts_hyperopt_results"
    )
    
    results = runner.run_optimization_with_cv(
        data_dict=data_dict,
        risk_config=risk_config,
        max_evals=10,  # Reduced for example
        n_cv_splits=3,  # Reduced for example
        optimization_objective='sharpe_ratio'
    )
    
    print(f"Optimization completed. Best parameters: {results['best_params']}")
    return results


if __name__ == "__main__":
    print("Running time series hyperopt example...")
    results = run_time_series_hyperopt_example()
    print("Example completed!")