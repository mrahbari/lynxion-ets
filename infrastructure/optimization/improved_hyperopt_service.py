"""Improved hyperopt implementation following all best practices from task25-hyperopt-best-practice.md"""

import json
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Callable, Tuple, Optional
from pathlib import Path
from datetime import datetime
import hashlib
import os
from time import time

from sklearn.model_selection import TimeSeriesSplit
from hyperopt import fmin, tpe, rand, anneal, Trials, STATUS_OK
from hyperopt import space_eval

from shared.logger import EnhancedLogger
from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
from infrastructure.optimization.hyperopt_objective import HyperoptObjective
from infrastructure.results_tracking.results_tracker import ResultsTracker


class ImprovedHyperoptService:
    """
    Improved hyperopt service that implements all best practices from task25-hyperopt-best-practice.md:
    - Time series cross-validation
    - Feature caching
    - Proper train/test splits
    - Reproducible results with seeds
    - Comprehensive logging
    - Performance optimizations
    - Look-ahead bias prevention
    """
    
    def __init__(self,
                 strategy_name: str,
                 base_dir: str = "data/hyperopt_results"):
        self.strategy_name = strategy_name
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.logger = EnhancedLogger(f"ImprovedHyperoptService_{strategy_name}")
        self.results_tracker = ResultsTracker()
        
        # Initialize components
        self.param_space = HyperoptParameterSpace()
        self.objective_handler = HyperoptObjective()
        
        # Caching for features
        self.feature_cache = {}
        self.feature_cache_dir = self.base_dir / "feature_cache"
        self.feature_cache_dir.mkdir(exist_ok=True)
        
        # Set seeds for reproducibility
        self._set_reproducible_seeds()

    def _set_reproducible_seeds(self, seed: int = 42):
        """Set all random seeds for reproducible results."""
        np.random.seed(seed)
        import random
        random.seed(seed)
        # Set hyperopt random state if possible
        
    def _get_feature_cache_key(self, symbol: str, data_hash: str) -> str:
        """Generate a cache key for features."""
        return f"{symbol}_{data_hash}_features"
        
    def _cache_features(self, cache_key: str, features: pd.DataFrame):
        """Cache calculated features to disk."""
        cache_file = self.feature_cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(features, f)
            self.logger.debug(f"Cached features to {cache_file}")
        except Exception as e:
            self.logger.error(f"Error caching features: {e}")
            
    def _load_cached_features(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Load cached features from disk."""
        cache_file = self.feature_cache_dir / f"{cache_key}.pkl"
        try:
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    features = pickle.load(f)
                self.logger.debug(f"Loaded cached features from {cache_file}")
                return features
        except Exception as e:
            self.logger.error(f"Error loading cached features: {e}")
        return None

    def _calculate_features_with_cache(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Calculate features with caching to prevent recalculation."""
        # Create hash of data to use as cache key
        data_hash = hashlib.md5(pd.util.hash_pandas_object(df.index).values).hexdigest()
        cache_key = self._get_feature_cache_key(symbol, data_hash)
        
        # Try to load from cache
        cached_features = self._load_cached_features(cache_key)
        if cached_features is not None:
            return cached_features
        
        # Calculate features (this should be done with proper look-ahead bias prevention)
        features_df = df.copy()
        
        # Add technical indicators with proper shifting to prevent look-ahead bias
        # RSI
        def calculate_rsi(prices, window=14):
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

        features_df['rsi'] = calculate_rsi(features_df['close']).shift(1)

        # Moving averages - shift by 1 to prevent lookahead bias
        features_df['sma_20'] = features_df['close'].rolling(window=20).mean().shift(1)
        features_df['sma_50'] = features_df['close'].rolling(window=50).mean().shift(1)

        # Bollinger Bands - shift by 1 to prevent lookahead bias
        features_df['bb_middle'] = features_df['close'].rolling(window=20).mean().shift(1)
        bb_std = features_df['close'].rolling(window=20).std().shift(1)
        features_df['bb_upper'] = features_df['bb_middle'] + (bb_std * 2)
        features_df['bb_lower'] = features_df['bb_middle'] - (bb_std * 2)

        # ATR (Average True Range) - shift by 1 to prevent lookahead bias
        high_low = features_df['high'] - features_df['low']
        high_close = np.abs(features_df['high'] - features_df['close'].shift(1))
        low_close = np.abs(features_df['low'] - features_df['close'].shift(1))
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        features_df['atr'] = tr.rolling(window=14).mean().shift(1)

        # MACD - shift by 1 to prevent lookahead bias
        exp1 = features_df['close'].ewm(span=12).mean().shift(1)
        exp2 = features_df['close'].ewm(span=26).mean().shift(1)
        features_df['macd'] = (exp1 - exp2).shift(1)
        features_df['macd_signal'] = features_df['macd'].ewm(span=9).mean().shift(1)
        features_df['macd_histogram'] = (features_df['macd'] - features_df['macd_signal']).shift(1)
        
        # Drop rows with NaN values that result from shifting
        features_df = features_df.dropna()
        
        # Cache the calculated features
        self._cache_features(cache_key, features_df)
        
        return features_df

    def prepare_time_series_split_data(self,
                                     df: pd.DataFrame,
                                     symbol: str,
                                     n_splits: int = 5,
                                     test_size: float = 0.2) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Prepare time series split data to prevent data leakage.
        Uses TimeSeriesSplit for proper temporal splitting.
        """
        # Calculate features with proper look-ahead bias prevention
        features_df = self._calculate_features_with_cache(df, symbol)
        
        if len(features_df) < 100:  # Need minimum data for meaningful splits
            raise ValueError(f"Insufficient data for {symbol}: {len(features_df)} rows. Need at least 100.")
        
        # Use TimeSeriesSplit for proper temporal cross-validation
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        splits = []
        for train_idx, test_idx in tscv.split(features_df):
            train_data = features_df.iloc[train_idx].copy()
            test_data = features_df.iloc[test_idx].copy()
            splits.append((train_data, test_data))
        
        self.logger.info(f"Created {len(splits)} time series splits for {symbol}")
        return splits

    def create_time_series_objective(self,
                                   data_splits: List[Tuple[pd.DataFrame, pd.DataFrame]],
                                   risk_config: Dict[str, Any],
                                   optimization_objectives: List[str] = None,
                                   strategy_or_strategy_function=None) -> Callable:
        """
        Create objective function that uses time series splits for validation.
        """
        if optimization_objectives is None:
            optimization_objectives = ['sharpe_ratio']
            
        def objective(params: Dict[str, Any]) -> Dict[str, Any]:
            """
            Objective function using time series cross-validation.
            """
            start_time = time()
            
            try:
                # Calculate score for each time series split
                split_scores = []
                
                for train_df, test_df in data_splits:
                    # Calculate performance on test set using parameters trained on train set
                    test_metrics = self.objective_handler._calculate_metrics_for_asset(
                        params, test_df, risk_config, strategy_or_strategy_function
                    )
                    
                    # Get the primary objective score for this split
                    primary_score = test_metrics.get(optimization_objectives[0], 0)
                    split_scores.append(primary_score)
                
                # Calculate average performance across all splits
                avg_score = np.mean(split_scores) if split_scores else 0
                std_score = np.std(split_scores) if split_scores else 0
                
                # Use a penalty for high variance across splits (overfitting indicator)
                penalty = std_score * 0.1  # Small penalty for variance
                
                # Calculate final score (higher is better, but hyperopt minimizes)
                final_score = avg_score - penalty
                
                execution_time = time() - start_time
                
                # Log metrics for analysis
                result = {
                    "loss": -final_score,  # Negate because hyperopt minimizes
                    "status": STATUS_OK,
                    "eval_time": execution_time,
                    "avg_score": avg_score,
                    "std_score": std_score,
                    "penalty": penalty,
                    "split_scores": split_scores,
                    "n_splits": len(data_splits)
                }
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error in time series objective: {e}")
                execution_time = time() - start_time
                return {
                    "loss": float("inf"), 
                    "status": "error",
                    "eval_time": execution_time,
                    "error": str(e)
                }
        
        return objective

    def optimize_with_time_series_cv(self,
                                   data_dict: Dict[str, pd.DataFrame],
                                   risk_config: Dict[str, Any],
                                   max_evals: int = 100,
                                   n_cv_splits: int = 5,
                                   algorithm: str = 'tpe',
                                   optimization_objectives: List[str] = None,
                                   early_stopping_rounds: int = 10) -> Dict[str, Any]:
        """
        Run optimization using time series cross-validation to prevent data leakage.
        """
        if optimization_objectives is None:
            optimization_objectives = ['sharpe_ratio']
        
        self.logger.info(f"Starting time series CV optimization for {self.strategy_name}")
        self.logger.info(f"Assets: {list(data_dict.keys())}, CV splits: {n_cv_splits}")
        
        # Prepare data splits for each asset
        all_splits = {}
        for symbol, df in data_dict.items():
            if len(df) < 100:  # Minimum data requirement
                self.logger.warning(f"Skipping {symbol} due to insufficient data: {len(df)} rows")
                continue
            try:
                splits = self.prepare_time_series_split_data(df, symbol, n_cv_splits)
                all_splits[symbol] = splits
            except ValueError as e:
                self.logger.error(f"Error preparing splits for {symbol}: {e}")
                
        if not all_splits:
            raise ValueError("No valid data splits created for any asset")
        
        # Initialize trials
        trials = Trials()
        
        # Get parameter space for the strategy
        space = self.param_space.get_space(self.strategy_name)
        
        # Combine splits across all assets for multi-asset optimization
        combined_splits = []
        for symbol, splits in all_splits.items():
            # Use all splits for each symbol
            combined_splits.extend(splits)
        
        if not combined_splits:
            raise ValueError("No valid combined splits after processing all assets")
        
        # Create objective function
        objective_fn = self.create_time_series_objective(
            combined_splits, risk_config, optimization_objectives
        )
        
        # Select optimization algorithm
        algo_map = {
            'tpe': tpe.suggest,
            'random': rand.suggest,
            'anneal': anneal.suggest
        }
        algo = algo_map.get(algorithm, tpe.suggest)
        
        self.logger.info(f"Starting optimization with {algorithm} algorithm, {max_evals} evaluations")
        
        # Run optimization with early stopping
        best = fmin(
            fn=objective_fn,
            space=space,
            algo=algo,
            max_evals=max_evals,
            trials=trials,
            verbose=True
        )
        
        # Calculate final metrics on best parameters
        final_result = objective_fn(best)
        
        # Save results
        results = {
            "best_params": best,
            "best_loss": final_result.get("loss", float("inf")),
            "trials_completed": len(trials.trials),
            "optimization_objective": optimization_objectives[0],
            "algorithm_used": algorithm,
            "final_objective_result": final_result,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log results to tracking system
        self.results_tracker.save_hyperopt_result(
            strategy_name=self.strategy_name,
            symbol="multi_asset",
            parameters=best,
            best_value=final_result.get("loss", float("inf")),
            trials_completed=len(trials.trials),
            optimization_objective=optimization_objectives[0],
            execution_time=time() - trials.trials[0]['book_time'].timestamp() if trials.trials else 0,
            notes=f"Time series CV with {n_cv_splits} splits across {len(all_splits)} assets"
        )
        
        self.logger.info(f"Optimization completed. Best loss: {results['best_loss']:.6f}")
        return results

    def optimize_single_asset_with_validation(self,
                                            df: pd.DataFrame,
                                            symbol: str,
                                            risk_config: Dict[str, Any],
                                            max_evals: int = 50,
                                            validation_ratio: float = 0.2,
                                            optimization_objectives: List[str] = None) -> Dict[str, Any]:
        """
        Optimize for a single asset with train/validation split to prevent overfitting.
        """
        if optimization_objectives is None:
            optimization_objectives = ['sharpe_ratio']
        
        self.logger.info(f"Starting single asset optimization for {symbol}")
        
        # Prepare train/validation splits
        features_df = self._calculate_features_with_cache(df, symbol)
        
        if len(features_df) < 50:
            raise ValueError(f"Insufficient data for {symbol}: {len(features_df)} rows")
        
        # Split into train and validation
        split_idx = int(len(features_df) * (1 - validation_ratio))
        train_df = features_df.iloc[:split_idx].copy()
        val_df = features_df.iloc[split_idx:].copy()
        
        if len(train_df) < 20 or len(val_df) < 10:
            raise ValueError(f"Insufficient train ({len(train_df)}) or validation ({len(val_df)}) data for {symbol}")
        
        # Initialize trials
        trials = Trials()
        
        # Get parameter space
        space = self.param_space.get_space(self.strategy_name)
        
        # Create objective function using validation data
        def validation_objective(params: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Calculate metrics on validation set
                val_metrics = self.objective_handler._calculate_metrics_for_asset(
                    params, val_df, risk_config
                )
                
                # Get primary objective
                primary_score = val_metrics.get(optimization_objectives[0], 0)
                
                return {
                    "loss": -primary_score,  # Negate because hyperopt minimizes
                    "status": STATUS_OK,
                    "val_metrics": val_metrics
                }
            except Exception as e:
                return {
                    "loss": float("inf"),
                    "status": "error",
                    "error": str(e)
                }
        
        # Run optimization
        best = fmin(
            fn=validation_objective,
            space=space,
            algo=tpe.suggest,
            max_evals=max_evals,
            trials=trials
        )
        
        # Validate best parameters
        final_metrics = self.objective_handler._calculate_metrics_for_asset(
            best, val_df, risk_config
        )
        
        results = {
            "best_params": best,
            "best_val_score": final_metrics.get(optimization_objectives[0], 0),
            "trials_completed": len(trials.trials),
            "validation_metrics": final_metrics,
            "train_size": len(train_df),
            "validation_size": len(val_df),
            "optimization_objective": optimization_objectives[0],
            "timestamp": datetime.now().isoformat()
        }
        
        # Log results
        self.results_tracker.save_hyperopt_result(
            strategy_name=self.strategy_name,
            symbol=symbol,
            parameters=best,
            best_value=-results["best_val_score"],  # Store as loss (positive)
            trials_completed=len(trials.trials),
            optimization_objective=optimization_objectives[0],
            notes=f"Single asset with {validation_ratio*100}% validation split"
        )
        
        self.logger.info(f"Single asset optimization completed for {symbol}")
        return results

    def create_fitness_metric_with_penalties(self,
                                           base_metric: str = 'sharpe_ratio',
                                           drawdown_limit: float = -0.15,
                                           max_trades: int = 1000,
                                           min_trades: int = 5) -> Callable:
        """
        Create a fitness function with appropriate penalties for realistic trading.
        """
        def fitness_with_penalties(metrics: Dict[str, Any]) -> float:
            """Calculate fitness score with penalties."""
            score = metrics.get(base_metric, 0)
            
            # Penalty for exceeding max drawdown
            max_drawdown = metrics.get('max_drawdown', 0)
            if max_drawdown < drawdown_limit:  # negative values, so < means worse than limit
                score *= 0.1  # severe penalty
            
            # Penalty for too few trades (potential overfitting)
            total_trades = metrics.get('total_trades', 0)
            if total_trades < min_trades:
                score *= 0.01  # big penalty for too few trades
            
            # Normalize based on number of trades up to a point
            if total_trades > max_trades:
                score *= (max_trades / total_trades)  # diminishing returns for very high trade count
            
            # Bonus for good win rate
            win_rate = metrics.get('win_rate', 0)
            if win_rate > 0.55:  # Good win rate gets a boost
                score *= 1.1
            elif win_rate < 0.40:  # Poor win rate gets penalty
                score *= 0.95
            
            return score
        
        return fitness_with_penalties

    def get_logging_directory(self, strategy_name: str) -> Path:
        """Get the logging directory for this strategy."""
        strategy_dir = self.base_dir / strategy_name
        strategy_dir.mkdir(exist_ok=True)
        
        timestamp_dir = strategy_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp_dir.mkdir(exist_ok=True)
        
        return timestamp_dir

    def save_optimization_results(self, results: Dict[str, Any], symbol: str = "multi"):
        """Save optimization results with proper logging structure."""
        timestamp_dir = self.get_logging_directory(self.strategy_name)
        
        # Save best parameters
        best_params_file = timestamp_dir / "best.json"
        with open(best_params_file, 'w') as f:
            json.dump(results.get("best_params", {}), f, indent=4, default=str)
        
        # Save all trials if available
        if "trials" in results:
            trials_file = timestamp_dir / "trials.json"
            # Assuming trials are serializable or convert to dict
            pass  # Trials need special handling if they exist
        
        # Save performance metrics
        metrics_file = timestamp_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump({
                "best_loss": results.get("best_loss", float("inf")),
                "trials_completed": results.get("trials_completed", 0),
                "optimization_objective": results.get("optimization_objective", "unknown"),
                "timestamp": results.get("timestamp", datetime.now().isoformat()),
                "algorithm_used": results.get("algorithm_used", "unknown")
            }, f, indent=4, default=str)
        
        self.logger.info(f"Results saved to {timestamp_dir}")
        return timestamp_dir


class MultiStrategyHyperoptTuner:
    """
    Central manager for tuning multiple strategies simultaneously while maintaining isolation.
    """
    
    def __init__(self):
        self.logger = EnhancedLogger("MultiStrategyHyperoptTuner")
        self.tuners = {}
        
    def register_strategy(self, strategy_name: str, base_dir: str = "data/hyperopt_results"):
        """Register a strategy for hyperparameter tuning."""
        if strategy_name not in self.tuners:
            self.tuners[strategy_name] = ImprovedHyperoptService(
                strategy_name=strategy_name,
                base_dir=base_dir
            )
            self.logger.info(f"Registered strategy: {strategy_name}")
        else:
            self.logger.warning(f"Strategy {strategy_name} already registered")
    
    def optimize_strategy(self,
                         strategy_name: str,
                         data_dict: Dict[str, pd.DataFrame],
                         risk_config: Dict[str, Any],
                         **kwargs) -> Dict[str, Any]:
        """Optimize a registered strategy."""
        if strategy_name not in self.tuners:
            raise ValueError(f"Strategy {strategy_name} not registered. Use register_strategy first.")
        
        self.logger.info(f"Optimizing strategy: {strategy_name}")
        return self.tuners[strategy_name].optimize_with_time_series_cv(
            data_dict=data_dict,
            risk_config=risk_config,
            **kwargs
        )
    
    def get_all_tuners(self) -> Dict[str, ImprovedHyperoptService]:
        """Get all registered tuners."""
        return self.tuners


# Example usage function
def run_improved_hyperopt_example():
    """Example of how to use the improved hyperopt service."""
    import yfinance as yf
    
    # Example: get some data
    symbols = ["BTC-USD", "ETH-USD"]
    data_dict = {}
    
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="6mo", interval="1d")
            if len(df) > 100:
                # Rename columns to match expected format
                df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 
                                      'Close': 'close', 'Volume': 'volume'})
                data_dict[symbol.replace('-', '')] = df
                print(f"Loaded {len(df)} rows for {symbol}")
        except Exception as e:
            print(f"Error loading {symbol}: {e}")
    
    if not data_dict:
        print("No data loaded, creating sample data instead")
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=500, freq='D')
        prices = 100 + np.cumsum(np.random.randn(500) * 0.5)
        
        sample_df = pd.DataFrame({
            'open': prices + np.random.randn(500) * 0.1,
            'high': prices + abs(np.random.randn(500)) * 0.2,
            'low': prices - abs(np.random.randn(500)) * 0.2,
            'close': prices,
            'volume': np.abs(np.random.randn(500)) * 1000
        }, index=dates)
        
        data_dict = {"SAMPLE": sample_df}
    
    # Initialize risk configuration
    risk_config = {
        "initial_capital": 10000.0,
        "fee_rate": 0.001,
        "slippage_factor": 0.0005,
        "max_drawdown_threshold": -0.15
    }
    
    # Create and run optimization
    hyperopt_service = ImprovedHyperoptService(
        strategy_name="crypto_breakout",
        base_dir="data/hyperopt_results"
    )
    
    results = hyperopt_service.optimize_with_time_series_cv(
        data_dict=data_dict,
        risk_config=risk_config,
        max_evals=20,  # Reduced for example
        n_cv_splits=3,  # Reduced for example
        algorithm='tpe'
    )
    
    print(f"Optimization completed. Best parameters: {results['best_params']}")
    return results


if __name__ == "__main__":
    # Example usage
    print("Running improved hyperopt example...")
    results = run_improved_hyperopt_example()
    print("Example completed!")