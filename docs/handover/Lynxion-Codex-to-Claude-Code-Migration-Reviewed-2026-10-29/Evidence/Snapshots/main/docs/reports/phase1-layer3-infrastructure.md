# Phase 1 — Layer Report 3: Infrastructure Layer

> Detailed exploration report (read-only audit) covering `infrastructure/` (197 files).
> Feeds into `phase1-codebase-audit-report.md`.

---

## 1. MODULE BREAKDOWN (subpackages)

| Subpackage | Responsibility |
|------------|-----------------|
| `adapters/` | Top-level port adapters (broker_data, engine, signal, live_dashboard) |
| `aggregators/` | Signal aggregation dispatcher |
| `backtest/` | MULTIPLE backtester implementations (realistic, real_backtest_engine, comprehensive_portfolio) |
| `brokers/` | Multi-broker execution service + 4 exchange adapters (BingX, Binance, MEXC, Phemex) |
| `data/` | Historical data providers + CSV loaders + caching + sync engines |
| `data_sync/` | Data download/repository adapters (overlaps with `data/`) |
| `engines/` | Signal engines (trend, volatility, correlation, ML, liquidity, orderflow, regime, ATR) |
| `execution/` | Advanced execution service + smart routers (TWAP, VWAP) |
| `fusion/` | Fusion service + hierarchical + ML fusion (fusion_service 794) |
| `logging/` | Forensic logger with statistical-validation integration |
| `market_regime/` | Regime detection and classification |
| `monitoring/` | Shadow KPI monitoring service |
| `optimization/` | Hyperparameter optimization backends |
| `orchestrators/` | Auto-detection orchestrator (1289) + architecture orchestrator |
| `performance_optimization/` | Performance optimizers |
| `portfolio/` | Portfolio management + comprehensive portfolio backtester (1356) |
| `position_sizing/` | Probabilistic position sizer (681) + advanced position sizing |
| `results_tracking/` | Results tracking (694) |
| `risk/` | 8 files: advanced_sltp_manager (1353), advanced_risk_management (667), adaptive_risk_manager, capital_shock_tester, monte_carlo_simulator, multi_symbol_router, risk_adapters, strategy_kill_switch |
| `risk_management/` | portfolio_risk_manager (667) — OVERLAPS with `risk/` |
| `services/` | broker_execution_service (805) + symbol discovery/validation + trading services |
| `shared/` | Pending orders tracker (minimal) |
| `statistical_validation/` | decision_defensibility_validator (952) + confidence calibrator + randomness firewall + statistical authority engine |
| `strategies/` | strategy_manager (871) + adapters for 10+ strategy types |
| `tracking/` | trade_tracker (94 LOC) — OVERLAPS with `results_tracking/` |
| `validation/` | architecture validator + comprehensive backtest validator + execution validator + global requirements enforcer |
| `watchers/` | market_opportunity_watcher (1778!) + 13 watcher adapters + manager/factory/config/init services |

---

## 2. ADAPTER INVENTORY

**Ports implemented:** DataProviderPort (csv_loader, enhanced/configurable/hybrid providers, improved_data_cache), ExecutionPort (multi_broker, advanced_execution), EnginePort (engine_adapters, base_engine), PortfolioManagementPort, broker adapters (BingX/Binance/MEXC/Phemex).

**Adapter subfolders (11, decentralized):** `adapters/` (4), `backtest/adapters/` (3), `brokers/adapters/` (5), `data/adapters/` (5), `engines/adapters/` (11), `execution/adapters/` (5), `fusion/adapters/` (2), `portfolio/adapters/` (4), `risk/adapters/` (5), `strategies/adapters/` (13), `watchers/adapters/` (13).

**Problem:** Adapters scattered with no unified discovery — hard to map adapter→port.

---

## 3. DUPLICATION & INCONSISTENCY

**A. Risk (CRITICAL):** parallel `risk/` (8 files) vs `risk_management/` (1 file). advanced_sltp_manager + advanced_risk_management both manage SL/TP; portfolio_risk_manager duplicates drawdown/allocation limits.

**B. Data providers (CRITICAL):** enhanced_data_provider (938), configurable_historical_data_provider (691), csv_history_loader, hybrid_data_provider (89), market_data_loader (145), coin_history_service (689) — 5–6 overlapping.

**C. Data sync:** data_sync/ (downloader + file_repository adapters) overlaps data/data_sync_engine + auto_sync_service.

**D. Backtest explosion:** realistic_backtester (2232), real_backtest_engine (648), realistic_backtest_engine, comprehensive_portfolio_backtester (1356) + comprehensive_backtest_validator — 4–5 implementations.

**E. Tracking fragmentation:** tracking/trade_tracker, results_tracking/results_tracker (694), monitoring/shadow_kpi_monitor — 3 systems.

**F. Position sizing:** application + infrastructure both implement (probabilistic_position_sizer 681, advanced_position_sizing).

**G. Strategy sprawl:** 13 strategy adapters + strategy_manager (871) + strategy_adapters (686) both do selection/routing.

---

## 4. GOD MODULES (>700 LOC)

| File | LOC | Concerns mixed |
|------|------|-----------------|
| backtest/realistic_backtester.py | 2232 | Execution sim + fees/slippage + position mgmt + risk + validation + result tracking |
| watchers/market_opportunity_watcher.py | 1778 | Orchestration + symbol discovery + opportunity detection + event routing + init |
| portfolio/comprehensive_portfolio_backtester.py | 1356 | Multi-strategy backtest + correlation + risk metrics + selection + aggregation |
| risk/advanced_sltp_manager.py | 1353 | SL/TP calc + volatility norm + structure detection + regime adjust + priority exec |
| orchestrators/auto_detection_orchestrator.py | 1289 | Market monitor + detection + routing + execution intent + event coordination |
| logging/forensic_logger.py | 964 | Logging + statistical validation + traceability + audit trails |
| statistical_validation/decision_defensibility_validator.py | 952 | Stat tests + evidence scoring + audit trails + validation framework |
| data/enhanced_data_provider.py | 938 | Loading + caching + auto-download + multi-source fallback + sync coordination |
| strategies/strategy_manager.py | 871 | Lifecycle + ranking + risk adjust + regime compat + allocation |
| brokers/multi_broker_service.py | 866 | Exchange switching + availability + adapter mgmt + rate limiting |
| brokers/adapters/bingx_adapter.py | 820 | API + execution + account mgmt + websocket |
| services/broker_execution_service.py | 805 | Broker comms + orders + risk checks + position tracking + slippage |
| fusion/fusion_service.py | 794 | Weighting + scoring + correlation penalty + regime adjust + stability |
| market_regime/regime_detector.py | 789 | Classification + volatility + trend + transition detection |
| engines/adapters/engine_adapters.py | 722 | Signal processing + trend filter + confidence adjust + metadata |
| results_tracking/results_tracker.py | 694 | Result tracking + metrics + stats + persistence |
| data/configurable_historical_data_provider.py | 691 | Multi-broker fetch + source switching + rate-limit avoidance + caching |
| strategies/strategy_adapters.py | 686 | Strategy signal processing + risk integration + routing |
| position_sizing/probabilistic_position_sizer.py | 681 | Sizing + correlation + regime weighting + expectancy |

Pattern: nearly every god module mixes orchestration + business logic + infrastructure detail.

---

## 5. HEXAGONAL VIOLATIONS — `from application` IMPORTS (33 verified)

**Primary type — `Configs` singleton** in: brokers/multi_broker_service.py, data/configurable_historical_data_provider.py, data/enhanced_data_provider.py, data/hybrid_data_provider.py, data/wfo_config.py, fusion/fusion_service.py, logging/forensic_logger.py, orchestrators/auto_detection_orchestrator.py, portfolio/comprehensive_portfolio_backtester.py, services/{symbol_discovery,symbol_validation,broker_execution}_service.py, + multiple watcher files.

**Secondary types:**
- backtest/adapters/walk_forward.py:8 → application.walk_forward.sliding_window_splitter
- data_sync/file_repository_adapter.py:12 → application.data_sync.ports
- data_sync/data_downloader_adapter.py:11-12 → application.configs.sync_settings, application.configs.symbol_config
- execution/advanced_execution_service.py:11 → application.services.execution_services
- data/enhanced_data_provider.py:16 → application.data_sync.sync_manager
- data/configurable_historical_data_provider.py:157 → application.symbol_management.centralized_symbol_manager

Severity: HIGH — infrastructure depends on application config/services/logic. Combined with application's 29 imports of infrastructure → **bidirectional layer cycle**.

---

## 6. INTERNAL COUPLING

**Problematic:**
- auto_detection_orchestrator imports engine_service, fusion_service, strategy_manager, market_opportunity_watcher, architecture_orchestrator, event_router (god object).
- multi_broker_service imports advanced_risk_management, strategy_kill_switch, TelegramNotificationService, pending_orders_tracker (broker coupled to risk + notification).
- comprehensive_portfolio_backtester tightly couples to realistic_backtester.
- enhanced_data_provider imports csv_loader, downloader_adapter, file_repository_adapter, broker_service, data_cache, configurable_data_provider, sync_manager (too many siblings; data↔broker concern).

---

## 7. CIRCULAR IMPORT RISK

No hard cycles found within infrastructure, but risk patterns:
1. orchestrators/auto_detection_orchestrator → architecture_orchestrator (possible back-edge).
2. execution/advanced_execution_service → application.services.execution_services (which may reach back to infra execution).
3. brokers/multi_broker_service → risk → data → broker (indirect).

---

## 8. PROBLEM SUMMARY

| Problem | Severity |
|---------|----------|
| Application imports (infra→app) | CRITICAL |
| Backtest explosion (4–5 impls) | HIGH |
| God modules (≈19 files >700 LOC) | HIGH |
| Risk management duplication | HIGH |
| Data provider sprawl | HIGH |
| Watchers / orchestrator god modules | HIGH |
| Adapter decentralization (11 subfolders) | MEDIUM |
| Tracking fragmentation (3 systems) | MEDIUM |
| Position sizing duplication | MEDIUM |
| Broker ↔ risk coupling | MEDIUM |

Infrastructure started clean but accumulated debt by adding features without consolidating, creating new implementations instead of refactoring, allowing infra→app dependencies, and not separating orchestration / business logic / adapters.
