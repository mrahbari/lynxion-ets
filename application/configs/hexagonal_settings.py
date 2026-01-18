"""
Enhanced configuration system for hexagonal architecture.

This module manages configuration settings with support for multiple environments,
validation, and integration with the dependency injection container.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from decimal import Decimal
import json
import decimal
from domain.value_objects import Percentage


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
        # Load from environment variables if they exist
        self.load_from_env()
    
    def load_from_env(self):
        """Load configuration from environment variables"""
        # General settings
        env_str = os.getenv("ENVIRONMENT", self.environment.value).upper()
        try:
            self.environment = Environment[env_str]
        except KeyError:
            # If the environment string doesn't match any enum, default to DEVELOPMENT
            self.environment = Environment.DEVELOPMENT
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.debug = os.getenv("DEBUG", str(self.debug)).lower() == "true"
        try:
            api_timeout_env = os.getenv("API_TIMEOUT", str(self.api_timeout))
            if api_timeout_env.lstrip('-').isdigit():
                self.api_timeout = int(api_timeout_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            max_workers_env = os.getenv("MAX_WORKERS", str(self.max_workers))
            if max_workers_env.lstrip('-').isdigit():
                self.max_workers = int(max_workers_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.redis_url = os.getenv("REDIS_URL", self.redis_url)
        self.enable_metrics = os.getenv("ENABLE_METRICS", str(self.enable_metrics)).lower() == "true"
        
        # Risk settings - need to extract the decimal value from Percentage
        max_portfolio_risk_env = os.getenv("MAX_PORTFOLIO_RISK", str(float(self.max_portfolio_risk.value)))
        try:
            # Check if the environment variable is a valid number
            if max_portfolio_risk_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (max_portfolio_risk_env.startswith('-') and max_portfolio_risk_env[1:].replace('.', '', 1).isdigit()):
                self.max_portfolio_risk = Percentage(Decimal(max_portfolio_risk_env))
            else:
                # If it's not a valid number, keep the default value
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        max_position_risk_env = os.getenv("MAX_POSITION_RISK", str(float(self.max_position_risk.value)))
        try:
            if max_position_risk_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (max_position_risk_env.startswith('-') and max_position_risk_env[1:].replace('.', '', 1).isdigit()):
                self.max_position_risk = Percentage(Decimal(max_position_risk_env))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        max_drawdown_env = os.getenv("MAX_DRAWDOWN", str(float(self.max_drawdown.value)))
        try:
            if max_drawdown_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (max_drawdown_env.startswith('-') and max_drawdown_env[1:].replace('.', '', 1).isdigit()):
                self.max_drawdown = Percentage(Decimal(max_drawdown_env))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        max_correlation_env = os.getenv("MAX_CORRELATION", str(float(self.max_correlation.value)))
        try:
            if max_correlation_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (max_correlation_env.startswith('-') and max_correlation_env[1:].replace('.', '', 1).isdigit()):
                self.max_correlation = Percentage(Decimal(max_correlation_env))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        try:
            max_leverage_env = os.getenv("MAX_LEVERAGE", str(self.max_leverage))
            if max_leverage_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (max_leverage_env.startswith('-') and max_leverage_env[1:].replace('.', '', 1).isdigit()):
                self.max_leverage = float(max_leverage_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        max_daily_loss_env = os.getenv("MAX_DAILY_LOSS", str(float(self.max_daily_loss.value)))
        try:
            if max_daily_loss_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (max_daily_loss_env.startswith('-') and max_daily_loss_env[1:].replace('.', '', 1).isdigit()):
                self.max_daily_loss = Percentage(Decimal(max_daily_loss_env))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        self.enable_kill_switch = os.getenv("ENABLE_KILL_SWITCH", str(self.enable_kill_switch)).lower() == "true"

        # Trading settings
        target_volatility_env = os.getenv("TARGET_VOLATILITY", str(float(self.target_volatility.value)))
        try:
            if target_volatility_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (target_volatility_env.startswith('-') and target_volatility_env[1:].replace('.', '', 1).isdigit()):
                self.target_volatility = Percentage(Decimal(target_volatility_env))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        self.rebalance_frequency = os.getenv("REBALANCE_FREQUENCY", self.rebalance_frequency)
        self.position_sizing_method = os.getenv("POSITION_SIZING_METHOD", self.position_sizing_method)
        try:
            min_order_size_env = os.getenv("MIN_ORDER_SIZE", str(self.min_order_size))
            if min_order_size_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (min_order_size_env.startswith('-') and min_order_size_env[1:].replace('.', '', 1).isdigit()):
                self.min_order_size = float(min_order_size_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            max_order_size_env = os.getenv("MAX_ORDER_SIZE", str(self.max_order_size))
            if max_order_size_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (max_order_size_env.startswith('-') and max_order_size_env[1:].replace('.', '', 1).isdigit()):
                self.max_order_size = float(max_order_size_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.enable_shorting = os.getenv("ENABLE_SHORTING", str(self.enable_shorting)).lower() == "true"

        max_position_concentration_env = os.getenv("MAX_POSITION_CONCENTRATION", str(float(self.max_position_concentration.value)))
        try:
            if max_position_concentration_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (max_position_concentration_env.startswith('-') and max_position_concentration_env[1:].replace('.', '', 1).isdigit()):
                self.max_position_concentration = Percentage(Decimal(max_position_concentration_env))
            else:
                pass  # Keep default value
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass  # Keep default value

        # Backtesting settings
        try:
            initial_capital_env = os.getenv("INITIAL_CAPITAL", str(self.initial_capital))
            if initial_capital_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (initial_capital_env.startswith('-') and initial_capital_env[1:].replace('.', '', 1).isdigit()):
                self.initial_capital = float(initial_capital_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            commission_rate_env = os.getenv("COMMISSION_RATE", str(self.commission_rate))
            if commission_rate_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (commission_rate_env.startswith('-') and commission_rate_env[1:].replace('.', '', 1).isdigit()):
                self.commission_rate = float(commission_rate_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            slippage_rate_env = os.getenv("SLIPPAGE_RATE", str(self.slippage_rate))
            if slippage_rate_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (slippage_rate_env.startswith('-') and slippage_rate_env[1:].replace('.', '', 1).isdigit()):
                self.slippage_rate = float(slippage_rate_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.start_date = os.getenv("BACKTEST_START_DATE", self.start_date)
        self.end_date = os.getenv("BACKTEST_END_DATE", self.end_date)
        self.benchmark_symbol = os.getenv("BENCHMARK_SYMBOL", self.benchmark_symbol)

        # Watcher settings
        self.enabled_watchers = os.getenv("ENABLED_WATCHERS", ",".join(self.enabled_watchers)).split(",")
        try:
            update_frequency_env = os.getenv("WATCHER_UPDATE_FREQ", str(self.update_frequency))
            if update_frequency_env.lstrip('-').isdigit():
                self.update_frequency = int(update_frequency_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            lookback_period_env = os.getenv("WATCHER_LOOKBACK", str(self.lookback_period))
            if lookback_period_env.lstrip('-').isdigit():
                self.lookback_period = int(lookback_period_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            signal_threshold_env = os.getenv("SIGNAL_THRESHOLD", str(self.signal_threshold))
            if signal_threshold_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (signal_threshold_env.startswith('-') and signal_threshold_env[1:].replace('.', '', 1).isdigit()):
                self.signal_threshold = float(signal_threshold_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.auto_enable_watchers = os.getenv("AUTO_ENABLE_WATCHERS", str(self.auto_enable_watchers)).lower() == "true"

        # Engine settings
        self.enabled_engines = os.getenv("ENABLED_ENGINES", ",".join(self.enabled_engines)).split(",")
        try:
            confidence_threshold_env = os.getenv("ENGINE_CONFIDENCE_THRESHOLD", str(self.confidence_threshold))
            if confidence_threshold_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (confidence_threshold_env.startswith('-') and confidence_threshold_env[1:].replace('.', '', 1).isdigit()):
                self.confidence_threshold = float(confidence_threshold_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value
        self.signal_fusion_enabled = os.getenv("SIGNAL_FUSION_ENABLED", str(self.signal_fusion_enabled)).lower() == "true"
        self.regime_detection_enabled = os.getenv("REGIME_DETECTION_ENABLED", str(self.regime_detection_enabled)).lower() == "true"
        self.ml_weights_enabled = os.getenv("ML_WEIGHTS_ENABLED", str(self.ml_weights_enabled)).lower() == "true"

        # Execution settings
        try:
            slippage_tolerance_env = os.getenv("SLIPPAGE_TOLERANCE", str(self.slippage_tolerance))
            if slippage_tolerance_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (slippage_tolerance_env.startswith('-') and slippage_tolerance_env[1:].replace('.', '', 1).isdigit()):
                self.slippage_tolerance = float(slippage_tolerance_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            order_timeout_env = os.getenv("ORDER_TIMEOUT", str(self.order_timeout))
            if order_timeout_env.lstrip('-').isdigit():
                self.order_timeout = int(order_timeout_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        try:
            retry_attempts_env = os.getenv("RETRY_ATTEMPTS", str(self.retry_attempts))
            if retry_attempts_env.lstrip('-').isdigit():
                self.retry_attempts = int(retry_attempts_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        self.enable_twap = os.getenv("ENABLE_TWAP", str(self.enable_twap)).lower() == "true"
        self.enable_vwap = os.getenv("ENABLE_VWAP", str(self.enable_vwap)).lower() == "true"
        self.smart_order_routing = os.getenv("SMART_ORDER_ROUTING", str(self.smart_order_routing)).lower() == "true"

        try:
            min_order_quantity_env = os.getenv("MIN_ORDER_QUANTITY", str(self.min_order_quantity))
            if min_order_quantity_env.replace('.', '', 1).replace('-', '', 1).isdigit() or \
               (min_order_quantity_env.startswith('-') and min_order_quantity_env[1:].replace('.', '', 1).isdigit()):
                self.min_order_quantity = float(min_order_quantity_env)
            else:
                pass  # Keep default value
        except (ValueError, TypeError):
            pass  # Keep default value

        self.prevent_same_direction_trade_per_symbol = os.getenv("PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL", str(self.prevent_same_direction_trade_per_symbol)).lower() == "true"

        # Broker settings
        self.enabled_brokers = os.getenv("ENABLED_BROKERS", ",".join(self.enabled_brokers)).split(",")
        self.default_broker = os.getenv("DEFAULT_BROKER", self.default_broker)

        # Parse watcher broker configuration from environment variable
        # Format: "MarketPulse:BingX,Volatility:Binance,TrendMTF:MEXC"
        watcher_broker_str = os.getenv("WATCHER_BROKER_CONFIG", "")
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