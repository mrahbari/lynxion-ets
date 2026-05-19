"""
Enhanced configuration system for hexagonal architecture.

This module manages configuration settings with support for multiple environments,
validation, and integration with the dependency injection container.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from decimal import Decimal
import json
import decimal
from domain.value_objects import Percentage
from application.configs.configs import Configs


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class HexagonalConfig:
    """Main configuration class for hexagonal architecture"""

    # General settings
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    debug: bool = False
    api_timeout: int = 30
    max_workers: int = 10
    redis_url: str = "redis://localhost:6379/0"
    enable_metrics: bool = True

    # Risk settings
    max_portfolio_risk: Percentage = field(default_factory=lambda: Percentage(Decimal("0.02")))
    max_position_risk: Percentage = field(default_factory=lambda: Percentage(Decimal("0.01")))
    max_drawdown: Percentage = field(default_factory=lambda: Percentage(Decimal("0.15")))
    max_correlation: Percentage = field(default_factory=lambda: Percentage(Decimal("0.7")))
    max_leverage: float = 1.0
    max_daily_loss: Percentage = field(default_factory=lambda: Percentage(Decimal("0.05")))
    enable_kill_switch: bool = True

    # Trading settings
    target_volatility: Percentage = field(default_factory=lambda: Percentage(Decimal("0.15")))
    rebalance_frequency: str = "daily"
    position_sizing_method: str = "risk_parity"
    min_order_size: float = 0.001
    max_order_size: float = 100000
    enable_shorting: bool = True
    max_position_concentration: Percentage = field(default_factory=lambda: Percentage(Decimal("0.1")))

    # Backtesting settings
    initial_capital: float = 100000
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    benchmark_symbol: str = "SPY"

    # Watcher settings
    enabled_watchers: List[str] = field(default_factory=lambda: ["MarketPulse", "Volatility", "TrendMTF"])
    update_frequency: int = 1  # seconds
    lookback_period: int = 100
    signal_threshold: float = 0.3
    auto_enable_watchers: bool = True

    # Engine settings
    enabled_engines: List[str] = field(default_factory=lambda: ["Trend", "Volatility", "Liquidity"])
    confidence_threshold: float = 0.3
    signal_fusion_enabled: bool = True
    regime_detection_enabled: bool = True
    ml_weights_enabled: bool = True

    # Execution settings
    slippage_tolerance: float = 0.005
    order_timeout: int = 30
    retry_attempts: int = 3
    enable_twap: bool = True
    enable_vwap: bool = True
    smart_order_routing: bool = True
    min_order_quantity: float = 0.001
    prevent_same_direction_trade_per_symbol: bool = True

    # Broker settings
    enabled_brokers: List[str] = field(default_factory=lambda: ["BingX"])
    default_broker: str = "BingX"
    # Broker configuration per watcher - allows each watcher to specify which broker to use
    watcher_broker_config: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        # Load from the new centralized config system
        self.load_from_new_config_system()

    def load_from_new_config_system(self):
        """Load configuration from the new centralized config system"""
        try:
            from .config_adapter import load_config_from_new_system
            config_mapping = load_config_from_new_system()

            # Apply mapped configuration values
            self.environment = config_mapping['environment']
            self.log_level = config_mapping['log_level']
            self.debug = config_mapping['debug']
            self.api_timeout = config_mapping['api_timeout']
            self.max_workers = config_mapping['max_workers']
            self.redis_url = config_mapping['redis_url']
            self.enable_metrics = config_mapping['enable_metrics']

            # Risk settings
            self.max_portfolio_risk = config_mapping['max_portfolio_risk']
            self.max_position_risk = config_mapping['max_position_risk']
            self.max_drawdown = config_mapping['max_drawdown']
            self.max_correlation = config_mapping['max_correlation']
            self.max_leverage = config_mapping['max_leverage']
            self.max_daily_loss = config_mapping['max_daily_loss']
            self.enable_kill_switch = config_mapping['enable_kill_switch']

            # Trading settings
            self.target_volatility = config_mapping['target_volatility']
            self.rebalance_frequency = config_mapping['rebalance_frequency']
            self.position_sizing_method = config_mapping['position_sizing_method']
            self.min_order_size = config_mapping['min_order_size']
            self.max_order_size = config_mapping['max_order_size']
            self.enable_shorting = config_mapping['enable_shorting']
            self.max_position_concentration = config_mapping['max_position_concentration']

            # Backtesting settings
            self.initial_capital = config_mapping['initial_capital']
            self.commission_rate = config_mapping['commission_rate']
            self.slippage_rate = config_mapping['slippage_rate']
            self.start_date = config_mapping['start_date']
            self.end_date = config_mapping['end_date']
            self.benchmark_symbol = config_mapping['benchmark_symbol']

            # Watcher settings
            self.enabled_watchers = config_mapping['enabled_watchers']
            self.update_frequency = config_mapping['update_frequency']
            self.lookback_period = config_mapping['lookback_period']
            self.signal_threshold = config_mapping['signal_threshold']
            self.auto_enable_watchers = config_mapping['auto_enable_watchers']

            # Engine settings
            self.enabled_engines = config_mapping['enabled_engines']
            self.confidence_threshold = config_mapping['confidence_threshold']
            self.signal_fusion_enabled = config_mapping['signal_fusion_enabled']
            self.regime_detection_enabled = config_mapping['regime_detection_enabled']
            self.ml_weights_enabled = config_mapping['ml_weights_enabled']

            # Execution settings
            self.slippage_tolerance = config_mapping['slippage_tolerance']
            self.order_timeout = config_mapping['order_timeout']
            self.retry_attempts = config_mapping['retry_attempts']
            self.enable_twap = config_mapping['enable_twap']
            self.enable_vwap = config_mapping['enable_vwap']
            self.smart_order_routing = config_mapping['smart_order_routing']
            self.min_order_quantity = config_mapping['min_order_quantity']
            self.prevent_same_direction_trade_per_symbol = config_mapping['prevent_same_direction_trade_per_symbol']

            # Broker settings
            self.enabled_brokers = config_mapping['enabled_brokers']
            self.default_broker = config_mapping['default_broker']
            self.watcher_broker_config = config_mapping['watcher_broker_config']

        except ImportError:
            # Fallback to environment variables if new config system is not available
            print("Warning: New configuration system not available, falling back to environment variables")
            self.load_from_env()

    def load_from_env(self):
        """Load configuration from environment variables - DEPRECATED: Use new config system instead"""
        print("Warning: Loading from environment variables is deprecated. Use the new configuration system instead.")
        # General settings
        env_str = Configs.infrastructure.environment if Configs.infrastructure and Configs.infrastructure.environment else self.environment.value
        try:
            self.environment = Environment[env_str.upper()]
        except KeyError:
            # If the environment string doesn't match any enum, default to DEVELOPMENT
            self.environment = Environment.DEVELOPMENT
        self.log_level = Configs.monitoring.logging_level if Configs.monitoring and hasattr(Configs.monitoring, 'logging_level') else self.log_level
        self.debug = Configs.infrastructure.debug if Configs.infrastructure and hasattr(Configs.infrastructure, 'debug') else str(self.debug).lower() == "true"
        try:
            api_timeout_env = Configs.infrastructure.api_timeout if Configs.infrastructure and hasattr(Configs.infrastructure, 'api_timeout') else str(self.api_timeout)
            if str(api_timeout_env).lstrip('-').isdigit():
                self.api_timeout = int(api_timeout_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            max_workers_env = Configs.infrastructure.max_workers if Configs.infrastructure and hasattr(Configs.infrastructure, 'max_workers') else str(self.max_workers)
            if str(max_workers_env).lstrip('-').isdigit():
                self.max_workers = int(max_workers_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.redis_url = Configs.infrastructure.redis_url if Configs.infrastructure and hasattr(Configs.infrastructure, 'redis_url') else self.redis_url
        self.enable_metrics = Configs.monitoring.enable_metrics if Configs.monitoring and hasattr(Configs.monitoring, 'enable_metrics') else str(self.enable_metrics).lower() == "true"

        # Risk settings - need to extract the decimal value from Percentage
        max_portfolio_risk_env = Configs.risk.max_portfolio_risk if Configs.risk and hasattr(Configs.risk, 'max_portfolio_risk') else str(float(self.max_portfolio_risk.value))
        try:
            # Check if the environment variable is a valid number
            if str(max_portfolio_risk_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(max_portfolio_risk_env).startswith('-') and str(max_portfolio_risk_env)[1:].replace('.', '', 1).isdigit()):
                self.max_portfolio_risk = Percentage(Decimal(str(max_portfolio_risk_env)))
            else:
                # If it's not a valid number, keep the default value
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        max_position_risk_env = Configs.risk.max_position_risk if Configs.risk and hasattr(Configs.risk, 'max_position_risk') else str(float(self.max_position_risk.value))
        try:
            if str(max_position_risk_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(max_position_risk_env).startswith('-') and str(max_position_risk_env)[1:].replace('.', '', 1).isdigit()):
                self.max_position_risk = Percentage(Decimal(str(max_position_risk_env)))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        max_drawdown_env = Configs.risk.max_drawdown if Configs.risk and hasattr(Configs.risk, 'max_drawdown') else str(float(self.max_drawdown.value))
        try:
            if str(max_drawdown_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(max_drawdown_env).startswith('-') and str(max_drawdown_env)[1:].replace('.', '', 1).isdigit()):
                self.max_drawdown = Percentage(Decimal(str(max_drawdown_env)))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        max_correlation_env = Configs.risk.max_correlation if Configs.risk and hasattr(Configs.risk, 'max_correlation') else str(float(self.max_correlation.value))
        try:
            if str(max_correlation_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(max_correlation_env).startswith('-') and str(max_correlation_env)[1:].replace('.', '', 1).isdigit()):
                self.max_correlation = Percentage(Decimal(str(max_correlation_env)))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        try:
            max_leverage_env = Configs.risk.max_leverage if Configs.risk and hasattr(Configs.risk, 'max_leverage') else str(self.max_leverage)
            if str(max_leverage_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(max_leverage_env).startswith('-') and str(max_leverage_env)[1:].replace('.', '', 1).isdigit()):
                self.max_leverage = float(max_leverage_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        max_daily_loss_env = Configs.risk.max_daily_loss if Configs.risk and hasattr(Configs.risk, 'max_daily_loss') else str(float(self.max_daily_loss.value))
        try:
            if str(max_daily_loss_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(max_daily_loss_env).startswith('-') and str(max_daily_loss_env)[1:].replace('.', '', 1).isdigit()):
                self.max_daily_loss = Percentage(Decimal(str(max_daily_loss_env)))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        self.enable_kill_switch = Configs.safety.enable_kill_switch if Configs.safety and hasattr(Configs.safety, 'enable_kill_switch') else str(self.enable_kill_switch).lower() == "true"

        # Trading settings
        target_volatility_env = Configs.risk.target_volatility if Configs.risk and hasattr(Configs.risk, 'target_volatility') else str(float(self.target_volatility.value))
        try:
            if str(target_volatility_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(target_volatility_env).startswith('-') and str(target_volatility_env)[1:].replace('.', '', 1).isdigit()):
                self.target_volatility = Percentage(Decimal(str(target_volatility_env)))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        self.rebalance_frequency = Configs.portfolio.rebalance_frequency if Configs.portfolio and hasattr(Configs.portfolio, 'rebalance_frequency') else self.rebalance_frequency
        self.position_sizing_method = Configs.position_sizing.method if Configs.position_sizing and hasattr(Configs.position_sizing, 'method') else self.position_sizing_method
        try:
            min_order_size_env = Configs.execution.min_order_size if Configs.execution and hasattr(Configs.execution, 'min_order_size') else str(self.min_order_size)
            if str(min_order_size_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(min_order_size_env).startswith('-') and str(min_order_size_env)[1:].replace('.', '', 1).isdigit()):
                self.min_order_size = float(min_order_size_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            max_order_size_env = Configs.execution.max_order_size if Configs.execution and hasattr(Configs.execution, 'max_order_size') else str(self.max_order_size)
            if str(max_order_size_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(max_order_size_env).startswith('-') and str(max_order_size_env)[1:].replace('.', '', 1).isdigit()):
                self.max_order_size = float(max_order_size_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.enable_shorting = Configs.strategy.enable_shorting if Configs.strategy and hasattr(Configs.strategy, 'enable_shorting') else str(self.enable_shorting).lower() == "true"

        max_position_concentration_env = Configs.risk.max_position_concentration if Configs.risk and hasattr(Configs.risk, 'max_position_concentration') else str(float(self.max_position_concentration.value))
        try:
            if str(max_position_concentration_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(max_position_concentration_env).startswith('-') and str(max_position_concentration_env)[1:].replace('.', '', 1).isdigit()):
                self.max_position_concentration = Percentage(Decimal(str(max_position_concentration_env)))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        # Backtesting settings
        try:
            initial_capital_env = Configs.backtest.initial_capital if Configs.backtest and hasattr(Configs.backtest, 'initial_capital') else str(self.initial_capital)
            if str(initial_capital_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(initial_capital_env).startswith('-') and str(initial_capital_env)[1:].replace('.', '', 1).isdigit()):
                self.initial_capital = float(initial_capital_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            commission_rate_env = Configs.execution.commission_rate if Configs.execution and hasattr(Configs.execution, 'commission_rate') else str(self.commission_rate)
            if str(commission_rate_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(commission_rate_env).startswith('-') and str(commission_rate_env)[1:].replace('.', '', 1).isdigit()):
                self.commission_rate = float(commission_rate_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            slippage_rate_env = Configs.execution.slippage_rate if Configs.execution and hasattr(Configs.execution, 'slippage_rate') else str(self.slippage_rate)
            if str(slippage_rate_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(slippage_rate_env).startswith('-') and str(slippage_rate_env)[1:].replace('.', '', 1).isdigit()):
                self.slippage_rate = float(slippage_rate_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.start_date = Configs.backtest.start_date if Configs.backtest and hasattr(Configs.backtest, 'start_date') else self.start_date
        self.end_date = Configs.backtest.end_date if Configs.backtest and hasattr(Configs.backtest, 'end_date') else self.end_date
        self.benchmark_symbol = Configs.backtest.benchmark_symbol if Configs.backtest and hasattr(Configs.backtest, 'benchmark_symbol') else self.benchmark_symbol

        # Watcher settings
        self.enabled_watchers = Configs.watcher.enabled_watchers if Configs.watcher and hasattr(Configs.watcher, 'enabled_watchers') else self.enabled_watchers
        try:
            update_frequency_env = Configs.watcher.polling_interval_seconds if Configs.watcher and hasattr(Configs.watcher, 'polling_interval_seconds') else str(self.update_frequency)
            if str(update_frequency_env).lstrip('-').isdigit():
                self.update_frequency = int(update_frequency_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            lookback_period_env = Configs.watcher.lookback if Configs.watcher and hasattr(Configs.watcher, 'lookback') else str(self.lookback_period)
            if str(lookback_period_env).lstrip('-').isdigit():
                self.lookback_period = int(lookback_period_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            signal_threshold_env = Configs.watcher.signal_threshold if Configs.watcher and hasattr(Configs.watcher, 'signal_threshold') else str(self.signal_threshold)
            if str(signal_threshold_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(signal_threshold_env).startswith('-') and str(signal_threshold_env)[1:].replace('.', '', 1).isdigit()):
                self.signal_threshold = float(signal_threshold_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.auto_enable_watchers = Configs.watcher.auto_enable_watchers if Configs.watcher and hasattr(Configs.watcher, 'auto_enable_watchers') else str(self.auto_enable_watchers).lower() == "true"

        # Engine settings
        self.enabled_engines = Configs.strategy.enabled_engines if Configs.strategy and hasattr(Configs.strategy, 'enabled_engines') else self.enabled_engines
        try:
            confidence_threshold_env = Configs.strategy.engine_confidence_threshold if Configs.strategy and hasattr(Configs.strategy, 'engine_confidence_threshold') else str(self.confidence_threshold)
            if str(confidence_threshold_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(confidence_threshold_env).startswith('-') and str(confidence_threshold_env)[1:].replace('.', '', 1).isdigit()):
                self.confidence_threshold = float(confidence_threshold_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.signal_fusion_enabled = Configs.strategy.signal_fusion_enabled if Configs.strategy and hasattr(Configs.strategy, 'signal_fusion_enabled') else str(self.signal_fusion_enabled).lower() == "true"
        self.regime_detection_enabled = Configs.strategy.regime_detection_enabled if Configs.strategy and hasattr(Configs.strategy, 'regime_detection_enabled') else str(self.regime_detection_enabled).lower() == "true"
        self.ml_weights_enabled = Configs.strategy.ml_weights_enabled if Configs.strategy and hasattr(Configs.strategy, 'ml_weights_enabled') else str(self.ml_weights_enabled).lower() == "true"

        # Execution settings
        try:
            slippage_tolerance_env = Configs.execution.slippage_tolerance if Configs.execution and hasattr(Configs.execution, 'slippage_tolerance') else str(self.slippage_tolerance)
            if str(slippage_tolerance_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(slippage_tolerance_env).startswith('-') and str(slippage_tolerance_env)[1:].replace('.', '', 1).isdigit()):
                self.slippage_tolerance = float(slippage_tolerance_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            order_timeout_env = Configs.execution.order_timeout if Configs.execution and hasattr(Configs.execution, 'order_timeout') else str(self.order_timeout)
            if str(order_timeout_env).lstrip('-').isdigit():
                self.order_timeout = int(order_timeout_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            retry_attempts_env = Configs.execution.retry_attempts if Configs.execution and hasattr(Configs.execution, 'retry_attempts') else str(self.retry_attempts)
            if str(retry_attempts_env).lstrip('-').isdigit():
                self.retry_attempts = int(retry_attempts_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        self.enable_twap = Configs.execution.enable_twap if Configs.execution and hasattr(Configs.execution, 'enable_twap') else str(self.enable_twap).lower() == "true"
        self.enable_vwap = Configs.execution.enable_vwap if Configs.execution and hasattr(Configs.execution, 'enable_vwap') else str(self.enable_vwap).lower() == "true"
        self.smart_order_routing = Configs.execution.smart_order_routing if Configs.execution and hasattr(Configs.execution, 'smart_order_routing') else str(self.smart_order_routing).lower() == "true"

        try:
            min_order_quantity_env = Configs.execution.min_order_quantity if Configs.execution and hasattr(Configs.execution, 'min_order_quantity') else str(self.min_order_quantity)
            if str(min_order_quantity_env).replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (str(min_order_quantity_env).startswith('-') and str(min_order_quantity_env)[1:].replace('.', '', 1).isdigit()):
                self.min_order_quantity = float(min_order_quantity_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        self.prevent_same_direction_trade_per_symbol = Configs.execution.prevent_same_direction_trade_per_symbol if Configs.execution and hasattr(Configs.execution, 'prevent_same_direction_trade_per_symbol') else str(self.prevent_same_direction_trade_per_symbol).lower() == "true"

        # Broker settings
        self.enabled_brokers = Configs.broker.enabled_brokers if Configs.broker and hasattr(Configs.broker, 'enabled_brokers') else self.enabled_brokers
        self.default_broker = Configs.broker.default_broker if Configs.broker and hasattr(Configs.broker, 'default_broker') else self.default_broker

        # Parse watcher broker configuration from environment variable
        # Format: "MarketPulse:BingX,Volatility:Binance,TrendMTF:MEXC"
        watcher_broker_str = Configs.watcher.broker_config if Configs.watcher and hasattr(Configs.watcher, 'broker_config') else ""
        if watcher_broker_str:
            watcher_broker_pairs = watcher_broker_str.split(",")
            for pair in watcher_broker_pairs:
                if ":" in pair:
                    watcher_name, broker_name = pair.split(":", 1)
                    self.watcher_broker_config[watcher_name.strip()] = broker_name.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for easy access"""
        result = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if not attr_name.startswith('_') and not callable(attr):
                if hasattr(attr, 'to_dict'):  # For custom objects
                    result[attr_name] = attr.to_dict()
                elif isinstance(attr, Percentage):
                    result[attr_name] = float(attr)
                elif isinstance(attr, Enum):
                    result[attr_name] = attr.value
                else:
                    result[attr_name] = attr
        return result

    def get_broker_for_watcher(self, watcher_name: str) -> str:
        """Get the broker to use for a specific watcher, falling back to default if not specified"""
        return self.watcher_broker_config.get(watcher_name, self.default_broker)


# Global configuration instance
config = HexagonalConfig()