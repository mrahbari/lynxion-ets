# Phase 1 — Layer Report 1: Domain & Shared/Utils

> Detailed exploration report (read-only audit) covering `domain/`, `shared/`, `utils/`.
> Feeds into `phase1-codebase-audit-report.md`.

---

## 1. MODULE BREAKDOWN

### DOMAIN LAYER

**Entities** (`domain/entities/`)
- `trading_entities.py` (188 LOC) — Legacy entity definitions: Signal, Order, Fill, Position, Portfolio, MarketData, Balance, TradingAccount; duplicates enums and entities found in signal_entities.py
- `signal_entities.py` (246 LOC) — Refined signal flow entities: MarketObservation, InterpretedSignal, FusedSignal, ExecutionIntent, Order, Fill, Position, Portfolio, MarketData, Balance, TradingAccount; mirrors trading_entities but with architectural layer semantics
- `engine_entities.py` (44 LOC) — EngineResult dataclass for engine computation output (score + signal)
- `__init__.py` (16 LOC) — Exports trading_entities definitions only

**Value Objects** (`domain/value_objects/`)
- `money.py` (154 LOC) — Symbol, Money, Percentage, Price, Volume, RiskValue, Correlation; immutable frozen dataclasses with validation

**Enums** (`domain/enums/`)
- `broker_enum.py` (36 LOC) — BrokerType enum with helpers (get_supported_types, from_string, get_display_name)
- `strategy_type.py` (20 LOC) — StrategyType enum listing 11 strategy variants

**Events** (`domain/events/`)
- `__init__.py` (107 LOC) — EventType enum and event classes: DomainEvent (base), SignalGeneratedEvent, OrderPlacedEvent, OrderFilledEvent, PositionOpenedEvent, PositionClosedEvent, RiskViolationEvent, PortfolioRebalancedEvent, StrategyChangedEvent

**Ports** (`domain/ports/` — 10 files, 838 LOC total)
- `engine_ports.py` (249 LOC) — SignalPort, OrderManagementPort, MarketDataPort, PositionManagementPort, RiskManagementPort, EnginePort, ObservationProcessorPort, StrategyPort, FusionPort, RiskGovernorPort, BrokerPort, DataProviderPort
- `strategy_ports.py` (55 LOC) — StrategyPort, StrategyManagerPort
- `broker_ports.py` (76 LOC) — BrokerPort, BrokerAdapterManagerPort
- `data_ports.py` (50 LOC) — DataProviderPort, DataCachePort, DataAggregatorPort
- `optimization_ports.py` (116 LOC) — IOptimizableStrategy, IParameterSpace, IHyperoptObjective, IStrategyRegistry, IDataLoader, IMetricCalculator, IOptimizationService (ABC-based)
- `backtest_ports.py` (43 LOC) — BacktestEnginePort, HistoricalDataProviderPort, BacktestMetricsPort
- `execution_ports.py` (41 LOC) — ExecutionPort, ExecutionAlgorithmPort
- `portfolio_ports.py` (40 LOC) — PortfolioManagementPort, PositionSizingPort, PortfolioOptimizationPort
- `watcher_ports.py` (32 LOC) — WatcherPort
- `sync.py` (74 LOC) — SymbolConfigRepository, FileRepository, DataDownloader
- `trading_ports.py` (16 LOC) — Re-exports from engine_ports.py

**Sync** (`domain/sync/`)
- `entities.py` (55 LOC) — SymbolSyncConfig, SyncJob, GapRange, FileIndex, SyncCycleReport

### SHARED LAYER (~4,371 LOC)
- `event_system.py` (604) — EventRouter, SignalEvent; routing Watcher→Engine→Fusion→Strategy→Broker
- `logger.py` (478) — EnhancedLogger with correlation IDs, log sampling, colored output
- `configurable_hyperopt.py` (451) — Hyperparameter optimization wrapper
- `auto_drop_engine.py` (412) — Auto-drop logic for engine management
- `signal_correlation_analyzer.py` (304) — Signal correlation analysis
- `signal_lineage_tracker.py` (294) — Signal source tracking across layers
- `optimization_service.py` (282) — Optimization service implementation
- `hexagonal_utils.py` (258) — HexagonalEventBus, DomainEventHandler, LoggerInterface, EventInterface protocols
- `config_manager.py` (234) — Configuration management
- `experiment_tracking.py` (185) — Experiment tracking and metrics
- `circuit_breaker.py` (155) — Circuit breaker pattern
- `utils.py` (140) — generate_client_order_id, normalize_symbol, pnl_calculation, format_price_for_api
- `exceptions.py` (139) — TradingException hierarchy (Data/Risk/Execution/Connectivity/Validation/Configuration/System)
- `metrics.py` (134) — Performance metrics computation
- `rate_limiter.py` (120) — Rate limiting
- `types.py` (86) — Duplicated simple dataclasses (MarketData, Signal, Order, Fill, Position, Balance)
- `event_bus.py` (58) — Event bus implementation
- `redis_client.py` (34) — Redis client wrapper

### UTILS LAYER (~1,351 LOC)
- `profitability_enhancer.py` (532) — Variance reduction, expectancy compounding, signal filtering, capital efficiency (God object)
- `data_integrity_report.py` (211) — Data validation and integrity reporting
- `logger.py` (196) — Duplicate logging setup (parallel to shared/logger.py)
- `data_integrity_checker.py` (190) — Data quality validation
- `config_helper.py` (147) — Configuration helpers
- `symbol_validator.py` (75) — Symbol validation using domain.value_objects.Symbol

---

## 2. PORTS (INTERFACES)

**Protocol-based** (modern): SignalPort, OrderManagementPort, MarketDataPort, PositionManagementPort, RiskManagementPort, EnginePort, ObservationProcessorPort, StrategyPort, FusionPort, RiskGovernorPort, BrokerPort, DataProviderPort, ExecutionPort, ExecutionAlgorithmPort, PortfolioManagementPort, PositionSizingPort, PortfolioOptimizationPort, WatcherPort, BrokerAdapterManagerPort, DataCachePort, DataAggregatorPort.

**ABC-based** (older, optimization): IOptimizableStrategy, IParameterSpace, IHyperoptObjective, IStrategyRegistry, IDataLoader, IMetricCalculator, IOptimizationService.

**Sync (ABC)**: SymbolConfigRepository, FileRepository, DataDownloader.

**Backtest**: BacktestEnginePort, HistoricalDataProviderPort, BacktestMetricsPort.

---

## 3. DOMAIN PURITY CHECK

| File | Line | Issue |
|------|------|-------|
| `domain/engines/engine_interface.py` | 8 | `import pandas as pd` — used in EngineInterface.compute() signature |
| `domain/ports/optimization_ports.py` | 5 | `import pandas as pd` — used in IDataLoader/IMetricCalculator returning pd.DataFrame/pd.Series |

- No imports from `application/` or `infrastructure/` in domain. ✓
- No `ccxt`/`redis`/`requests` in domain. ✓
- Domain is **NOT strictly pure**: pandas couples domain to a concrete dataframe library.

---

## 4. CODE SMELLS

**A. Entity duplication (CRITICAL):** `trading_entities.py` vs `signal_entities.py` duplicate Order, Fill, Position, Portfolio, MarketData, Balance, TradingAccount nearly identically. `Signal` exists in trading_entities but signal_entities introduces layered observations without removing it.

**B. Enum duplication:** `SignalType`, `OrderSide`, `PositionSide` defined in trading_entities.py, signal_entities.py, AND shared/types.py.

**C. Oversized files:** shared/event_system.py (604), shared/logger.py (478), shared/configurable_hyperopt.py (451), shared/auto_drop_engine.py (412), utils/profitability_enhancer.py (532, god object).

**D. Entity anemia:** trading_entities.Signal mixes fusion fields (fused_score, fused_confidence); shared/types.Signal uses raw `str`/`float` instead of VOs.

**E. Misplaced logic:** shared/utils.py `calculate_position_size()` deprecated stub returning 0.0.

**F. Layering back-edge:** `shared/event_system.py:12` → `from application.configs.configs import Configs` (shared depends on application — backwards).

**G. God object:** utils/profitability_enhancer.py (532) handles variance reduction + expectancy compounding + trade filtering + capital efficiency + signal timing.

**H. Missing VO enforcement:** shared/types.py + trading_entities.MarketData use raw float for price instead of Money/Price VOs.

---

## 5. SHARED/UTILS DUPLICATION

| Concept | Locations | Severity |
|---|---|---|
| Logging setup | shared/logger.py, utils/logger.py | HIGH |
| Event/messaging | shared/event_system.py, shared/event_bus.py, shared/hexagonal_utils.HexagonalEventBus | MEDIUM |
| Enums (SignalType/OrderSide/PositionSide) | trading_entities, signal_entities, shared/types | CRITICAL |
| Simple types (MarketData/Signal/Order/Fill/Position/Balance) | trading_entities, signal_entities, shared/types | CRITICAL |
| Optimization/profitability | shared/optimization_service, shared/configurable_hyperopt, utils/profitability_enhancer | MEDIUM |

`shared/types.py` is effectively a **shadow domain model** with raw types; `shared/exceptions.py` defines domain errors; `shared/utils.py` defines domain operations.

---

## 6. CIRCULAR IMPORTS

- **shared → application** (violation): `shared/event_system.py:12`.
- No cycles within domain itself (entities → value_objects; ports → entities + value_objects; events → entities). ✓
- Duplicate ports exported: StrategyPort (engine_ports + strategy_ports), BrokerPort (engine_ports + broker_ports).
