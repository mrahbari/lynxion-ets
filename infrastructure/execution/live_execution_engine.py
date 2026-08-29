"""Live execution engine following hexagonal architecture."""

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


from typing import List
from domain.ports.execution_ports import ExecutionPort
from domain.ports.broker_ports import BrokerPort
from domain.ports.optimization_ports import IDataLoader
from domain.value_objects import Symbol
from domain.entities import Balance, Position


class LiveExecutionEngine:
    """Live execution engine following hexagonal architecture."""

    def __init__(self,
                 broker_service: BrokerPort,
                 data_loader: IDataLoader,
                 optimization_service: Any,  # We'll depend on the infrastructure optimization
                 execution_service: ExecutionPort,
                 retune_interval_hours: int = 6,
                 evals_per_retune: int = 20,
                 sleep_seconds: int = 60):
        self.broker_service = broker_service
        self.data_loader = data_loader
        self.optimization_service = optimization_service
        self.execution_service = execution_service
        self.retune_interval_hours = retune_interval_hours
        self.evals_per_retune = evals_per_retune
        self.sleep_seconds = sleep_seconds
        self.logger = EnhancedLogger("LiveExecutionEngine")

        # Initialize hyperopt components
        self.param_space = HyperoptParameterSpace()
        self.objective_handler = HyperoptObjective()

        # File paths for persistence
        self.trials_file = Path("data/live_trials.pkl")
        self.best_params_file = Path("data/best_params_live.json")
        self.trials_file.parent.mkdir(parents=True, exist_ok=True)
        self.best_params_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize state
        self.last_retune = datetime.now() - timedelta(hours=retune_interval_hours)

    def run_live_execution_with_auto_retune(self,
                                          data_fetcher: Callable[[], Dict[str, Any]],
                                          strategy_name: str = "crypto_breakout",
                                          risk_config: Dict[str, Any] = None):
        """Main execution loop with auto-retune capability."""
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
                    time.sleep(self.sleep_seconds)
                    continue

                # Check if retune is needed
                if datetime.now() - self.last_retune >= timedelta(hours=self.retune_interval_hours):
                    self.logger.info(f"Running auto-retune at {datetime.now()}")
                    self._perform_auto_retune(trials, data_dict, risk_config, strategy_name)

                # Execute trades based on current data and parameters
                self._execute_trades(data_dict, strategy_name, risk_config)

                # Wait before next iteration
                time.sleep(self.sleep_seconds)

            except KeyboardInterrupt:
                self.logger.info("Live execution stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in live execution loop: {e}")
                time.sleep(self.sleep_seconds)  # Wait before continuing

    def _perform_auto_retune(self, trials: Trials, data_dict: Dict[str, Any],
                           risk_config: Dict[str, Any], strategy_name: str):
        """Perform auto retune optimization."""
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

            # Save results
            self._save_best_params(best)
            self._save_trials(trials)

            self.last_retune = datetime.now()
            self.logger.info("Auto-retune completed and best params saved.")

        except Exception as e:
            self.logger.error(f"Error during auto-retune: {e}")

    def _execute_trades(self, data_dict: Dict[str, Any],
                       strategy_name: str, risk_config: Dict[str, Any]):
        """Execute trades for all assets."""
        try:
            for asset_name, df in data_dict.items():
                # Note: This is simplified. In a real implementation you'd have proper strategy execution
                # For now, this serves as a placeholder showing the architecture
                self.logger.debug(f"Processing trades for {asset_name}")

                # In a real implementation, you would:
                # 1. Use your strategy to generate signals
                # 2. Determine position sizes based on risk config
                # 3. Place orders through the broker service
                # 4. Track PnL, positions, etc.

        except Exception as e:
            self.logger.error(f"Error executing trades for {asset_name}: {e}")

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


class BrokerAPIService(BrokerPort):
    """Broker API service implementation following hexagonal architecture."""

    def __init__(self, api_config: Dict[str, Any] = None):
        self.api_config = api_config or {}
        self.logger = EnhancedLogger("BrokerAPIService")

    def connect(self):
        """Connect to the broker."""
        self.logger.info("Connecting to broker...")
        # Implementation would connect to broker API
        return True

    def disconnect(self):
        """Disconnect from the broker."""
        self.logger.info("Disconnecting from broker...")
        # Implementation would disconnect from broker API
        return True

    def place_order(self, order) -> str:
        """Place an order and return order ID under LiveExecutionGuard authorization."""
        from shared.live_execution_guard import live_execution_guard
        guard_decision, order_id = live_execution_guard.authorize_and_send(
            broker_name="live_engine", settings=None, order=order,
            send_fn=lambda: f"{getattr(order.symbol, 'value', str(order.symbol))}_{datetime.now().timestamp()}"
        )
        if not guard_decision.allowed or not order_id:
            self.logger.error(f"🛑 LIVE EXECUTION ENGINE BLOCKED: Order rejected by Risk Gate: {guard_decision.reason}")
            return ""

        self.logger.info(f"Placing order for {getattr(order.symbol, 'value', str(order.symbol))} | Side: {order.side} | Size: {order.quantity}")
        return order_id

    def cancel_order(self, order_id: str, symbol: Symbol) -> bool:
        """Cancel an order by ID."""
        self.logger.info(f"Cancelling order {order_id} for {symbol.value}")
        # Implementation would cancel order through broker API
        return True

    def get_order_status(self, order_id: str, symbol: Symbol) -> str:
        """Get the status of an order."""
        # For demonstration
        return "FILLED"

    def get_balance(self, asset: str = None) -> List[Balance]:
        """Get account balance."""
        # For demonstration - return mock balance
        return [Balance(asset="USD", total=10000, available=10000, reserved=0, timestamp=datetime.now())]

    def get_position(self, symbol: Symbol) -> Position:
        """Get position for a symbol."""
        # For demonstration - return mock position
        from domain.entities import PositionSide, Money
        position = Position(
            symbol=symbol,
            side=PositionSide.FLAT,
            quantity=0,
            entry_price=Money(0, "USD"),
            timestamp=datetime.now()
        )
        return position

    def get_all_positions(self) -> List[Position]:
        """Get all positions."""
        # For demonstration
        return []