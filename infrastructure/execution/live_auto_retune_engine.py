"""Live auto-retune engine following hexagonal architecture."""

import time
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Callable

from hyperopt import fmin, tpe, Trials
from shared.logger import EnhancedLogger
from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
from infrastructure.optimization.hyperopt_objective import HyperoptObjective


from domain.ports.optimization_ports import IDataLoader
from domain.ports.execution_ports import ExecutionPort


class LiveAutoRetuneEngine:
    """Live auto-retune engine following hexagonal architecture."""

    def __init__(self,
                 data_loader: IDataLoader,
                 execution_service: ExecutionPort,
                 retune_interval_hours: int = 6,
                 evals_per_retune: int = 20,
                 performance_threshold: float = -5.0):
        self.data_loader = data_loader
        self.execution_service = execution_service
        self.retune_interval_hours = retune_interval_hours
        self.evals_per_retune = evals_per_retune
        self.performance_threshold = performance_threshold
        self.logger = EnhancedLogger("LiveAutoRetuneEngine")

        # Initialize hyperopt components
        self.param_space = HyperoptParameterSpace()
        self.objective_handler = HyperoptObjective()

        # File paths for persistence
        self.trials_file = Path("data/live_auto_trials.pkl")
        self.best_params_file = Path("data/best_params_live_auto.json")
        self.trials_file.parent.mkdir(parents=True, exist_ok=True)
        self.best_params_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize state
        self.last_retune = datetime.now() - timedelta(hours=retune_interval_hours)

    def run_live_auto_retune(self,
                           data_fetcher: Callable[[], Dict[str, Any]],
                           strategy_name: str = "crypto_breakout",
                           risk_config: Dict[str, Any] = None,
                           sleep_seconds: int = 60):
        """Main auto-retune loop with live execution capability."""
        if risk_config is None:
            risk_config = {
                "max_risk": 0.02,
                "atr_multiplier": 1.5,
                "use_dynamic_position": True
            }

        # Load or create trials
        trials = self._load_trials()

        # Main execution loop
        while True:
            try:
                # Fetch latest data
                data_dict = data_fetcher()
                if not data_dict:
                    self.logger.warning("No data fetched, waiting...")
                    time.sleep(sleep_seconds)
                    continue

                # Check if retune is needed
                if datetime.now() - self.last_retune >= timedelta(hours=self.retune_interval_hours):
                    self.logger.info(f"Running auto-retune at {datetime.now()}")
                    data_dict = self._perform_auto_retune(trials, data_dict, risk_config, strategy_name)

                # Execute live trading with current best parameters
                self._execute_live_trading(data_dict, strategy_name, risk_config)

                # Wait before next iteration
                time.sleep(sleep_seconds)

            except KeyboardInterrupt:
                self.logger.info("Live auto-retune stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in live auto-retune loop: {e}")
                time.sleep(sleep_seconds)  # Wait before continuing

    def _perform_auto_retune(self, trials: Trials, data_dict: Dict[str, Any],
                           risk_config: Dict[str, Any], strategy_name: str) -> Dict[str, Any]:
        """Perform auto retune optimization and return filtered data."""
        try:
            # Create objective function
            objective_fn = self.objective_handler.create_objective_function(data_dict, risk_config)

            # Get parameter space for strategy
            space = self.param_space.get_space(strategy_name)

            # Run optimization
            best = fmin(
                fn=objective_fn,
                space=space,
                algo=tpe.suggest,
                max_evals=len(trials.trials) + self.evals_per_retune,
                trials=trials,
                verbose=True
            )

            # Evaluate performance of each asset to identify poor performers
            performance_dict = {}
            for asset_name, df in data_dict.items():
                single_asset_data = {asset_name: df}
                asset_objective = self.objective_handler.create_objective_function(single_asset_data, risk_config)
                res = asset_objective(best)
                performance_dict[asset_name] = -res["loss"]  # Convert loss to performance

            # Remove poor performing assets
            filtered_data = self._drop_bad_assets(data_dict, performance_dict)

            # Save results
            self._save_best_params(best)
            self._save_trials(trials)

            self.last_retune = datetime.now()
            self.logger.info(f"Auto-retune completed. Assets remaining: {len(filtered_data)}")

            return filtered_data

        except Exception as e:
            self.logger.error(f"Error during auto-retune: {e}")
            return data_dict  # Return original data if retune fails

    def _execute_live_trading(self, data_dict: Dict[str, Any],
                             strategy_name: str, risk_config: Dict[str, Any]):
        """Execute live trading for all assets."""
        try:
            for asset_name, df in data_dict.items():
                # This would be where the actual trading logic happens
                # using the strategy name and risk config
                self.logger.debug(f"Executing live trading for {asset_name} with strategy {strategy_name}")

                # In a real implementation, the execution service would handle this
                # This is a placeholder for the actual trading execution
                pass

        except Exception as e:
            self.logger.error(f"Error executing live trading: {e}")

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

    def _load_trials(self) -> Trials:
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

    def _save_trials(self, trials: Trials):
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


# Backward compatibility function
def live_auto_retune(data_fetcher, strategy_class, retune_interval_hours=6, evals_per_retune=20):
    """
    Standalone function for backward compatibility.
    In hexagonal architecture, this would be called from an application service.
    """
    from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
    from infrastructure.optimization.hyperopt_objective import HyperoptObjective
    from domain.ports.optimization_ports import IDataLoader
    from domain.ports.execution_ports import IExecutionService

    # Create minimal implementations for standalone execution
    class MockDataLoader(IDataLoader):
        def load_historical_data(self, symbol: str, timeframe: str, limit: int):
            import pandas as pd
            return pd.DataFrame()

        def cache_exists(self, symbol: str, timeframe: str) -> bool:
            return False

    class MockExecutionService(IExecutionService):
        pass

    # Create engine instance
    engine = LiveAutoRetuneEngine(
        data_loader=MockDataLoader(),
        execution_service=MockExecutionService(),
        retune_interval_hours=retune_interval_hours,
        evals_per_retune=evals_per_retune
    )

    # Simple risk config
    risk_config = {
        "max_risk": 0.02,
        "atr_multiplier": 1.5,
        "use_dynamic_position": True
    }

    # Get strategy name (assuming it's based on class name)
    strategy_name = getattr(strategy_class, '__name__', 'unknown_strategy').replace('Strategy', '').replace('Class', '')

    # Run the live auto-retune
    engine.run_live_auto_retune(
        data_fetcher=data_fetcher,
        strategy_name=strategy_name.lower(),
        risk_config=risk_config
    )