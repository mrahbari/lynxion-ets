"""Configurable Hyperopt system with parameter ranges, constraints, and optimization goals."""

import json
from typing import Dict, Any, List, Callable, Optional
from pathlib import Path
import pandas as pd

from shared.logger import EnhancedLogger


class HyperoptConfig:
    """
    Configuration class for hyperopt with flexible parameter ranges and constraints.
    Allows customization of optimization goals, parameter spaces, and constraints.
    """

    def __init__(self, config_file: str = None, strategy_name: str = "default"):
        self.logger = EnhancedLogger("HyperoptConfig")
        self.strategy_name = strategy_name

        # General configuration (no strategy-specific defaults)
        self.config = self._get_default_config()

        # Load custom config file if provided
        if config_file and Path(config_file).exists():
            self.load_config(config_file)

        # Validate and set defaults after loading
        self._validate_and_set_defaults()

    def _get_default_config(self):
        """Get default configuration for general strategies."""
        return {
            "optimization_objective": "sharpe_ratio",
            "max_evals": 100,
            "algorithm": "tpe",
            "timeout_minutes": 60,
            "early_stopping_rounds": 10,

            "parameter_ranges": {
                "rsi_length": {"type": "quniform", "min": 5, "max": 30, "step": 1},
                "rsi_overbought": {"type": "quniform", "min": 60, "max": 90, "step": 1},
                "rsi_oversold": {"type": "quniform", "min": 10, "max": 40, "step": 1},
                "ema_fast": {"type": "quniform", "min": 5, "max": 20, "step": 1},
                "ema_slow": {"type": "quniform", "min": 20, "max": 80, "step": 1},
                "atr_length": {"type": "quniform", "min": 7, "max": 40, "step": 1},
                "atr_multiplier": {"type": "uniform", "min": 1.0, "max": 5.0},
                "risk_per_trade": {"type": "uniform", "min": 0.005, "max": 0.03},
                "tp_ratio": {"type": "uniform", "min": 1.0, "max": 5.0},
                "sl_ratio": {"type": "uniform", "min": 0.5, "max": 3.0},
                "trailing_enabled": {"type": "choice", "options": [0, 1]},
                "trailing_atr_multiplier": {"type": "uniform", "min": 1.0, "max": 4.0},
            },

            "parameter_constraints": {
                "ema_slow_gt_ema_fast": {"condition": "ema_slow > ema_fast", "message": "EMA slow must be greater than EMA fast"},
                "atr_multiplier_range": {"condition": "1.0 <= atr_multiplier <= 5.0", "message": "ATR multiplier must be between 1.0 and 5.0"},
                "risk_per_trade_range": {"condition": "0.005 <= risk_per_trade <= 0.03", "message": "Risk per trade must be between 0.5% and 3%"},
            },

            "optimization_constraints": {
                "min_sharpe_ratio": 0.5,
                "max_drawdown": -0.20,
                "min_win_rate": 0.40,
                "max_trades_per_day": 10
            },

            "strategy_configs": {}  # Empty, strategies will provide their own configs via the interface
        }

    def _validate_and_set_defaults(self):
        """Validate configuration and set any missing default values."""
        # Ensure required keys exist
        defaults = {
            "optimization_objective": "sharpe_ratio",
            "max_evals": 100,
            "algorithm": "tpe",
            "timeout_minutes": 60,
            "early_stopping_rounds": 10
        }

        for key, default_value in defaults.items():
            if key not in self.config:
                self.config[key] = default_value
                self.logger.warning(f"Missing config key '{key}', using default value: {default_value}")

        # Validate optimization objective
        valid_objectives = ["sharpe_ratio", "profit_factor", "max_drawdown", "total_return", "win_rate"]
        if self.config.get("optimization_objective") not in valid_objectives:
            self.config["optimization_objective"] = "sharpe_ratio"
            self.logger.warning(f"Invalid optimization objective, using default: sharpe_ratio")

        # Validate algorithm
        valid_algorithms = ["tpe", "random", "anneal"]
        if self.config.get("algorithm") not in valid_algorithms:
            self.config["algorithm"] = "tpe"
            self.logger.warning(f"Invalid algorithm, using default: tpe")

        # Validate max_evals is positive
        max_evals = self.config.get("max_evals", 100)
        if not isinstance(max_evals, int) or max_evals <= 0:
            self.config["max_evals"] = 100
            self.logger.warning("max_evals must be a positive integer, using default: 100")

        # Validate parameter ranges
        for param_name, param_config in self.config.get("parameter_ranges", {}).items():
            if "type" not in param_config:
                self.logger.error(f"Parameter {param_name} missing 'type' in configuration")
                continue

            if param_config["type"] in ["quniform", "uniform"] and ("min" not in param_config or "max" not in param_config):
                self.logger.error(f"Parameter {param_name} missing min/max values for {param_config['type']} type")

            if param_config["type"] == "quniform" and "step" not in param_config:
                self.logger.warning(f"Parameter {param_name} missing step value for quniform, using default step of 1")
                param_config["step"] = 1

    def validate_config(self) -> Dict[str, List[str]]:
        """Validate the configuration and return any issues found."""
        issues = {
            "errors": [],
            "warnings": []
        }

        # Check required sections
        required_sections = ["parameter_ranges", "optimization_constraints"]
        for section in required_sections:
            if section not in self.config:
                issues["errors"].append(f"Missing required configuration section: {section}")

        # Validate parameter ranges
        for param_name, param_config in self.config.get("parameter_ranges", {}).items():
            if not isinstance(param_config, dict):
                issues["errors"].append(f"Parameter {param_name} configuration must be a dictionary")
                continue

            if "type" not in param_config:
                issues["errors"].append(f"Parameter {param_name} missing 'type' field")
                continue

            param_type = param_config["type"]
            if param_type in ["quniform", "uniform"]:
                for field in ["min", "max"]:
                    if field not in param_config:
                        issues["errors"].append(f"Parameter {param_name} missing '{field}' field")
                    elif not isinstance(param_config[field], (int, float)):
                        issues["errors"].append(f"Parameter {param_name} {field} must be numeric")

            if param_type == "quniform" and "step" not in param_config:
                issues["warnings"].append(f"Parameter {param_name} missing 'step' field for quniform type")

        # Check strategy-specific parameters
        strategy_config = self.config.get("strategy_configs", {}).get(self.strategy_name)
        if strategy_config:
            allowed_params = strategy_config.get("allowed_parameters", [])
            all_params = list(self.config.get("parameter_ranges", {}).keys())

            for param in allowed_params:
                if param not in all_params:
                    issues["warnings"].append(f"Allowed parameter {param} not defined in parameter_ranges")

        return issues
    
    def load_config(self, config_file: str):
        """Load configuration from file."""
        try:
            with open(config_file, 'r') as f:
                loaded_config = json.load(f)
            self.config.update(loaded_config)
            self.logger.info(f"Loaded hyperopt config from {config_file}")
        except Exception as e:
            self.logger.error(f"Error loading config from {config_file}: {e}")
    
    def save_config(self, config_file: str):
        """Save configuration to file."""
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info(f"Saved hyperopt config to {config_file}")
        except Exception as e:
            self.logger.error(f"Error saving config to {config_file}: {e}")
    
    def get_parameter_space(self, strategy_name: str = None) -> Dict[str, Any]:
        """Get parameter space for hyperopt - no strategy filtering, let strategies provide their own via interface."""
        # Return all available parameter ranges
        # Strategy-specific filtering will be handled by each strategy via the IOptimizableStrategy interface
        space = self.config["parameter_ranges"]

        self.logger.info(f"Returning parameter space with {len(space)} parameters for {strategy_name or 'all strategies'}")
        return space
    
    def get_optimization_config(self) -> Dict[str, Any]:
        """Get optimization-specific configuration."""
        return {
            "max_evals": self.config["max_evals"],
            "algorithm": self.config["algorithm"],
            "timeout_minutes": self.config["timeout_minutes"],
            "early_stopping_rounds": self.config["early_stopping_rounds"],
            "optimization_objective": self.config["optimization_objective"]
        }
    
    def get_optimization_constraints(self) -> Dict[str, Any]:
        """Get optimization constraints."""
        return self.config["optimization_constraints"]
    
    def update_parameter_range(self, param_name: str, range_config: Dict[str, Any]):
        """Update a single parameter range with validation."""
        # Validate the parameter range configuration
        if not isinstance(range_config, dict):
            self.logger.error(f"Parameter range for {param_name} must be a dictionary")
            return

        if "type" not in range_config:
            self.logger.error(f"Parameter range for {param_name} missing 'type' field")
            return

        param_type = range_config["type"]
        if param_type in ["quniform", "uniform"]:
            if "min" not in range_config or "max" not in range_config:
                self.logger.error(f"Parameter range for {param_name} missing min/max values for {param_type} type")
                return
            if range_config["min"] > range_config["max"]:
                self.logger.error(f"Parameter range for {param_name}: min ({range_config['min']}) > max ({range_config['max']})")
                return

        if param_type == "quniform" and "step" not in range_config:
            range_config["step"] = 1  # Add default step if not provided

        self.config["parameter_ranges"][param_name] = range_config
        self.logger.info(f"Updated parameter range for {param_name}: {range_config}")
    
    def update_optimization_goal(self, objective: str):
        """Update the optimization objective."""
        valid_objectives = ["sharpe_ratio", "profit_factor", "max_drawdown", "total_return", "win_rate"]
        if objective in valid_objectives:
            self.config["optimization_objective"] = objective
            self.logger.info(f"Updated optimization objective to {objective}")
        else:
            self.logger.error(f"Invalid objective {objective}. Valid options: {valid_objectives}")


class ConfigurableHyperoptOptimizer:
    """
    Hyperopt optimizer with configurable parameters, ranges, and constraints.
    """

    def __init__(self,
                 hyperopt_config: HyperoptConfig = None,
                 strategy_name: str = "default"):
        self.config = hyperopt_config or HyperoptConfig(strategy_name=strategy_name)
        self.logger = EnhancedLogger("ConfigurableHyperoptOptimizer")

        # Validate configuration
        issues = self.config.validate_config()
        if issues["errors"]:
            self.logger.error(f"Configuration validation errors: {issues['errors']}")
            raise ValueError(f"Invalid configuration: {issues['errors']}")

        if issues["warnings"]:
            self.logger.warning(f"Configuration validation warnings: {issues['warnings']}")

        # Track optimization history
        self.optimization_history = []
    
    def optimize_with_config(self, 
                           strategy_name: str,
                           data: pd.DataFrame, 
                           symbol: str,
                           custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run optimization with specific configuration.
        
        Args:
            strategy_name: Name of the strategy to optimize
            data: Historical market data
            symbol: Trading symbol
            custom_config: Custom configuration that overrides default settings
            
        Returns:
            Dictionary with optimization results
        """
        # Apply custom config if provided
        if custom_config:
            temp_config = HyperoptConfig()
            temp_config.config.update(self.config.config)
            temp_config.config.update(custom_config)
            config_to_use = temp_config
        else:
            config_to_use = self.config
        
        try:
            # Prepare parameter space based on strategy
            param_space = config_to_use.get_parameter_space(strategy_name)
            
            # Prepare optimization configuration
            opt_config = config_to_use.get_optimization_config()
            
            self.logger.info(f"Starting optimization for {strategy_name} on {symbol}")
            self.logger.info(f"Parameter space: {list(param_space.keys())}")
            self.logger.info(f"Optimization config: {opt_config}")
            
            # For now, return a mock result - in real implementation this would call hyperopt
            results = self._run_optimization(
                param_space=param_space,
                data=data,
                symbol=symbol,
                strategy_name=strategy_name,
                opt_config=opt_config
            )
            
            # Log successful optimization
            self.optimization_history.append({
                "timestamp": pd.Timestamp.now(),
                "strategy": strategy_name,
                "symbol": symbol,
                "objective": opt_config["optimization_objective"],
                "max_evals": opt_config["max_evals"],
                "results": results
            })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in optimization for {strategy_name} {symbol}: {e}")
            return {"error": str(e)}
    
    def _run_optimization(self,
                         param_space: Dict[str, Any],
                         data: pd.DataFrame,
                         symbol: str,
                         strategy_name: str,
                         opt_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the actual optimization (mock implementation).
        In a real system, this would interface with hyperopt.
        """
        # This is a mock implementation - in reality would call hyperopt with the config
        self.logger.info(f"Running mock optimization for {strategy_name} on {symbol}")
        
        # Generate mock results based on the parameter space
        mock_params = {}
        for param_name, param_config in param_space.items():
            if param_config["type"] == "quniform":
                mock_params[param_name] = (param_config["min"] + param_config["max"]) / 2
            elif param_config["type"] == "uniform":
                mock_params[param_name] = (param_config["min"] + param_config["max"]) / 2
            elif param_config["type"] == "choice":
                mock_params[param_name] = param_config["options"][0]
        
        # Mock optimization results
        results = {
            "best_params": mock_params,
            "best_value": -0.15,  # Negative because hyperopt minimizes
            "trials_completed": opt_config["max_evals"],
            "optimization_objective": opt_config["optimization_objective"],
            "parameter_space_used": list(param_space.keys()),
            "symbol": symbol,
            "strategy": strategy_name
        }
        
        self.logger.info(f"Mock optimization completed for {strategy_name} on {symbol}")
        return results
    
    def get_optimization_history(self, strategy_name: str = None, symbol: str = None) -> List[Dict[str, Any]]:
        """Get historical optimization results."""
        filtered_history = self.optimization_history
        
        if strategy_name:
            filtered_history = [item for item in filtered_history if item["strategy"] == strategy_name]
        
        if symbol:
            filtered_history = [item for item in filtered_history if item["symbol"] == symbol]
        
        return filtered_history


class HyperoptConfigManager:
    """
    Manager class to handle hyperopt configuration loading, saving, and validation.
    """
    
    def __init__(self):
        self.logger = EnhancedLogger("HyperoptConfigManager")
        self.default_configs_dir = Path("configs/hyperopt_configs")
        self.default_configs_dir.mkdir(parents=True, exist_ok=True)
    
    def create_strategy_config(self, strategy_name: str, parameters: List[str], 
                             constraints: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a configuration for a specific strategy."""
        config = {
            "parameters": parameters,
            "constraints": constraints or {},
            "default_ranges": self._get_default_ranges(parameters)
        }
        
        return config
    
    def _get_default_ranges(self, parameters: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get default ranges for specified parameters."""
        default_ranges = {}
        
        # Define default ranges for common parameters
        range_definitions = {
            "rsi_length": {"type": "quniform", "min": 5, "max": 30, "step": 1},
            "rsi_overbought": {"type": "quniform", "min": 60, "max": 90, "step": 1},
            "rsi_oversold": {"type": "quniform", "min": 10, "max": 40, "step": 1},
            "ema_fast": {"type": "quniform", "min": 5, "max": 20, "step": 1},
            "ema_slow": {"type": "quniform", "min": 20, "max": 80, "step": 1},
            "atr_length": {"type": "quniform", "min": 7, "max": 40, "step": 1},
            "atr_multiplier": {"type": "uniform", "min": 1.0, "max": 5.0},
            "risk_per_trade": {"type": "uniform", "min": 0.005, "max": 0.03},
            "tp_ratio": {"type": "uniform", "min": 1.0, "max": 5.0},
            "sl_ratio": {"type": "uniform", "min": 0.5, "max": 3.0},
            "trailing_enabled": {"type": "choice", "options": [0, 1]},
            "trailing_atr_multiplier": {"type": "uniform", "min": 1.0, "max": 4.0},
        }
        
        for param in parameters:
            if param in range_definitions:
                default_ranges[param] = range_definitions[param]
        
        return default_ranges
    
    def save_strategy_config(self, strategy_name: str, config: Dict[str, Any], 
                           filename: str = None) -> str:
        """Save strategy configuration to file."""
        if filename is None:
            filename = f"{strategy_name}_config.json"
        
        config_path = self.default_configs_dir / filename
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            self.logger.info(f"Saved strategy config for {strategy_name} to {config_path}")
            return str(config_path)
        except Exception as e:
            self.logger.error(f"Error saving strategy config: {e}")
            return ""
    
    def load_strategy_config(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load strategy configuration from file."""
        config_path = self.default_configs_dir / filename
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.logger.info(f"Loaded strategy config from {config_path}")
            return config
        except Exception as e:
            self.logger.error(f"Error loading strategy config {config_path}: {e}")
            return None