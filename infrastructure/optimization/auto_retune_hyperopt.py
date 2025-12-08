"""Auto-retune hyperopt implementation following hexagonal architecture."""

import pickle
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from hyperopt import fmin, tpe, Trials
from shared.logger import EnhancedLogger
from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
from infrastructure.optimization.hyperopt_objective import HyperoptObjective


class AutoRetuneOptimizer:
    """Auto-retune optimizer following hexagonal architecture."""

    def __init__(self,
                 trials_file: str = "data/hyperopt_auto_trials.pkl",
                 best_params_file: str = "data/best_params_auto.json",
                 strategy_name: str = "crypto_breakout",
                 performance_threshold: float = -5.0):
        self.trials_file = Path(trials_file)
        self.best_params_file = Path(best_params_file)
        self.strategy_name = strategy_name
        self.performance_threshold = performance_threshold
        self.logger = EnhancedLogger("AutoRetuneOptimizer")

        # Create directories if they don't exist
        self.trials_file.parent.mkdir(parents=True, exist_ok=True)
        self.best_params_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize parameter space and objective
        self.param_space = HyperoptParameterSpace()
        self.objective_handler = HyperoptObjective()

    def run_auto_retune(self,
                       data_dict: Dict[str, Any],
                       risk_config: Dict[str, Any],
                       max_cycles: int = 3,
                       evals_per_cycle: int = 20) -> Dict[str, Any]:
        """Run auto-retune optimization cycle."""
        self.logger.info(f"Starting auto-retune optimization for strategy: {self.strategy_name}")

        # Load or create trials
        trials = self._load_trials()

        # Get parameter space for strategy
        space = self.param_space.get_space(self.strategy_name)

        # Run multiple optimization cycles
        current_data_dict = data_dict.copy()

        for cycle in range(max_cycles):
            self.logger.info(f"Starting auto-retune cycle {cycle+1}/{max_cycles}")

            if not current_data_dict:
                self.logger.warning("No assets left for optimization. Stopping auto-retune.")
                break

            # Create objective function for current data
            objective_fn = self.objective_handler.create_objective_function(current_data_dict, risk_config)

            try:
                # Run optimization for this cycle
                best = fmin(
                    fn=objective_fn,
                    space=space,
                    algo=tpe.suggest,
                    max_evals=len(trials.trials) + evals_per_cycle,
                    trials=trials,
                    verbose=True
                )

                # Evaluate performance of each asset
                performance_dict = self._evaluate_asset_performance(best, current_data_dict, risk_config)

                # Remove poor performing assets
                current_data_dict = self._drop_bad_assets(current_data_dict, performance_dict)

                self.logger.info(f"Cycle {cycle+1}/{max_cycles} completed. Assets remaining: {len(current_data_dict)}")

            except Exception as e:
                self.logger.error(f"Error in auto-retune cycle {cycle+1}: {e}")
                continue

        # Save final results
        if 'best' in locals():
            self._save_best_params(best)
            self._save_trials(trials)

        self.logger.info("Auto-retune optimization completed successfully")
        return {"best_params": best if 'best' in locals() else {}, "trials_count": len(trials.trials)}

    def _evaluate_asset_performance(self, params: Dict[str, Any], data_dict: Dict[str, Any], risk_config: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate performance of each asset with given parameters."""
        performance_dict = {}

        for asset_name, df in data_dict.items():
            # Create objective function for single asset
            single_asset_data = {asset_name: df}
            objective_fn = self.objective_handler.create_objective_function(single_asset_data, risk_config)

            # Get loss for this asset
            result = objective_fn(params)
            # Convert to performance score (higher is better)
            performance_dict[asset_name] = -result["loss"]  # Negative loss = positive performance

        return performance_dict

    def _drop_bad_assets(self, data_dict: Dict[str, Any], performance_dict: Dict[str, float]) -> Dict[str, Any]:
        """Drop assets with performance below threshold."""
        filtered_data = {}

        for asset, df in data_dict.items():
            performance = performance_dict.get(asset, 0)
            if performance > self.performance_threshold:
                filtered_data[asset] = df
            else:
                self.logger.info(f"Dropping {asset} due to poor performance: {performance:.2f}%")

        return filtered_data

    def _load_trials(self):
        """Load existing trials or create new ones."""
        try:
            with open(self.trials_file, "rb") as f:
                trials = pickle.load(f)
            self.logger.info("Loaded existing trials")
            return trials
        except FileNotFoundError:
            self.logger.info("Starting with fresh trials")
            return Trials()
        except Exception as e:
            self.logger.warning(f"Could not load trials: {e}, starting fresh")
            return Trials()

    def _save_trials(self, trials):
        """Save trials to file."""
        try:
            with open(self.trials_file, "wb") as f:
                pickle.dump(trials, f)
            self.logger.info(f"Trials saved to {self.trials_file}")
        except Exception as e:
            self.logger.error(f"Could not save trials: {e}")

    def _save_best_params(self, best_params: Dict[str, Any]):
        """Save best parameters to file."""
        try:
            with open(self.best_params_file, "w") as f:
                json.dump(best_params, f, indent=4, default=str)
            self.logger.info(f"Best parameters saved to {self.best_params_file}")
        except Exception as e:
            self.logger.error(f"Could not save best parameters: {e}")

    def get_best_params(self) -> Dict[str, Any]:
        """Load best parameters from file."""
        try:
            with open(self.best_params_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Best params file not found: {self.best_params_file}")
            return {}
        except Exception as e:
            self.logger.error(f"Could not load best parameters: {e}")
            return {}


class AutoRetuneScheduler:
    """Scheduler for auto-retune cycles."""

    def __init__(self, auto_retune_optimizer: AutoRetuneOptimizer, check_interval_hours: int = 24):
        self.auto_retune_optimizer = auto_retune_optimizer
        self.check_interval_hours = check_interval_hours
        self.logger = EnhancedLogger("AutoRetuneScheduler")
        self.last_run_time = None

    def should_run_retune(self) -> bool:
        """Check if auto-retune should be run based on time interval."""
        if self.last_run_time is None:
            return True

        time_since_last = datetime.now() - self.last_run_time
        return time_since_last.total_seconds() >= (self.check_interval_hours * 3600)

    def run_scheduled_retune(self, data_dict: Dict[str, Any], risk_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run scheduled auto-retune if needed."""
        if self.should_run_retune():
            self.logger.info("Starting scheduled auto-retune...")
            result = self.auto_retune_optimizer.run_auto_retune(
                data_dict=data_dict,
                risk_config=risk_config,
                max_cycles=2,
                evals_per_cycle=15
            )
            self.last_run_time = datetime.now()
            return result
        else:
            self.logger.info("Auto-retune not due yet, skipping...")
            return {"skipped": True, "reason": "not due yet"}


def generate_sample_data():
    """Generate sample data for testing."""
    import pandas as pd
    import numpy as np

    data_dict = {}

    # Creating sample data for gold
    timestamps = pd.date_range(start='2023-01-01', periods=1000, freq='H')
    prices = 2000 + np.cumsum(np.random.randn(1000) * 0.5)  # Simulated gold prices around $2000
    data_dict["XAUUSD"] = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices + np.random.randn(1000) * 0.1,
        'high': prices + abs(np.random.randn(1000)) * 0.2,
        'low': prices - abs(np.random.randn(1000)) * 0.2,
        'close': prices,
        'volume': np.abs(np.random.randn(1000)) * 1000,
        'volatility': np.abs(np.random.randn(1000)) * 2
    })

    # Creating sample data for BTC
    btc_prices = 30000 + np.cumsum(np.random.randn(1000) * 100)  # Simulated BTC prices
    data_dict["BTCUSD"] = pd.DataFrame({
        'timestamp': timestamps,
        'open': btc_prices + np.random.randn(1000) * 5,
        'high': btc_prices + abs(np.random.randn(1000)) * 10,
        'low': btc_prices - abs(np.random.randn(1000)) * 10,
        'close': btc_prices,
        'volume': np.abs(np.random.randn(1000)) * 500,
        'volatility': np.abs(np.random.randn(1000)) * 5
    })

    # Creating sample data for NASDAQ
    nasdaq_prices = 15000 + np.cumsum(np.random.randn(1000) * 5)  # Simulated NASDAQ prices
    data_dict["NAS100"] = pd.DataFrame({
        'timestamp': timestamps,
        'open': nasdaq_prices + np.random.randn(1000) * 2,
        'high': nasdaq_prices + abs(np.random.randn(1000)) * 4,
        'low': nasdaq_prices - abs(np.random.randn(1000)) * 4,
        'close': nasdaq_prices,
        'volume': np.abs(np.random.randn(1000)) * 800,
        'volatility': np.abs(np.random.randn(1000)) * 3
    })

    return data_dict


if __name__ == "__main__":
    # Example usage
    print("\n🚀 Initializing Auto-Retune Optimizer...")

    # Create optimizer instance
    optimizer = AutoRetuneOptimizer(
        trials_file="data/hyperopt_auto_trials.pkl",
        best_params_file="data/best_params_auto.json",
        strategy_name="crypto_breakout",
        performance_threshold=-5.0
    )

    print("📊 Loading sample data...")
    data_dict = generate_sample_data()

    risk_config = {
        "max_risk": 0.02,
        "atr_multiplier": 1.5,
        "use_dynamic_position": True
    }

    print("🔥 Running Auto-Retune Optimization...")
    result = optimizer.run_auto_retune(
        data_dict=data_dict,
        risk_config=risk_config,
        max_cycles=3,
        evals_per_cycle=20
    )

    if not result.get("skipped"):
        print("\n🏁 Auto-Retune Finished.")
        print(f"📊 Trials completed: {result.get('trials_count', 'N/A')}")
        best_params = optimizer.get_best_params()
        print(f"🎯 Best Params: {best_params}")
        print("\n💾 Results saved successfully")
    else:
        print(f"\n⚠️  Auto-Retune skipped: {result.get('reason', 'unknown reason')}")