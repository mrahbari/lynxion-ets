"""Composition root (E2.T1).

A single place that constructs adapters, injects typed settings, and exposes
them by key. Construction is fully lazy (factories run on first ``resolve``)
and there are **no module-level side effects** — nothing is built at import
time. Lifecycle (startup/shutdown) is owned by :mod:`bootstrap.lifecycle`.

Scope note: this wires the set of ports/adapters that are safely
instantiable in an offline environment (data, file-repo, backtest,
optimization/results). Ports that require external resources (live brokers,
network data providers, ML/torch components) are intentionally deferred; add
them via :meth:`Container.register` using the same factory pattern.
"""

import os
from typing import Any, Callable, Dict, List, Optional

from bootstrap.settings.schema import Settings


class Container:
    """Lazy, settings-injected dependency container."""

    def __init__(self, settings: Settings, base_data_dir: Optional[str] = None):
        self.settings = settings
        self._base_data_dir = base_data_dir or getattr(settings.data, "dir", "./data/history")
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._register_default_factories()

    # -- registration / resolution -------------------------------------------------

    def register(self, key: str, factory: Callable[[], Any]) -> None:
        """Register a zero-arg factory for ``key`` (overrides any existing)."""
        self._factories[key] = factory

    def resolve(self, key: str) -> Any:
        """Resolve (and cache) the adapter registered under ``key``."""
        if key in self._instances:
            return self._instances[key]
        if key not in self._factories:
            raise KeyError(f"No factory registered for '{key}'")
        instance = self._factories[key]()
        self._instances[key] = instance
        return instance

    def resolve_all(self) -> Dict[str, Any]:
        """Resolve every registered key; raises if any factory errors."""
        return {key: self.resolve(key) for key in self._factories}

    def registered_keys(self) -> List[str]:
        return list(self._factories)

    def risk_enforcement(self) -> Any:
        """Helper to return the active RiskEnforcement instance."""
        return getattr(self, "_risk_enforcement", None)

    # -- lifecycle -----------------------------------------------------------------

    def shutdown(self) -> None:
        """Release resources held by resolved instances (best-effort)."""
        for instance in self._instances.values():
            for method in ("close", "shutdown", "dispose"):
                fn = getattr(instance, method, None)
                if callable(fn):
                    try:
                        fn()
                    except Exception:
                        pass
                    break
        self._instances.clear()
        # Best-effort: close any broker connections registered globally.
        try:
            from infrastructure.services.broker_registry import broker_registry
            broker_registry.clear_registry()
        except Exception:
            pass

    # -- internals -----------------------------------------------------------------

    def _path(self, *parts: str) -> str:
        return os.path.join(self._base_data_dir, *parts)

    def _register_default_factories(self) -> None:
        self.register("file_repository", self._build_file_repository)
        self.register("data_loader", self._build_data_loader)
        self.register("metric_calculator", self._build_metric_calculator)
        self.register("backtester", self._build_backtester)
        # Canonical backtest engine port (E3.T1): thin BacktestEnginePort adapter
        # over the live RealisticBacktester. Additive — the backtester /
        # backtester_factory registrations and all live consumers are unchanged.
        self.register("backtest_engine", self._build_backtest_engine)
        self.register("coin_history_service", self._build_coin_history_service)
        self.register("optimization_repository", self._build_optimization_repository)
        self.register("results_tracker", self._build_results_tracker)
        self.register("data_downloader", self._build_data_downloader)
        self.register("sync_manager", self._build_sync_manager)
        self.register("watcher_retune", self._build_watcher_retune)
        self.register("csv_history_loader", self._build_csv_history_loader)
        self.register("data_integrity_checker", self._build_data_integrity_checker)
        self.register("data_integrity_report", self._build_data_integrity_report)
        self.register("hyperopt_param_space_factory", self._build_hyperopt_param_space_factory)
        self.register("portfolio_backtester_factory", self._build_portfolio_backtester_factory)
        self.register("wfo_orchestrator_factory", self._build_wfo_orchestrator_factory)
        self.register("hyperopt_optimizer_factory", self._build_hyperopt_optimizer_factory)
        self.register("backtester_factory", self._build_backtester_factory)
        self.register("backtest_strategy_provider", self._build_backtest_strategy_provider)
        self.register("capital_allocator_factory", self._build_capital_allocator_factory)
        self.register("monte_carlo_analyzer", self._build_monte_carlo_analyzer)
        self.register("kill_switch_factory", self._build_kill_switch_factory)
        self.register("portfolio_walk_forward_validator", self._build_portfolio_walk_forward_validator)
        self.register("historical_data_provider_factory", self._build_historical_data_provider_factory)
        self.register("historical_csv_loader_factory", self._build_historical_csv_loader_factory)
        self.register("shadow_strategy_provider", self._build_shadow_strategy_provider)
        self.register("shadow_csv_loader_factory", self._build_shadow_csv_loader_factory)
        self.register("shadow_kpi_reporter", self._build_shadow_kpi_reporter)
        self.register("legacy_backtest_use_case_factory", self._build_legacy_backtest_use_case_factory)
        self.register("hyperopt_config_factory", self._build_hyperopt_config_factory)
        self.register("auto_retune_optimizer_factory", self._build_auto_retune_optimizer_factory)
        self.register("production_orchestrator_factory", self._build_production_orchestrator_factory)
        self.register("auto_detection_orchestrator_factory", self._build_auto_detection_orchestrator_factory)
        # Retired global singletons (E2.T6) -> container-scoped.
        self.register("strategy_manager", self._build_strategy_manager)
        self.register("engine_service", self._build_engine_service)
        # Canonical engine port (E3.T7.1): thin EnginePort adapter over the live
        # engine_service. Additive — engine_service registration and the live
        # orchestrator import path are unchanged.
        self.register("engine", self._build_engine)
        self.register("fusion_service", self._build_fusion_service)
        self.register("regime_detector", self._build_regime_detector)
        self.register("broker_registry", self._build_broker_registry)
        self.register("global_rate_limiter", self._build_global_rate_limiter)
        self.register("pending_orders_tracker", self._build_pending_orders_tracker)
        # Portfolio Allocation Engine (Task 0040).
        self.register("portfolio_allocation_engine", self._build_portfolio_allocation_engine)
        # Consolidated position-sizing engine (E3.T3).
        self.register("position_sizing_engine", self._build_position_sizing_engine)
        # Consolidated risk engine (E3.T4): portfolio risk + separated SL/TP.
        self.register("risk_engine", self._build_risk_engine)
        # Consolidated tracking system (E3.T5): trade + results + shadow-KPI.
        self.register("tracking", self._build_tracking)
        # Consolidated logger + event bus (E3.T6).
        self.register("logging", self._build_logging)
        self.register("message_bus", self._build_message_bus)
        # Statistical-validation services behind ports (E3.T9, F11/F12).
        self.register("confidence_calibrator", self._build_confidence_calibrator)
        self.register("randomness_firewall", self._build_randomness_firewall)
        self.register("statistical_authority_engine", self._build_statistical_authority_engine)
        self.register("statistical_historical_data_tracker", self._build_statistical_historical_data_tracker)
        self.register("decision_defensibility_validator", self._build_decision_defensibility_validator)
        self.register("market_structure_engine", self._build_market_structure_engine)
        self.register("setup_engine", self._build_setup_engine)
        self.register("execution_confirmation_engine", self._build_execution_confirmation_engine)
        self.register("execution_optimizer", self._build_execution_optimizer)
        self.register("decision_pipeline", self._build_decision_pipeline)

    # Factories use local imports so importing this module has no heavy/side effects.

    def _build_file_repository(self):
        from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
        return FileRepositoryAdapter(
            base_data_dir=self._base_data_dir,
            raw_retention_days=self.settings.data.raw_retention_days,
        )

    def _build_data_loader(self):
        from infrastructure.optimization import FileDataLoader
        return FileDataLoader(data_dir=self._path("cache"))

    def _build_metric_calculator(self):
        from infrastructure.optimization import BacktestMetricCalculator
        return BacktestMetricCalculator()

    def _build_backtester(self):
        from infrastructure.backtest.realistic_backtester import RealisticBacktester
        bt = self.settings.backtest
        return RealisticBacktester(
            initial_capital=bt.initial_capital,
            fee_rate=bt.fee_rate,
            slippage_factor=bt.slippage_factor,
        )

    def _build_backtest_engine(self):
        # Canonical BacktestEnginePort (E3.T1): pure-delegation adapter over the
        # container's RealisticBacktester. No new singleton — reuses the resolved one.
        from infrastructure.backtest.backtest_engine_adapter import RealisticBacktesterAdapter
        return RealisticBacktesterAdapter(self.resolve("backtester"))

    def _build_coin_history_service(self):
        from infrastructure.data.coin_history_service import CoinHistoryService
        data = self.settings.data
        return CoinHistoryService(
            cache_dir=self._path("coin_history_cache"),
            max_cache_age_hours=getattr(data, "max_cache_age_hours", 24),
            max_cache_size=getattr(data, "max_coin_cache_size", 50),
        )

    def _build_optimization_repository(self):
        from infrastructure.optimization import OptimizationRepository
        return OptimizationRepository(storage_dir=self._path("optimization_results"))

    def _build_results_tracker(self):
        from infrastructure.results_tracking.results_tracker import ResultsTracker
        return ResultsTracker(
            db_path=self._path("results.db"),
            storage_dir=self._path("results_storage"),
        )

    # Data-sync ports (E2.T3). Both are offline-safe to construct: the
    # downloader only opens its aiohttp session inside ``async with`` and the
    # sync manager's thread pool spawns workers lazily on first submit.

    def _build_data_downloader(self):
        from infrastructure.data_sync.data_downloader_adapter import DataDownloaderAdapter
        return DataDownloaderAdapter()

    def _build_sync_manager(self):
        from application.data_sync.sync_manager import SyncManager
        return SyncManager(self.resolve("file_repository"), self.resolve("data_downloader"))

    def _build_watcher_retune(self):
        from application.data_sync.watcher_retune import WatcherRetuneUseCase
        return WatcherRetuneUseCase(
            self.resolve("file_repository"),
            self.resolve("data_downloader"),
            self.resolve("sync_manager"),
        )

    # Validation / optimization ports (E2.T4). csv_history_loader and
    # data_integrity_checker are offline-safe ports built eagerly. The remaining
    # infra is exposed as factory callables that import + construct lazily, so
    # resolve_all() (offline smoke) never imports heavy/request-parameterized
    # dependencies (e.g. hyperopt / WFO) -- they are only built when a use case
    # actually invokes the factory during a real run.

    def _build_csv_history_loader(self):
        from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
        return CSVHistoryLoaderAdapter()

    def _build_data_integrity_checker(self):
        # Canonical home migrated to infrastructure/data/integrity (E3.T10);
        # behind DataIntegrityPort. utils/ retains a deprecated re-export shim.
        from infrastructure.data.integrity.data_integrity_checker import DataIntegrityChecker
        return DataIntegrityChecker()

    def _build_data_integrity_report(self):
        from infrastructure.data.integrity.data_integrity_report import DataIntegrityReport
        return DataIntegrityReport(base_path=self._base_data_dir)

    def _build_hyperopt_param_space_factory(self):
        def factory():
            from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
            return HyperoptParameterSpace()
        return factory

    def _build_portfolio_backtester_factory(self):
        def factory(initial_capital, fee_rate, slippage_factor):
            from infrastructure.portfolio.comprehensive_portfolio_backtester import ComprehensivePortfolioBacktester
            # E-P5.2 T3: the composition root builds backtesters for real
            # validation runs, so the runtime ``use_mock_data`` setting is NOT
            # propagated here. Mock data is a hard error in any wired run and is
            # only reachable via explicit in-code injection in unit tests
            # (see shared.mock_data_guard). Defaults to use_mock_data=False.
            return ComprehensivePortfolioBacktester(
                initial_capital=initial_capital,
                fee_rate=fee_rate,
                slippage_factor=slippage_factor,
            )
        return factory

    def _build_wfo_orchestrator_factory(self):
        def factory(config):
            from application.walk_forward.wfo_orchestrator import WFOOrchestrator
            return WFOOrchestrator(config=config)
        return factory

    def _build_hyperopt_optimizer_factory(self):
        def factory(hyperopt_config, strategy_name):
            from shared.configurable_hyperopt import ConfigurableHyperoptOptimizer
            return ConfigurableHyperoptOptimizer(
                hyperopt_config=hyperopt_config,
                strategy_name=strategy_name,
            )
        return factory

    # Backtest ports (E2.T4b). The backtester is exposed as a
    # request-parameterized factory callable (capital/fee/slippage come from the
    # CLI surface, not settings), and the strategy provider is an offline-safe
    # adapter that loads + execution-intent-wraps strategy functions. Both import
    # lazily so resolve_all() (offline smoke) stays light.

    def _build_backtester_factory(self):
        def factory(initial_capital, fee_rate, slippage_factor):
            from infrastructure.backtest.realistic_backtester import RealisticBacktester
            return RealisticBacktester(
                initial_capital=initial_capital,
                fee_rate=fee_rate,
                slippage_factor=slippage_factor,
            )
        return factory

    def _build_backtest_strategy_provider(self):
        from infrastructure.backtest.strategy_provider import BacktestStrategyProvider
        return BacktestStrategyProvider()

    # Portfolio/risk validation analytics ports (E2.T4b). Each is a callable that
    # lazily imports + delegates to its infrastructure function, so resolve_all()
    # (offline smoke) never imports the heavy risk/portfolio modules; they load
    # only when a validation pipeline actually invokes the port.

    def _build_capital_allocator_factory(self):
        def factory(*args, **kwargs):
            from infrastructure.portfolio.capital_allocator import create_capital_allocator_from_backtest_results
            return create_capital_allocator_from_backtest_results(*args, **kwargs)
        return factory

    def _build_monte_carlo_analyzer(self):
        def analyzer(*args, **kwargs):
            from infrastructure.risk.monte_carlo_simulator import run_monte_carlo_analysis_from_backtest_results
            return run_monte_carlo_analysis_from_backtest_results(*args, **kwargs)
        return analyzer

    def _build_kill_switch_factory(self):
        def factory(*args, **kwargs):
            from infrastructure.risk.strategy_kill_switch import create_kill_switch_from_backtest_results
            return create_kill_switch_from_backtest_results(*args, **kwargs)
        return factory

    def _build_portfolio_walk_forward_validator(self):
        def validator(*args, **kwargs):
            from infrastructure.backtest.portfolio_walk_forward_validator import run_portfolio_walk_forward_validation_from_backtest_results
            return run_portfolio_walk_forward_validation_from_backtest_results(*args, **kwargs)
        return validator

    # Historical-data-sync ports (E2.T4c). The historical-data provider is
    # network/broker-backed (its constructor builds broker adapters), so it is
    # exposed as a zero-arg factory callable that imports + constructs lazily;
    # resolve_all() (offline smoke) therefore only resolves the callable and
    # never instantiates brokers. The CSV loader is request-parameterized by the
    # sync flow's derived base path, so it is exposed as a factory taking
    # base_path. Construction logic mirrors the legacy runner byte-for-byte.

    def _build_historical_data_provider_factory(self):
        settings = self.settings

        def factory():
            from infrastructure.data.configurable_historical_data_provider import ConfigurableHistoricalDataProvider
            fallback_sources_raw = settings.data.historical_data_fallback_sources if settings.data and settings.data.historical_data_fallback_sources else 'binance,mexc,phemex'
            if isinstance(fallback_sources_raw, list):
                fallback_sources = fallback_sources_raw
            else:
                fallback_sources = fallback_sources_raw.split(',')
            return ConfigurableHistoricalDataProvider(
                settings=settings,
                preferred_data_source=settings.data.preferred_historical_data_source if settings.data and settings.data.preferred_historical_data_source else 'binance',
                fallback_sources=fallback_sources,
            )
        return factory

    def _build_historical_csv_loader_factory(self):
        def factory(base_path):
            from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
            return CSVHistoryLoaderAdapter(base_path=base_path)
        return factory

    # Shadow-deployment ports (E2.T5.1). All three are exposed as callables that
    # import + construct lazily, so resolve_all() (offline smoke) only resolves
    # the callables and never loads the strategy/KPI infrastructure. Construction
    # mirrors the legacy runner byte-for-byte (default CSV loader base path).

    def _build_shadow_strategy_provider(self):
        def provider():
            from infrastructure.portfolio.comprehensive_portfolio_backtester import load_sample_strategies
            return load_sample_strategies()
        return provider

    def _build_shadow_csv_loader_factory(self):
        def factory():
            from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
            return CSVHistoryLoaderAdapter()
        return factory

    def _build_shadow_kpi_reporter(self):
        def reporter(current_metrics, baseline_metrics):
            from infrastructure.monitoring.shadow_kpi_monitor import generate_shadow_kpi_report
            return generate_shadow_kpi_report(
                current_metrics=current_metrics,
                baseline_metrics=baseline_metrics,
            )
        return reporter

    # Non-production trading-mode ports (E2.T5.2). Each is a factory callable that
    # imports + constructs lazily, so resolve_all() (offline smoke) only resolves
    # the callables (the optimize/retune pipelines pull hyperopt, which is built
    # only when a mode actually runs). Construction mirrors the legacy runner
    # byte-for-byte.

    def _build_legacy_backtest_use_case_factory(self):
        def factory(strategy_name):
            from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
            from infrastructure.backtest.backtest_adapters import (
                MockHistoricalDataProviderAdapter, BasicBacktestEngineAdapter,
                BacktestMetricsCalculatorAdapter,
            )
            from application.services.backtest_services import BacktestExecutionService
            from application.use_cases.backtest_use_cases import RunBacktestUseCase

            risk_manager = EnterpriseRiskManager(
                max_portfolio_exposure=100000,
                max_position_exposure=50000,
                max_risk_per_trade=0.01,
                max_daily_loss_pct=0.05,
                max_drawdown_pct=0.15
            )
            historical_data_provider = MockHistoricalDataProviderAdapter()
            backtest_engine = BasicBacktestEngineAdapter(
                strategy=strategy_name,
                risk_manager=risk_manager,
                historical_data_provider=historical_data_provider
            )
            metrics_calculator = BacktestMetricsCalculatorAdapter()
            backtest_service = BacktestExecutionService(
                backtest_engine_port=backtest_engine,
                historical_data_port=historical_data_provider,
                metrics_port=metrics_calculator
            )
            return RunBacktestUseCase(backtest_service)
        return factory

    def _build_hyperopt_config_factory(self):
        def factory(strategy_name):
            from shared.configurable_hyperopt import HyperoptConfig
            return HyperoptConfig(strategy_name=strategy_name)
        return factory

    def _build_auto_retune_optimizer_factory(self):
        def factory(strategy_name, performance_threshold):
            from infrastructure.optimization.auto_retune_hyperopt import AutoRetuneOptimizer
            return AutoRetuneOptimizer(
                strategy_name=strategy_name,
                performance_threshold=performance_threshold,
            )
        return factory

    # Production + auto-detect orchestrator ports (E2.T5.3). The wiring below was
    # moved verbatim out of run_trading_system.run_production_orchestrator / the
    # auto-detect CLI branch. Both factories build (but do NOT initialize/run) the
    # orchestrator. They go through the SAME broker_registry singleton, so there is
    # exactly one execution service per process and no duplicate broker sessions.
    # Imports are lazy (invoked only when production actually runs), keeping
    # resolve_all() offline-safe.

    def _build_production_data_and_services(self):
        """Shared wiring for production + auto-detect (broker_registry singleton)."""
        from bootstrap.settings.loaders import load_settings
        settings = load_settings()

        # Container-mediated access (E2.T6). broker_registry is a process singleton,
        # so this returns the one shared registry and avoids duplicate broker sessions.
        broker_registry = self.resolve("broker_registry")

        # Create execution service first using the registry to avoid duplicate initialization
        execution_service = broker_registry.get_execution_service(
            settings=settings,
            use_multi_broker=True,
            primary_broker='bingx'
        )
        # Enhanced data provider (real data, can download missing symbols); binance
        # primary to avoid BingX rate limits, with fallbacks.
        historical_data_source = (
            settings.data.preferred_historical_data_source
            if settings.data and hasattr(settings.data, 'preferred_historical_data_source')
            else 'binance'
        )
        market_data_repo = broker_registry.get_historical_data_provider(
            settings=settings,
            csv_base_path=None,
            download_enabled=True,
            broker_service=execution_service,
            historical_data_source=historical_data_source,
            fallback_sources=['mexc', 'phemex', 'bingx']
        )
        from infrastructure.portfolio.portfolio_adapters import EqualWeightPortfolioAdapter
        from infrastructure.optimization.advanced_optimization_service import AdvancedOptimizationService
        portfolio_service = EqualWeightPortfolioAdapter()
        optimization_service = AdvancedOptimizationService()

        # Paper-trading fill engine (E11): wire into the LIVE_EXECUTION_GUARD so PAPER-routed
        # orders are actually filled (positions / realized+unrealized PnL / equity) and
        # persisted, instead of returning a bare synthetic id. Filling only ever happens for
        # a PAPER decision, so this is inert in live/testnet routing.
        try:
            from shared.live_execution_guard import live_execution_guard
            from infrastructure.execution.paper_trading_engine import PaperTradingEngine
            from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
            from infrastructure.risk.risk_enforcement import RiskEnforcement
            bt = settings.backtest
            self._paper_engine = PaperTradingEngine(
                initial_capital=getattr(bt, "initial_capital", 10000.0),
                fee_rate=getattr(bt, "fee_rate", 0.001),
                slippage_factor=getattr(bt, "slippage_factor", 0.0005),
                persist_path=self._path("paper_state.json"),
            )
            # Risk enforcement on EVERY order path (E11 Priority 2): the guard consults the
            # portfolio risk engine before any fill/send; fills feed exposure back so the
            # engine's existing limits become enforceable. No risk thresholds are changed.
            self._risk_enforcement = RiskEnforcement(EnterpriseRiskManager())
            live_execution_guard.set_risk_enforcer(self._risk_enforcement.enforce)
            live_execution_guard.set_risk_state_provider(self._risk_enforcement.state)

            def _paper_fill_and_account(order):
                result = self._paper_engine.simulate_fill(order)
                try:
                    if isinstance(result, dict) and result.get("filled"):
                        self._risk_enforcement.register_fill(order, float(result["fill_price"]))
                except Exception:
                    pass
                return result

            live_execution_guard.set_paper_fill_handler(_paper_fill_and_account)
        except Exception:
            pass  # paper-fill / risk wiring must never block composition

        return execution_service, market_data_repo, portfolio_service, optimization_service

    def _build_production_orchestrator_factory(self):
        def factory():
            from infrastructure.orchestrators.production_trading_orchestrator import ProductionTradingOrchestrator
            execution_service, market_data_repo, portfolio_service, optimization_service = \
                self._build_production_data_and_services()
            return ProductionTradingOrchestrator(
                market_data_repo=market_data_repo,
                execution_service=execution_service,
                portfolio_service=portfolio_service,
                optimization_service=optimization_service
            )
        return factory

    def _build_auto_detection_orchestrator_factory(self):
        def factory(symbols, risk_config, comprehensive_logging):
            from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
            execution_service, market_data_repo, portfolio_service, optimization_service = \
                self._build_production_data_and_services()
            return AutoDetectionOrchestrator(
                settings=self.settings,
                market_data_repo=market_data_repo,
                execution_service=execution_service,
                portfolio_service=portfolio_service,
                optimization_service=optimization_service,
                symbols=symbols,
                risk_config=risk_config,
                comprehensive_logging=comprehensive_logging
            )
        return factory

    # Retired global singletons (E2.T6). The container is now the canonical
    # creation point. ``resolve`` caches per container, so each container holds a
    # single instance for its lifetime and two containers get INDEPENDENT state.
    #
    # broker_registry / global_rate_limiter / pending_orders_tracker are
    # deliberate process-wide safety singletons (one execution service per run,
    # shared API rate budget, cross-broker duplicate-trade prevention). Their
    # classes enforce a process singleton via ``__new__``/class state, so the
    # container mediates ACCESS without breaking that guarantee.

    def _build_strategy_manager(self):
        from infrastructure.strategies.strategy_manager import StrategyManager
        return StrategyManager()

    def _build_engine_service(self):
        from infrastructure.engines.engine_service import EngineService
        return EngineService()

    def _build_engine(self):
        # Canonical EnginePort (E3.T7.1): pure-delegation adapter over the
        # container's engine_service. No new singleton — reuses the resolved one.
        from infrastructure.engines.engine_port_adapter import EngineServiceAdapter
        return EngineServiceAdapter(self.resolve("engine_service"))

    def _build_fusion_service(self):
        from infrastructure.fusion.fusion_service import FusionService
        return FusionService()

    def _build_regime_detector(self):
        from infrastructure.market_regime.regime_detector import RegimeDetector
        return RegimeDetector()

    def _build_broker_registry(self):
        from infrastructure.services.broker_registry import BrokerRegistry
        return BrokerRegistry()

    def _build_global_rate_limiter(self):
        from shared.rate_limiter import GlobalRateLimiter
        return GlobalRateLimiter()

    def _build_pending_orders_tracker(self):
        from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
        return PendingOrdersTracker()

    def _build_portfolio_allocation_engine(self):
        from infrastructure.risk.portfolio_allocation_engine import PortfolioAllocationEngine
        return PortfolioAllocationEngine()

    def _build_position_sizing_engine(self):
        from application.position_sizing.enterprise_position_sizing import PositionSizingService
        from infrastructure.position_sizing.position_sizing_engine_adapter import (
            PositionSizingEngineAdapter,
        )
        allocation_engine = self.resolve("portfolio_allocation_engine")
        settings = self.resolve("settings") if "settings" in self.registered_keys() else None
        risk_cfg = getattr(settings, "risk", None) if settings else None
        allocation_config = getattr(risk_cfg, "portfolio_allocation", None) if risk_cfg else None
        return PositionSizingEngineAdapter(
            service=PositionSizingService(),
            allocation_engine=allocation_engine,
            allocation_config=allocation_config,
        )

    def _build_risk_engine(self):
        from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
        from infrastructure.risk.risk_engine_adapter import ConsolidatedRiskEngineAdapter
        return ConsolidatedRiskEngineAdapter(risk_manager=EnterpriseRiskManager())

    def _build_tracking(self):
        # Reuse the container's configured ResultsTracker so the consolidated
        # tracking system writes to the same DB/storage paths (persistence format
        # preserved). Trade + shadow-KPI trackers use their canonical defaults.
        from infrastructure.tracking.tracking_adapter import ConsolidatedTrackingAdapter
        return ConsolidatedTrackingAdapter(results_tracker=self.resolve("results_tracker"))

    def _build_logging(self):
        from infrastructure.monitoring.logging_adapter import LoggingAdapter
        return LoggingAdapter()

    def _build_message_bus(self):
        from infrastructure.messaging.message_bus_adapter import MessageBusAdapter
        return MessageBusAdapter()

    # Statistical-validation services (E3.T9). Each is the canonical implementation
    # behind its port in domain/ports/statistical_validation_ports.py. Construction
    # is parameterless and offline-safe (numpy/scipy/sklearn only, no I/O); local
    # imports keep resolve_all() light. No scoring formula is altered.

    def _build_confidence_calibrator(self):
        from infrastructure.statistical_validation.confidence_calibrator import ConfidenceCalibrator
        return ConfidenceCalibrator()

    def _build_randomness_firewall(self):
        from infrastructure.statistical_validation.randomness_exposure_firewall import RandomnessExposureFirewall
        return RandomnessExposureFirewall()

    def _build_statistical_authority_engine(self):
        from infrastructure.statistical_validation.statistical_authority_engine import StatisticalAuthorityScoreEngine
        return StatisticalAuthorityScoreEngine()

    def _build_statistical_historical_data_tracker(self):
        from infrastructure.statistical_validation.historical_data_tracker import HistoricalDataTracker
        return HistoricalDataTracker()

    def _build_decision_defensibility_validator(self):
        from infrastructure.statistical_validation.decision_defensibility_validator import DecisionDefensibilityValidator
        return DecisionDefensibilityValidator()

    def _build_market_structure_engine(self):
        from infrastructure.market_structure.market_structure_engine import MarketStructureEngine
        return MarketStructureEngine()

    def _build_setup_engine(self):
        from infrastructure.strategies.setup_engine import SetupEngine
        return SetupEngine()

    def _build_execution_confirmation_engine(self):
        from infrastructure.execution.execution_confirmation_engine import ExecutionConfirmationEngine
        return ExecutionConfirmationEngine()

    def _build_execution_optimizer(self):
        from infrastructure.execution.execution_optimizer import ExecutionOptimizer
        return ExecutionOptimizer()

    def _build_decision_pipeline(self):
        from infrastructure.strategies.decision_pipeline import DecisionPipeline
        return DecisionPipeline(
            confirmation_engine=self.resolve("execution_confirmation_engine"),
            optimizer=self.resolve("execution_optimizer")
        )
