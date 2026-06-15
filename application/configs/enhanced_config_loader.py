from typing import Dict, Any, Optional
from application.configs.env_loader import EnvLoader
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
import logging
from application.configs._config_extractors import _ConfigExtractorsMixin


class EnhancedConfigLoader(_ConfigExtractorsMixin):
    """
    Enhanced configuration loader that properly maps all environment variables to their respective schema fields.
    """

    def __init__(self, env_file_path: Optional[str] = None):
        """
        Initialize the enhanced config loader.

        Args:
            env_file_path: Optional path to .env file
        """
        self.env_loader = EnvLoader()
        self.env_vars = self.env_loader.load(env_file_path)

    def load_config(self, environment=None) -> Dict[str, Any]:
        """
        Load configuration for the specified environment.

        Args:
            environment: Target environment. If None, uses current environment.

        Returns:
            Dictionary containing all configuration objects
        """
        # Import Environment inside the function to avoid circular imports
        from application.configs.environments import Environment
        config_objects = {}

        # Broker configuration
        broker_data = self._extract_broker_config_data()
        config_objects['broker'] = BrokerConfig(**broker_data)

        # Risk configuration
        risk_data = self._extract_risk_config_data()
        config_objects['risk'] = RiskConfig(**risk_data)

        # Strategy configuration
        strategy_data = self._extract_strategy_config_data()
        config_objects['strategy'] = StrategyConfig(**strategy_data)

        # Execution configuration
        execution_data = self._extract_execution_config_data()
        config_objects['execution'] = ExecutionConfig(**execution_data)

        # Safety configuration
        safety_data = self._extract_safety_config_data()
        config_objects['safety'] = SafetyConfig(**safety_data)

        # Data configuration
        data_data = self._extract_data_config_data()
        config_objects['data'] = DataConfig(**data_data)

        # Optimization configuration
        optimization_data = self._extract_optimization_config_data()
        config_objects['optimization'] = OptimizationConfig(**optimization_data)

        # WFO configuration
        wfo_data = self._extract_wfo_config_data()
        config_objects['wfo'] = WFOConfig(**wfo_data)

        # Monitoring configuration
        monitoring_data = self._extract_monitoring_config_data()
        config_objects['monitoring'] = MonitoringConfig(**monitoring_data)

        # Analytics configuration
        analytics_data = self._extract_analytics_config_data()
        config_objects['analytics'] = AnalyticsConfig(**analytics_data)

        # Infrastructure configuration
        infrastructure_data = self._extract_infrastructure_config_data()
        config_objects['infrastructure'] = InfrastructureConfig(**infrastructure_data)

        # Position Sizing configuration
        position_sizing_data = self._extract_position_sizing_config_data()
        config_objects['position_sizing'] = PositionSizingConfig(**position_sizing_data)

        # Watcher configuration
        watcher_data = self._extract_watcher_config_data()
        config_objects['watcher'] = WatcherConfig(**watcher_data)

        # Portfolio configuration
        portfolio_data = self._extract_portfolio_config_data()
        config_objects['portfolio'] = PortfolioConfig(**portfolio_data)

        # Backtest configuration
        backtest_data = self._extract_backtest_config_data()
        config_objects['backtest'] = BacktestConfig(**backtest_data)

        # Fusion configuration
        fusion_data = self._extract_fusion_config_data()
        config_objects['fusion'] = FusionConfig(**fusion_data)

        return config_objects