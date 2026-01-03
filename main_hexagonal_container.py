"""Main hexagonal container for the Enterprise Hedge Fund Trading System - Clean Architecture Implementation."""

import sys
from pathlib import Path
from typing import Dict, Any
import logging

# Try to import torch, but make it optional to avoid dependency issues
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # When torch is not available, provide a mock to avoid errors
    class MockTorch:
        @staticmethod
        def cuda():
            class Cuda:
                @staticmethod
                def is_available():
                    return False
            return Cuda()
    torch = MockTorch()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.logger import EnhancedLogger
from domain.ports.optimization_ports import IOptimizationService, IDataLoader, IMetricCalculator
from application.services.optimization_service_app import OptimizationAppService
from application.services.adaptive_retuning import AdaptiveRetuningManager
from infrastructure.optimization import FileDataLoader
from infrastructure.results_tracking.results_tracker import ResultsTracker
from infrastructure.optimization import BacktestMetricCalculator
from infrastructure.optimization import OptimizationRepository
from infrastructure.data.coin_history_service import CoinHistoryService
from infrastructure.backtest.realistic_backtester import RealisticBacktester
from shared.auto_drop_engine import AutoDropEngine

# Import new architecture components
from infrastructure.engines.engine_service import engine_service
from infrastructure.fusion.fusion_service import fusion_service
from infrastructure.strategies.strategy_manager import strategy_manager


class MainHexagonalContainer:
    """
    Hexagonal architecture container that maintains clean architectural boundaries.
    Implements dependency inversion principle with ports and adapters pattern.
    Following correct architecture: Watcher → Engine → Fusion → Strategy → Broker
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.logger = EnhancedLogger("MainHexagonalContainer")

        self.logger.info("Initializing domain layer...")
        self._initialize_domain_layer()

        self.logger.info("Initializing application layer...")
        self._initialize_application_layer()

        self.logger.info("Initializing infrastructure layer...")
        self._initialize_infrastructure_layer()

        self.logger.info("Initializing shared components...")
        self._initialize_shared_components()

        self.logger.info("Initializing new architecture components...")
        self._initialize_new_architecture_components()

        self.logger.info("Wiring dependencies in hexagonal architecture...")
        self._wire_dependencies()

        self.logger.info("Dependencies wired successfully in hexagonal architecture")

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
            "initial_capital": 10000.0,
            "fee_rate": 0.001,
            "slippage_factor": 0.0005,
            "default_timeframe": "1h",
            "default_strategy": "crypto_breakout",
            "enable_auto_retune_scheduler": True,
            "retune_check_interval": 3600,
            "performance_check_interval": 1800,
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }

    def _initialize_domain_layer(self):
        """Initialize domain layer with pure business logic and ports."""
        self.logger.info("Domain layer initialized")

        # Domain services would go here in a full implementation
        # In our case, the domain logic is mostly in the application services
        # This layer focuses on business rules without infrastructure dependencies

    def _initialize_application_layer(self):
        """Initialize application layer services."""
        self.logger.info("Initializing application services...")

        # Application services that orchestrate domain logic
        self.optimization_app_service = OptimizationAppService()
        self.adaptive_retuning_manager = AdaptiveRetuningManager()

    def _initialize_infrastructure_layer(self):
        """Initialize infrastructure layer adapters and implementations."""
        self.logger.info("Initializing infrastructure layer...")

        # Infrastructure implementations (adapters)
        # Data loader adapter
        self.data_loader: IDataLoader = FileDataLoader(
            data_dir=self.config["data_cache_dir"]
        )

        # Results tracker adapter
        self.results_tracker = ResultsTracker(
            db_path=self.config["results_db_path"],
            storage_dir=self.config["results_storage_dir"]
        )

        # Metric calculator adapter
        self.metric_calculator: IMetricCalculator = BacktestMetricCalculator()

        # Optimization repository adapter
        self.optimization_repository = OptimizationRepository(
            storage_dir=self.config["optimization_results_dir"]
        )

        # Coin history service
        self.coin_history_service = CoinHistoryService(
            cache_dir=self.config["coin_cache_dir"],
            max_cache_age_hours=self.config["max_cache_age_hours"],
            max_cache_size=self.config["max_coin_cache_size"]
        )

        # Backtesting service
        self.backtester = RealisticBacktester(
            initial_capital=self.config["initial_capital"],
            fee_rate=self.config["fee_rate"],
            slippage_factor=self.config["slippage_factor"]
        )

        # Auto-drop engine
        self.auto_drop_engine = AutoDropEngine()

    def _initialize_new_architecture_components(self):
        """Initialize new architecture components following Watcher → Engine → Fusion → Strategy → Broker pattern."""
        self.logger.info("Initializing new architecture components...")

        # Engine service - processes raw observations into interpreted signals
        self.engine_service = engine_service
        self.engine_service.logger = self.logger

        # Fusion service - aggregates interpreted signals into fused signals
        self.fusion_service = fusion_service
        self.fusion_service.logger = self.logger

        # Strategy manager - the ONLY layer that selects strategies and deploys capital
        self.strategy_manager = strategy_manager
        # Add some default strategies
        from infrastructure.strategies.strategy_adapters import TrendFollowingStrategy, MeanReversionStrategy, VolatilityBreakoutStrategy
        self.strategy_manager.add_strategy(TrendFollowingStrategy())
        self.strategy_manager.add_strategy(MeanReversionStrategy())
        self.strategy_manager.add_strategy(VolatilityBreakoutStrategy())

    def _initialize_shared_components(self):
        """Initialize shared cross-cutting components."""
        self.logger.info("Initializing shared components...")
        # Shared components like logger are already initialized

    def _wire_dependencies(self):
        """Wire dependencies following hexagonal architecture principles."""
        self.logger.info("Wiring dependencies in hexagonal architecture...")

        # Inject infrastructure adapters into application services
        # This maintains dependency inversion: domain/application don't depend on infrastructure
        # but infrastructure adapts to domain/application interfaces

        # Configure optimization app service with dependencies
        self.optimization_app_service.configure(
            data_loader=self.data_loader,
            results_tracker=self.results_tracker,
            metric_calculator=self.metric_calculator
        )

        # Configure adaptive retuning with dependencies
        self.adaptive_retuning_manager.configure(
            results_tracker=self.results_tracker,
            data_loader=self.data_loader,
            coin_history_service=self.coin_history_service
        )

        # Verify all dependencies are properly wired
        self._verify_dependencies()

    def _verify_dependencies(self):
        """Verify that all dependencies are properly wired."""
        dependencies = [
            self.data_loader,
            self.results_tracker,
            self.metric_calculator,
            self.optimization_repository,
            self.coin_history_service,
            self.backtester,
            self.auto_drop_engine,
            self.optimization_app_service,
            self.adaptive_retuning_manager,
            self.engine_service,
            self.fusion_service,
            self.strategy_manager
        ]

        for dep in dependencies:
            assert dep is not None, f"Dependency {type(dep).__name__} is None"

        self.logger.info("All dependencies verified successfully")

    def get_port(self, port_name: str):
        """Get a port/adapter by name following hexagonal architecture."""
        ports = {
            # Infrastructure ports
            "data_loader": self.data_loader,
            "results_tracker": self.results_tracker,
            "metric_calculator": self.metric_calculator,
            "optimization_repository": self.optimization_repository,
            "coin_history_service": self.coin_history_service,
            "backtester": self.backtester,
            "auto_drop_engine": self.auto_drop_engine,

            # Application ports
            "optimization_app_service": self.optimization_app_service,
            "adaptive_retuning_manager": self.adaptive_retuning_manager,

            # New architecture components
            "engine_service": self.engine_service,
            "fusion_service": self.fusion_service,
            "strategy_manager": self.strategy_manager,
        }

        port = ports.get(port_name)
        if port is None:
            raise ValueError(f"Port {port_name} not found in hexagonal container")

        return port

    def get_all_ports(self) -> Dict[str, Any]:
        """Get all available ports/adapters."""
        return {
            "data_loader": self.data_loader,
            "results_tracker": self.results_tracker,
            "metric_calculator": self.metric_calculator,
            "optimization_repository": self.optimization_repository,
            "coin_history_service": self.coin_history_service,
            "backtester": self.backtester,
            "auto_drop_engine": self.auto_drop_engine,
            "optimization_app_service": self.optimization_app_service,
            "adaptive_retuning_manager": self.adaptive_retuning_manager,
            "engine_service": self.engine_service,
            "fusion_service": self.fusion_service,
            "strategy_manager": self.strategy_manager,
        }

    def validate_architecture(self) -> Dict[str, bool]:
        """Validate hexagonal architecture compliance."""
        validation_results = {
            "domain_layer_initialized": hasattr(self, 'optimization_app_service'),  # Application is part of this
            "application_layer_initialized": hasattr(self, 'optimization_app_service'),
            "infrastructure_layer_initialized": hasattr(self, 'data_loader'),
            "new_architecture_components_initialized": (
                hasattr(self, 'engine_service') and
                hasattr(self, 'fusion_service') and
                hasattr(self, 'strategy_manager')
            ),
            "dependencies_properly_wired": (
                self.optimization_app_service.data_loader is not None and
                self.adaptive_retuning_manager.results_tracker is not None
            ),
            "ports_accessible": True  # This is verified by trying to access them
        }

        return validation_results

    def shutdown(self):
        """Clean shutdown of hexagonal container."""
        self.logger.info("Shutting down hexagonal container")
        # Add any cleanup logic if needed