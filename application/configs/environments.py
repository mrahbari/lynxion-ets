import os
from enum import Enum
from typing import Optional


class Environment(str, Enum):
    """Enumeration of supported environments"""
    DEV = "dev"
    STAGING = "staging"
    LIVE = "live"
    PRODUCTION = "production"
    BACKTEST = "backtest"
    OPTIMIZATION = "optimization"


def get_current_environment() -> Environment:
    """
    Determine the current environment based on environment variables.

    The environment is determined in the following priority order:
    1. LYNXION_ENV environment variable
    2. ENVIRONMENT environment variable
    3. Default to dev if none is set

    Returns:
        Current environment as an Environment enum value
    """
    # Check for LYNXION_ENV first (highest priority)
    env_value = os.getenv('LYNXION_ENV')
    if env_value:
        try:
            return Environment(env_value.lower())
        except ValueError:
            raise ValueError(f"Invalid environment value: {env_value}. "
                           f"Valid values are: {[e.value for e in Environment]}")

    # Check for ENVIRONMENT as backup
    env_value = os.getenv('ENVIRONMENT')
    if env_value:
        try:
            return Environment(env_value.lower())
        except ValueError:
            raise ValueError(f"Invalid environment value: {env_value}. "
                           f"Valid values are: {[e.value for e in Environment]}")

    # Default to dev environment
    return Environment.DEV


def is_live_environment() -> bool:
    """
    Check if the current environment is live trading.
    
    Returns:
        True if environment is live, False otherwise
    """
    return get_current_environment() == Environment.LIVE


def is_dev_environment() -> bool:
    """
    Check if the current environment is development.
    
    Returns:
        True if environment is dev, False otherwise
    """
    return get_current_environment() == Environment.DEV


def is_test_environment() -> bool:
    """
    Check if the current environment is a test environment (dev or staging).
    
    Returns:
        True if environment is dev or staging, False otherwise
    """
    current_env = get_current_environment()
    return current_env in [Environment.DEV, Environment.STAGING]


def is_backtest_environment() -> bool:
    """
    Check if the current environment is backtesting.
    
    Returns:
        True if environment is backtest, False otherwise
    """
    return get_current_environment() == Environment.BACKTEST


def is_optimization_environment() -> bool:
    """
    Check if the current environment is optimization.
    
    Returns:
        True if environment is optimization, False otherwise
    """
    return get_current_environment() == Environment.OPTIMIZATION