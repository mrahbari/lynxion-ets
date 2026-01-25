from typing import Optional
from application.configs.enhanced_config_loader import EnhancedConfigLoader
from application.configs.schemas.broker import BrokerConfig
from application.configs.schemas.risk import RiskConfig
from application.configs.schemas.strategy import StrategyConfig
from application.configs.schemas.execution import ExecutionConfig
from application.configs.schemas.safety import SafetyConfig
from application.configs.schemas.data import DataConfig
from application.configs.schemas.optimization import OptimizationConfig
from application.configs.schemas.wfo import WFOConfig
from application.configs.schemas.monitoring import MonitoringConfig
from application.configs.schemas.analytics import AnalyticsConfig
from application.configs.schemas.infrastructure import InfrastructureConfig
from application.configs.schemas.position_sizing import PositionSizingConfig
from application.configs.schemas.watcher import WatcherConfig
from application.configs.schemas.portfolio import PortfolioConfig
from application.configs.schemas.backtest import BacktestConfig
from application.configs.schemas.fusion import FusionConfig


class Configs:
    """
    Singleton class providing global access to all configurations.
    This is the single access point for all configuration values in the application.
    """

    _instance = None
    _initialized = False
    _config_loader: Optional[EnhancedConfigLoader] = None

    # Configuration attributes
    broker: Optional[BrokerConfig] = None
    risk: Optional[RiskConfig] = None
    strategy: Optional[StrategyConfig] = None
    execution: Optional[ExecutionConfig] = None
    safety: Optional[SafetyConfig] = None
    data: Optional[DataConfig] = None
    optimization: Optional[OptimizationConfig] = None
    wfo: Optional[WFOConfig] = None
    monitoring: Optional[MonitoringConfig] = None
    analytics: Optional[AnalyticsConfig] = None
    infrastructure: Optional[InfrastructureConfig] = None
    position_sizing: Optional[PositionSizingConfig] = None
    watcher: Optional[WatcherConfig] = None
    portfolio: Optional[PortfolioConfig] = None
    backtest: Optional[BacktestConfig] = None
    fusion: Optional[FusionConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Configs, cls).__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, env_file_path: str = None, environment=None):
        """
        Initialize the configuration system.

        Args:
            env_file_path: Optional path to .env file
            environment: Target environment. If None, uses current environment.
        """
        if cls._initialized:
            return  # Already initialized

        # Import Environment inside the function to avoid circular imports
        from application.configs.environments import Environment, get_current_environment

        if environment is None:
            environment = get_current_environment()

        cls._config_loader = EnhancedConfigLoader(env_file_path)
        config_objects = cls._config_loader.load_config(environment)

        # Assign configuration objects to class attributes
        cls.broker = config_objects.get('broker')
        cls.risk = config_objects.get('risk')
        cls.strategy = config_objects.get('strategy')
        cls.execution = config_objects.get('execution')
        cls.safety = config_objects.get('safety')
        cls.data = config_objects.get('data')
        cls.optimization = config_objects.get('optimization')
        cls.wfo = config_objects.get('wfo')
        cls.monitoring = config_objects.get('monitoring')
        cls.analytics = config_objects.get('analytics')
        cls.infrastructure = config_objects.get('infrastructure')
        cls.position_sizing = config_objects.get('position_sizing')
        cls.watcher = config_objects.get('watcher')
        cls.portfolio = config_objects.get('portfolio')
        cls.backtest = config_objects.get('backtest')
        cls.fusion = config_objects.get('fusion')

        cls._initialized = True

    @classmethod
    def validate_all(cls):
        """
        Validate all configuration objects.

        Raises:
            ValidationError: If any configuration object is invalid
        """
        if not cls._initialized:
            cls.initialize()

        # Since Pydantic models are validated on creation,
        # we just need to ensure they exist and are accessible
        assert cls.broker is not None, "Broker config is not initialized"
        assert cls.risk is not None, "Risk config is not initialized"
        assert cls.strategy is not None, "Strategy config is not initialized"
        assert cls.execution is not None, "Execution config is not initialized"
        assert cls.safety is not None, "Safety config is not initialized"
        assert cls.data is not None, "Data config is not initialized"
        assert cls.optimization is not None, "Optimization config is not initialized"
        assert cls.wfo is not None, "WFO config is not initialized"
        assert cls.monitoring is not None, "Monitoring config is not initialized"
        assert cls.analytics is not None, "Analytics config is not initialized"
        assert cls.infrastructure is not None, "Infrastructure config is not initialized"
        assert cls.position_sizing is not None, "Position sizing config is not initialized"
        assert cls.watcher is not None, "Watcher config is not initialized"
        assert cls.portfolio is not None, "Portfolio config is not initialized"
        assert cls.backtest is not None, "Backtest config is not initialized"
        assert cls.fusion is not None, "Fusion config is not initialized"

    @classmethod
    def reload(cls, env_file_path: str = None, environment=None):
        """
        Reload all configurations.

        Args:
            env_file_path: Optional path to .env file
            environment: Target environment. If None, uses current environment.
        """
        cls._initialized = False
        cls.initialize(env_file_path, environment)

    @classmethod
    def get_env_var(cls, key: str, default: str = None) -> str:
        """
        Get an environment variable value through the config loader.

        Args:
            key: Environment variable key
            default: Default value if key is not found

        Returns:
            Value of the environment variable or default
        """
        if cls._config_loader is None:
            raise RuntimeError("Configs not initialized. Call Configs.initialize() first.")
        return cls._config_loader.env_loader.get_env_var(key, default)

    @classmethod
    def get_required_env_var(cls, key: str) -> str:
        """
        Get a required environment variable value. Raises exception if not found.

        Args:
            key: Environment variable key

        Returns:
            Value of the environment variable
        """
        if cls._config_loader is None:
            raise RuntimeError("Configs not initialized. Call Configs.initialize() first.")
        return cls._config_loader.env_loader.get_required_env_var(key)


# Initialize configs automatically when module is imported
Configs.initialize()