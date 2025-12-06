"""
Configuration management for the enterprise hedge fund trading system.
Provides centralized configuration with validation and reloading capabilities.
"""
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
from shared.logger import logger


@dataclass
class ConfigValue:
    """Represents a configuration value with metadata"""
    value: Any
    default: Any
    description: str = ""
    validator: Optional[callable] = None
    last_modified: datetime = field(default_factory=datetime.now)
    is_encrypted: bool = False


class ConfigManager:
    """Centralized configuration manager with validation and reloading"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.configs: Dict[str, ConfigValue] = {}
        self.config_file = config_file or "configs/app_config.json"
        self.load_config()
    
    def register_config(self, key: str, default_value: Any, description: str = "", 
                       validator: Optional[callable] = None) -> None:
        """Register a configuration parameter"""
        self.configs[key] = ConfigValue(
            value=default_value,
            default=default_value,
            description=description,
            validator=validator
        )
    
    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value with validation"""
        if key not in self.configs:
            logger.warning(f"Configuration key '{key}' not registered, creating with default validator")
            self.configs[key] = ConfigValue(
                value=value,
                default=value,
                description="Dynamically created config"
            )
        
        config_value = self.configs[key]
        
        # Validate the value if a validator is provided
        if config_value.validator:
            try:
                if not config_value.validator(value):
                    logger.error(f"Configuration validation failed for key '{key}' with value '{value}'")
                    return False
            except Exception as e:
                logger.error(f"Configuration validation error for key '{key}': {str(e)}")
                return False
        
        # Set the new value
        old_value = config_value.value
        config_value.value = value
        config_value.last_modified = datetime.now()
        
        logger.info(f"Configuration updated: {key} = {value} (was: {old_value})")
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        if key in self.configs:
            return self.configs[key].value
        elif default is not None:
            return default
        else:
            raise KeyError(f"Configuration key '{key}' not found")
    
    def get_with_metadata(self, key: str) -> Optional[ConfigValue]:
        """Get configuration value with metadata"""
        return self.configs.get(key)
    
    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            if not os.path.exists(self.config_file):
                logger.info(f"Configuration file {self.config_file} does not exist, using defaults")
                self._save_config_to_file()
                return True
            
            with open(self.config_file, 'r') as f:
                file_configs = json.load(f)
            
            # Update registered configs with file values
            for key, value in file_configs.items():
                if key in self.configs:
                    # Validate before setting
                    if self.configs[key].validator:
                        try:
                            if self.configs[key].validator(value):
                                self.configs[key].value = value
                            else:
                                logger.warning(f"Validation failed for config '{key}', using default: {self.configs[key].default}")
                        except Exception as e:
                            logger.error(f"Validation error for config '{key}': {str(e)}, using default")
                            self.configs[key].value = self.configs[key].default
                    else:
                        self.configs[key].value = value
                else:
                    # Add unregistered config as a new entry (but warn about it)
                    logger.warning(f"Unregistered config key found in file: {key}")
                    self.configs[key] = ConfigValue(value=value, default=value)
            
            logger.info(f"Configuration loaded from {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load configuration from {self.config_file}: {str(e)}")
            return False
    
    def save_config(self) -> bool:
        """Save current configuration to file"""
        return self._save_config_to_file()
    
    def _save_config_to_file(self) -> bool:
        """Internal method to save configuration to file"""
        try:
            # Create directory if it doesn't exist
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare config data (only save non-default values or all if preferred)
            config_data = {}
            for key, config_value in self.configs.items():
                config_data[key] = config_value.value
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration to {self.config_file}: {str(e)}")
            return False
    
    def reload_config(self) -> bool:
        """Reload configuration from file"""
        logger.info("Reloading configuration from file")
        return self.load_config()
    
    def reset_to_defaults(self) -> None:
        """Reset all configurations to their default values"""
        for key in self.configs:
            self.configs[key].value = self.configs[key].default
        logger.info("Configuration reset to defaults")
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return {key: config.value for key, config in self.configs.items()}
    
    def get_config_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all configurations"""
        return {
            key: {
                'value': config.value,
                'default': config.default,
                'description': config.description,
                'last_modified': config.last_modified.isoformat() if config.last_modified else None,
                'is_encrypted': config.is_encrypted
            }
            for key, config in self.configs.items()
        }


# Predefined validators
def validate_percentage(value: float) -> bool:
    """Validate that a value is between 0 and 1"""
    return 0 <= value <= 1

def validate_positive_number(value: Union[int, float]) -> bool:
    """Validate that a value is a positive number"""
    return value > 0

def validate_non_empty_string(value: str) -> bool:
    """Validate that a value is a non-empty string"""
    return isinstance(value, str) and len(value.strip()) > 0


# Global configuration manager instance
config_manager = ConfigManager()

# Register default configurations for the trading system
config_manager.register_config(
    "max_portfolio_risk", 
    0.01, 
    "Maximum risk per portfolio (1%)", 
    validate_percentage
)
config_manager.register_config(
    "max_position_risk", 
    0.005, 
    "Maximum risk per position (0.5%)", 
    validate_percentage
)
config_manager.register_config(
    "max_daily_loss", 
    0.02, 
    "Maximum daily loss (2%)", 
    validate_percentage
)
config_manager.register_config(
    "max_drawdown", 
    0.15, 
    "Maximum drawdown (15%)", 
    validate_percentage
)
config_manager.register_config(
    "commission_rate", 
    0.001, 
    "Commission rate per trade (0.1%)", 
    validate_percentage
)
config_manager.register_config(
    "slippage_tolerance", 
    0.001, 
    "Slippage tolerance (0.1%)", 
    validate_percentage
)
config_manager.register_config(
    "initial_capital", 
    100000.0, 
    "Initial capital for trading", 
    validate_positive_number
)