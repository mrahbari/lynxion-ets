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
        self.api_timeout = int(os.getenv("API_TIMEOUT", str(self.api_timeout)))
        self.max_workers = int(os.getenv("MAX_WORKERS", str(self.max_workers)))
        self.redis_url = os.getenv("REDIS_URL", self.redis_url)
        self.enable_metrics = os.getenv("ENABLE_METRICS", str(self.enable_metrics)).lower() == "true"
        
        # Risk settings - need to extract the decimal value from Percentage
        self.max_portfolio_risk = Percentage(Decimal(os.getenv("MAX_PORTFOLIO_RISK", str(float(self.max_portfolio_risk.value)))))
        self.max_position_risk = Percentage(Decimal(os.getenv("MAX_POSITION_RISK", str(float(self.max_position_risk.value)))))
        self.max_drawdown = Percentage(Decimal(os.getenv("MAX_DRAWDOWN", str(float(self.max_drawdown.value)))))
        self.max_correlation = Percentage(Decimal(os.getenv("MAX_CORRELATION", str(float(self.max_correlation.value)))))
        self.max_leverage = float(os.getenv("MAX_LEVERAGE", str(self.max_leverage)))
        self.max_daily_loss = Percentage(Decimal(os.getenv("MAX_DAILY_LOSS", str(float(self.max_daily_loss.value)))))
        self.enable_kill_switch = os.getenv("ENABLE_KILL_SWITCH", str(self.enable_kill_switch)).lower() == "true"

        # Trading settings
        self.target_volatility = Percentage(Decimal(os.getenv("TARGET_VOLATILITY", str(float(self.target_volatility.value)))))
        self.rebalance_frequency = os.getenv("REBALANCE_FREQUENCY", self.rebalance_frequency)
        self.position_sizing_method = os.getenv("POSITION_SIZING_METHOD", self.position_sizing_method)
        self.min_order_size = float(os.getenv("MIN_ORDER_SIZE", str(self.min_order_size)))
        self.max_order_size = float(os.getenv("MAX_ORDER_SIZE", str(self.max_order_size)))
        self.enable_shorting = os.getenv("ENABLE_SHORTING", str(self.enable_shorting)).lower() == "true"
        self.max_position_concentration = Percentage(Decimal(os.getenv("MAX_POSITION_CONCENTRATION", str(float(self.max_position_concentration.value)))))

        # Backtesting settings
        self.initial_capital = float(os.getenv("INITIAL_CAPITAL", str(self.initial_capital)))
        self.commission_rate = float(os.getenv("COMMISSION_RATE", str(self.commission_rate)))
        self.slippage_rate = float(os.getenv("SLIPPAGE_RATE", str(self.slippage_rate)))
        self.start_date = os.getenv("BACKTEST_START_DATE", self.start_date)
        self.end_date = os.getenv("BACKTEST_END_DATE", self.end_date)
        self.benchmark_symbol = os.getenv("BENCHMARK_SYMBOL", self.benchmark_symbol)

        # Watcher settings
        self.enabled_watchers = os.getenv("ENABLED_WATCHERS", ",".join(self.enabled_watchers)).split(",")
        self.update_frequency = int(os.getenv("WATCHER_UPDATE_FREQ", str(self.update_frequency)))
        self.lookback_period = int(os.getenv("WATCHER_LOOKBACK", str(self.lookback_period)))
        self.signal_threshold = float(os.getenv("SIGNAL_THRESHOLD", str(self.signal_threshold)))
        self.auto_enable_watchers = os.getenv("AUTO_ENABLE_WATCHERS", str(self.auto_enable_watchers)).lower() == "true"

        # Engine settings
        self.enabled_engines = os.getenv("ENABLED_ENGINES", ",".join(self.enabled_engines)).split(",")
        self.confidence_threshold = float(os.getenv("ENGINE_CONFIDENCE_THRESHOLD", str(self.confidence_threshold)))
        self.signal_fusion_enabled = os.getenv("SIGNAL_FUSION_ENABLED", str(self.signal_fusion_enabled)).lower() == "true"
        self.regime_detection_enabled = os.getenv("REGIME_DETECTION_ENABLED", str(self.regime_detection_enabled)).lower() == "true"
        self.ml_weights_enabled = os.getenv("ML_WEIGHTS_ENABLED", str(self.ml_weights_enabled)).lower() == "true"

        # Execution settings
        self.slippage_tolerance = float(os.getenv("SLIPPAGE_TOLERANCE", str(self.slippage_tolerance)))
        self.order_timeout = int(os.getenv("ORDER_TIMEOUT", str(self.order_timeout)))
        self.retry_attempts = int(os.getenv("RETRY_ATTEMPTS", str(self.retry_attempts)))
        self.enable_twap = os.getenv("ENABLE_TWAP", str(self.enable_twap)).lower() == "true"
        self.enable_vwap = os.getenv("ENABLE_VWAP", str(self.enable_vwap)).lower() == "true"
        self.smart_order_routing = os.getenv("SMART_ORDER_ROUTING", str(self.smart_order_routing)).lower() == "true"
        self.min_order_quantity = float(os.getenv("MIN_ORDER_QUANTITY", str(self.min_order_quantity)))
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