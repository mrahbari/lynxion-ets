"""Main container for the Hyperopt Auto-Retune system - Production Ready."""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.logger import EnhancedLogger
from shared.configurable_hyperopt import ConfigurableHyperoptOptimizer, HyperoptConfig
from infrastructure.results_tracking.results_tracker import ResultsTracker
from infrastructure.data.coin_history_service import CoinHistoryService
from application.services.optimization_service_app import OptimizationAppService
from application.services.adaptive_retuning import AdaptiveRetuningManager
from infrastructure.backtest.realistic_backtester import RealisticBacktester
from shared.auto_drop_engine import AutoDropEngine


class MainContainer:
    """
    Production-ready main container implementing dependency injection for the Hyperopt Auto-Retune system.
    Follows clean architecture principles with clear separation of concerns.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize all services with dependency injection."""
        self.config = config or self._get_default_config()
        self.logger = EnhancedLogger("MainContainer")
        
        # Initialize shared components
        self._initialize_shared_components()
        
        # Initialize infrastructure services  
        self._initialize_infrastructure_services()
        
        # Initialize application services
        self._initialize_application_services()
        
        # Initialize domain services
        self._initialize_domain_services()
        
        self.logger.info("Main container initialized with all services")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default production configuration."""
        return {
            "data_cache_dir": "data/cache",
            "results_db_path": "data/results.db",
            "results_storage_dir": "data/results_storage",
            "coin_cache_dir": "data/coin_history_cache",
            "optimization_results_dir": "data/optimization_results",
            "max_cache_age_hours": 24,
            "max_coin_cache_size": 50,
            "initial_capital": 1000000.0,
            "fee_rate": 0.001,
            "slippage_factor": 0.0005,
            "default_timeframe": "1h",
            "default_strategy": "crypto_breakout",
            "enable_auto_retune_scheduler": True,
            "retune_check_interval": 3600,  # 1 hour
            "performance_check_interval": 1800,  # 30 minutes
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
    
    def _initialize_shared_components(self):
        """Initialize shared components."""
        self.logger.info("Initializing shared components...")
        
        # Create necessary directories
        for dir_path in [
            self.config["data_cache_dir"],
            self.config["results_storage_dir"], 
            self.config["coin_cache_dir"],
            self.config["optimization_results_dir"]
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def _initialize_infrastructure_services(self):
        """Initialize infrastructure layer services."""
        self.logger.info("Initializing infrastructure services...")
        
        # Data loading and caching
        self.data_loader = FileDataLoader(data_dir=self.config["data_cache_dir"])
        
        # Results tracking
        self.results_tracker = ResultsTracker(
            db_path=self.config["results_db_path"],
            storage_dir=self.config["results_storage_dir"],
            use_database=True
        )
        
        # Coin history with caching
        self.coin_history_service = CoinHistoryService(
            cache_dir=self.config["coin_cache_dir"],
            max_cache_age_hours=self.config["max_cache_age_hours"],
            max_cache_size=self.config["max_coin_cache_size"]
        )
        
        # Realistic backtesting
        self.backtester = RealisticBacktester(
            initial_capital=self.config["initial_capital"],
            fee_rate=self.config["fee_rate"],
            slippage_factor=self.config["slippage_factor"]
        )
        
        # Auto-drop engine
        self.auto_drop = AutoDropEngine()
    
    def _initialize_application_services(self):
        """Initialize application layer services."""
        self.logger.info("Initializing application services...")
        
        # Optimization application service
        self.optimization_app_service = OptimizationAppService(
            data_loader=self.data_loader,
            results_tracker=self.results_tracker,
            backtester=self.backtester
        )
        
        # Adaptive retuning manager
        self.adaptive_retuning_manager = AdaptiveRetuningManager(
            results_tracker=self.results_tracker,
            schedule_config={
                "daily_retuning_enabled": True,
                "weekly_retuning_enabled": True,
                "monthly_retuning_enabled": True
            },
            performance_config={
                "sharpe_ratio_threshold": 0.5,
                "max_drawdown_threshold": -0.15,
                "win_rate_threshold": 0.45
            }
        )
    
    def _initialize_domain_services(self):
        """Initialize domain layer services."""
        self.logger.info("Initializing domain services...")
        
        # Hyperopt configuration
        self.hyperopt_config = HyperoptConfig(
            strategy_name=self.config["default_strategy"]
        )
        
        # Configurable hyperopt optimizer
        self.hyperopt_optimizer = ConfigurableHyperoptOptimizer(
            hyperopt_config=self.hyperopt_config
        )
    
    def get_service(self, service_name: str):
        """Get a service by name."""
        services = {
            'data_loader': self.data_loader,
            'results_tracker': self.results_tracker,
            'coin_history_service': self.coin_history_service,
            'backtester': self.backtester,
            'auto_drop': self.auto_drop,
            'optimization_app_service': self.optimization_app_service,
            'adaptive_retuning_manager': self.adaptive_retuning_manager,
            'hyperopt_config': self.hyperopt_config,
            'hyperopt_optimizer': self.hyperopt_optimizer
        }
        
        service = services.get(service_name)
        if service is None:
            raise ValueError(f"Service {service_name} not found")
        
        return service

    def get_all_services(self) -> Dict[str, Any]:
        """Get all initialized services."""
        return {
            'data_loader': self.data_loader,
            'results_tracker': self.results_tracker,
            'coin_history_service': self.coin_history_service,
            'backtester': self.backtester,
            'auto_drop': self.auto_drop,
            'optimization_app_service': self.optimization_app_service,
            'adaptive_retuning_manager': self.adaptive_retuning_manager,
            'hyperopt_config': self.hyperopt_config,
            'hyperopt_optimizer': self.hyperopt_optimizer
        }

    def shutdown(self):
        """Clean shutdown of all services."""
        self.logger.info("Shutting down main container")
        # Add any cleanup logic here if needed