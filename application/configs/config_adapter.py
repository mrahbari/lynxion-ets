"""
Configuration adapter to transition from environment variables to the new config system.

This module provides a bridge between the old environment variable-based configuration
and the new centralized configuration system.
"""
from application.configs.configs import Configs
from domain.value_objects import Percentage
from decimal import Decimal
from typing import List, Optional, Dict


def load_config_from_new_system():
    """
    Load configuration from the new centralized config system.
    This function adapts the new config system to the existing HexagonalConfig structure.
    """
    # Ensure configs are loaded and validated
    Configs.validate_all()
    
    # Create a mapping from the new config system to the old structure
    config_mapping = {
        # General settings
        'environment': _map_environment(Configs.infrastructure.environment),
        'log_level': Configs.monitoring.logging_level,
        'debug': Configs.infrastructure.debug,
        'api_timeout': Configs.infrastructure.api_timeout,
        'max_workers': Configs.infrastructure.max_workers,
        'redis_url': Configs.infrastructure.redis_url,
        'enable_metrics': Configs.monitoring.enable_metrics,
        
        # Risk settings
        'max_portfolio_risk': Percentage(Decimal(str(Configs.risk.max_portfolio_risk))),
        'max_position_risk': Percentage(Decimal(str(Configs.risk.max_position_risk))),
        'max_drawdown': Percentage(Decimal(str(Configs.risk.max_drawdown))),
        'max_correlation': Percentage(Decimal(str(Configs.risk.max_correlation))),
        'max_leverage': Configs.risk.max_leverage,
        'max_daily_loss': Percentage(Decimal(str(Configs.risk.max_daily_loss))),
        'enable_kill_switch': Configs.safety.enable_kill_switch,
        
        # Trading settings
        'target_volatility': Percentage(Decimal(str(Configs.strategy.target_volatility))),
        'rebalance_frequency': Configs.portfolio.rebalance_frequency,
        'position_sizing_method': Configs.position_sizing.method,
        'min_order_size': Configs.risk.min_order_size,
        'max_order_size': Configs.risk.max_order_size,
        'enable_shorting': Configs.strategy.enable_shorting,
        'max_position_concentration': Percentage(Decimal(str(Configs.risk.max_position_concentration))),
        
        # Backtesting settings
        'initial_capital': Configs.backtest.initial_capital,
        'commission_rate': Configs.backtest.commission_rate,
        'slippage_rate': Configs.backtest.slippage_factor,
        'start_date': Configs.backtest.start_date,
        'end_date': Configs.backtest.end_date,
        'benchmark_symbol': Configs.backtest.benchmark_symbol,
        
        # Watcher settings
        'enabled_watchers': Configs.watcher.enabled_watchers,
        'update_frequency': Configs.watcher.update_freq,
        'lookback_period': Configs.watcher.lookback,
        'signal_threshold': Configs.strategy.signal_threshold,
        'auto_enable_watchers': Configs.watcher.auto_enable_watchers,
        
        # Engine settings
        'enabled_engines': Configs.strategy.enabled_engines,
        'confidence_threshold': Configs.strategy.engine_confidence_threshold,
        'signal_fusion_enabled': Configs.strategy.signal_fusion_enabled,
        'regime_detection_enabled': Configs.strategy.regime_detection_enabled,
        'ml_weights_enabled': Configs.strategy.ml_weights_enabled,
        
        # Execution settings
        'slippage_tolerance': Configs.execution.slippage_tolerance,
        'order_timeout': Configs.execution.order_timeout,
        'retry_attempts': Configs.infrastructure.max_workers,  # Using max_workers as retry_attempts
        'enable_twap': Configs.execution.enable_twap,
        'enable_vwap': Configs.execution.enable_vwap,
        'smart_order_routing': Configs.execution.smart_order_routing,
        'min_order_quantity': Configs.execution.min_order_quantity,
        'prevent_same_direction_trade_per_symbol': Configs.execution.prevent_same_direction_trade_per_symbol,
        
        # Broker settings
        'enabled_brokers': Configs.broker.enabled_brokers,
        'default_broker': Configs.broker.default_broker,
        'watcher_broker_config': _parse_watcher_broker_config(Configs.watcher.broker_config)
    }
    
    return config_mapping


def _map_environment(env_str: str) -> 'Environment':
    """Map environment string to Environment enum"""
    from enum import Enum
    
    class Environment(Enum):
        DEVELOPMENT = "development"
        STAGING = "staging"
        PRODUCTION = "production"
    
    env_lower = env_str.lower()
    if env_lower in ["development", "dev"]:
        return Environment.DEVELOPMENT
    elif env_lower in ["staging", "stage"]:
        return Environment.STAGING
    else:
        return Environment.PRODUCTION


def _parse_watcher_broker_config(broker_config_str: str) -> Dict[str, str]:
    """Parse the watcher broker configuration string into a dictionary"""
    result = {}
    if not broker_config_str:
        return result
    
    pairs = broker_config_str.split(",")
    for pair in pairs:
        if ":" in pair:
            watcher, broker = pair.split(":", 1)
            result[watcher.strip()] = broker.strip()
    
    return result