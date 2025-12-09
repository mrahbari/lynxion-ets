"""Parallel hyperopt runner following hexagonal architecture."""

import pickle
import json
from pathlib import Path
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from hyperopt import fmin, tpe, Trials
from shared.logger import EnhancedLogger
from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
from infrastructure.optimization.hyperopt_objective import HyperoptObjective


class ParallelHyperoptRunner:
    """Parallel runner for hyperopt optimization following hexagonal architecture."""

    def __init__(self,
                 trials_file: str = "data/hyperopt_parallel_trials.pkl",
                 best_params_file: str = "data/best_params_parallel.json",
                 strategy_name: str = "crypto_breakout"):
        self.trials_file = Path(trials_file)
        self.best_params_file = Path(best_params_file)
        self.strategy_name = strategy_name
        self.logger = EnhancedLogger("ParallelHyperoptRunner")

        # Create directories if they don't exist
        self.trials_file.parent.mkdir(parents=True, exist_ok=True)
        self.best_params_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize parameter space and objective
        self.param_space = HyperoptParameterSpace()
        self.objective_handler = HyperoptObjective()

    def run_parallel_optimization(self,
                                 data_dict: Dict[str, Any],
                                 risk_config: Dict[str, Any],
                                 max_evals: int = 20,
                                 n_jobs: int = 4) -> Dict[str, Any]:
        """Run parallel hyperopt optimization."""
        self.logger.info(f"Starting parallel hyperopt optimization for strategy: {self.strategy_name}")

        # Load or create trials
        trials = self._load_trials()

        # Create objective function
        objective_fn = self.objective_handler.create_objective_function(data_dict, risk_config)

        # Get parameter space for strategy
        space = self.param_space.get_space(self.strategy_name)

        # Run parallel optimization
        try:
            best = self._parallel_optimization(
                objective_fn=objective_fn,
                space=space,
                trials=trials,
                max_evals=max_evals,
                n_jobs=n_jobs
            )

            # Save best parameters
            self._save_best_params(best)
            self._save_trials(trials)

            self.logger.info("Parallel hyperopt optimization completed successfully")
            return {"best_params": best, "trials_count": len(trials.trials)}

        except Exception as e:
            self.logger.error(f"Error during parallel hyperopt optimization: {e}")
            return {"error": str(e)}

    def _parallel_optimization(self, objective_fn, space, trials, max_evals, n_jobs):
        """Run parallel optimization using ThreadPoolExecutor."""
        futures = []
        results = []

        with ThreadPoolExecutor(max_workers=n_jobs) as executor:
            for _ in range(max_evals):
                # Submit a job to run a single optimization
                future = executor.submit(
                    fmin,
                    fn=objective_fn,
                    space=space,
                    algo=tpe.suggest,
                    max_evals=len(trials.trials) + 1,
                    trials=trials,
                    verbose=False
                )
                futures.append(future)

            for future in as_completed(futures):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    self.logger.error(f"Error in parallel optimization task: {e}")

        # Return the best result from all parallel runs
        if results:
            # For this implementation, we'll return the last result
            # In a more sophisticated implementation, you might want to compare all results
            return results[-1]

        return {}

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
    print("\n🚀 Initializing Parallel Hyperopt Runner...")

    # Create runner instance
    runner = ParallelHyperoptRunner(
        trials_file="data/hyperopt_parallel_trials.pkl",
        best_params_file="data/best_params_parallel.json",
        strategy_name="crypto_breakout"
    )

    print("📊 Loading sample data...")
    data_dict = generate_sample_data()

    risk_config = {
        "max_risk": 0.02,
        "atr_multiplier": 1.5,
        "use_dynamic_position": True
    }

    print("🔥 Running Parallel Hyperopt Optimization...")
    result = runner.run_parallel_optimization(
        data_dict=data_dict,
        risk_config=risk_config,
        max_evals=20,
        n_jobs=4
    )

    if "error" not in result:
        print("\n🏁 Parallel Hyperopt Finished.")
        print(f"📊 Trials completed: {result.get('trials_count', 'N/A')}")
        best_params = runner.get_best_params()
        print(f"🎯 Best Params: {best_params}")
        print("\n💾 Results saved successfully")
    else:
        print(f"\n❌ Error during optimization: {result['error']}")