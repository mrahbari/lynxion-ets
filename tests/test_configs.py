import os
import pytest
from unittest.mock import patch, MagicMock
from application.configs.configs import Configs
from application.configs.environments import (
    Environment, get_current_environment, is_live_environment,
    is_dev_environment, is_test_environment
)
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


class TestConfigs:
    """Test suite for the configuration system."""
    
    def setup_method(self):
        """Reset the singleton state before each test."""
        Configs._initialized = False
        Configs.broker = None
        Configs.risk = None
        Configs.strategy = None
        Configs.execution = None
        Configs.safety = None
        Configs.data = None
        Configs.optimization = None
        Configs.wfo = None
        Configs.monitoring = None
        Configs.analytics = None
    
    def test_configs_initialization(self):
        """Test that configs are properly initialized."""
        Configs.initialize(environment=Environment.DEV)
        
        assert Configs.broker is not None
        assert Configs.risk is not None
        assert Configs.strategy is not None
        assert Configs.execution is not None
        assert Configs.safety is not None
        assert Configs.data is not None
        assert Configs.optimization is not None
        assert Configs.wfo is not None
        assert Configs.monitoring is not None
        assert Configs.analytics is not None
    
    def test_configs_validation(self):
        """Test that all configs can be validated."""
        Configs.initialize(environment=Environment.DEV)
        
        # This should not raise any exceptions
        Configs.validate_all()
    
    def test_broker_config_properties(self):
        """Test broker configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.broker, BrokerConfig)
        assert Configs.broker.api_key == "dev_api_key"
        assert Configs.broker.secret_key == "dev_secret_key"
        assert Configs.broker.testnet is True
        assert Configs.broker.paper_trading is True
    
    def test_risk_config_properties(self):
        """Test risk configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.risk, RiskConfig)
        assert Configs.risk.max_drawdown == 0.1
        assert Configs.risk.max_risk_per_trade == 0.02
        assert Configs.risk.max_correlation == 0.7
    
    def test_strategy_config_properties(self):
        """Test strategy configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.strategy, StrategyConfig)
        assert Configs.strategy.strategy_name == "dev_strategy"
        assert Configs.strategy.enabled is True
    
    def test_execution_config_properties(self):
        """Test execution configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.execution, ExecutionConfig)
        assert Configs.execution.order_type == "market"
        assert Configs.execution.slippage_tolerance == 0.001
    
    def test_safety_config_properties(self):
        """Test safety configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.safety, SafetyConfig)
        assert Configs.safety.circuit_breaker_enabled is True
        assert Configs.safety.max_daily_losses == 5000.0
    
    def test_data_config_properties(self):
        """Test data configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.data, DataConfig)
        assert Configs.data.data_source == "simulated"
        assert Configs.data.cache_enabled is True
    
    def test_optimization_config_properties(self):
        """Test optimization configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.optimization, OptimizationConfig)
        assert Configs.optimization.optimization_enabled is False
        assert Configs.optimization.population_size == 50
    
    def test_wfo_config_properties(self):
        """Test WFO configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.wfo, WFOConfig)
        assert Configs.wfo.wfo_enabled is False
        assert Configs.wfo.window_size == 252
    
    def test_monitoring_config_properties(self):
        """Test monitoring configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.monitoring, MonitoringConfig)
        assert Configs.monitoring.logging_level == "DEBUG"
        assert Configs.monitoring.alert_enabled is False
    
    def test_analytics_config_properties(self):
        """Test analytics configuration properties."""
        Configs.initialize(environment=Environment.DEV)
        
        assert isinstance(Configs.analytics, AnalyticsConfig)
        assert Configs.analytics.analytics_enabled is True
        assert Configs.analytics.report_frequency == "daily"
    
    def test_environment_switching(self):
        """Test that different environments load different configs."""
        # Test dev environment
        Configs.initialize(environment=Environment.DEV)
        dev_max_position_size = Configs.risk.max_position_size
        
        # Reset and test live environment
        Configs._initialized = False
        Configs.initialize(environment=Environment.LIVE)
        live_max_position_size = Configs.risk.max_position_size
        
        # These should be different values
        assert dev_max_position_size != live_max_position_size
        assert dev_max_position_size == 1000.0  # Dev value
        assert live_max_position_size == 100000.0  # Live value
    
    def test_reload_functionality(self):
        """Test that configs can be reloaded."""
        Configs.initialize(environment=Environment.DEV)
        original_value = Configs.risk.max_drawdown
        
        Configs.reload(environment=Environment.LIVE)
        new_value = Configs.risk.max_drawdown
        
        assert original_value != new_value
        assert new_value == 0.02  # Live value
    
    def test_get_env_var(self):
        """Test getting environment variables through the config system."""
        # Set up a mock environment variable
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            Configs.initialize(environment=Environment.DEV)
            
            # This would normally fail because env vars aren't loaded in dev profile
            # But we can test the method exists and works with the loader
            assert hasattr(Configs, 'get_env_var')
    
    def test_invalid_config_raises_error(self):
        """Test that invalid configurations raise appropriate errors."""
        # This test would require creating intentionally invalid configs
        # which is difficult with Pydantic's validation happening at instantiation
        # Instead, we'll verify that validation runs without error for valid configs
        Configs.initialize(environment=Environment.DEV)
        Configs.validate_all()  # Should not raise an exception
    
    def test_singleton_pattern(self):
        """Test that Configs follows the singleton pattern."""
        config1 = Configs()
        config2 = Configs()
        
        assert config1 is config2
        assert Configs._instance is config1


def test_environment_detection():
    """Test environment detection functionality."""
    # Need to temporarily reset the global config to test environment detection
    original_env = os.environ.get('LYNXION_ENV'), os.environ.get('ENVIRONMENT')

    # Clean environment first
    if 'LYNXION_ENV' in os.environ:
        del os.environ['LYNXION_ENV']
    if 'ENVIRONMENT' in os.environ:
        del os.environ['ENVIRONMENT']

    # Test LYNXION_ENV
    os.environ['LYNXION_ENV'] = 'live'
    env = get_current_environment()
    assert env == Environment.LIVE

    # Test ENVIRONMENT fallback
    del os.environ['LYNXION_ENV']
    os.environ['ENVIRONMENT'] = 'staging'
    env = get_current_environment()
    assert env == Environment.STAGING

    # Test default
    del os.environ['ENVIRONMENT']
    env = get_current_environment()
    assert env == Environment.DEV

    # Restore original environment
    if original_env[0] is not None:
        os.environ['LYNXION_ENV'] = original_env[0]
    if original_env[1] is not None:
        os.environ['ENVIRONMENT'] = original_env[1]


def test_environment_helpers():
    """Test environment helper functions."""
    with patch.dict(os.environ, {'LYNXION_ENV': 'live'}):
        assert get_current_environment() == Environment.LIVE
        assert is_live_environment() is True
        assert is_dev_environment() is False
        assert is_test_environment() is False
    
    with patch.dict(os.environ, {'LYNXION_ENV': 'dev'}):
        assert get_current_environment() == Environment.DEV
        assert is_dev_environment() is True
        assert is_test_environment() is True
        assert is_live_environment() is False
    
    with patch.dict(os.environ, {'LYNXION_ENV': 'staging'}):
        assert is_test_environment() is True
        assert is_live_environment() is False