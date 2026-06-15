# Phase 3 — Task Graph: Architecture Conversion Execution Plan

**Repository:** Lynxion ETS
**Scope:** Planning only. Converts `phase1-codebase-audit-report.md` (current reality) + `phase2-target-architecture.md` (target) into a structured, incremental execution plan.
**Principle:** Every task is small, independently testable, and leaves the system shippable (always-green). No task rewrites the whole system.

---

## How to read this plan

- **9 epics**, sequenced so the highest-leverage / lowest-risk work comes first (break the `Configs` cycle before touching anything else).
- **Risk** = low / medium / high (blast radius + reversibility).
- **Validation** = the concrete check that proves the task is done and safe.
- **Dependencies** reference task IDs (e.g. `E1.T2`). A task with `none` can start immediately.
- Phase 1 problem IDs (P1–P9) are referenced so each epic traces back to a finding.

### Epic dependency graph
```
E0 (safety net)
  └─▶ E1 (settings / break Configs cycle)        ← addresses P1, P2
        └─▶ E2 (composition root)                ← addresses P3, P4
              ├─▶ E3 (consolidate duplicates)    ← addresses P5
              ├─▶ E4 (unify domain model)        ← addresses P6
              │     └─▶ E5 (interface + split god modules) ← addresses P7, P9
              └─────────▶ E6 (enforce rules + test pyramid) ← addresses P8
                                └─▶ E7 (scale-readiness, optional)
E8 (cleanup) runs continuously / last.
```

---

## EPIC E0 — Safety Net & Tooling

**Description:** Before any refactor, establish the ability to detect regressions. Make the existing 64 test files runnable under one command, add CI, and capture golden outputs for the canonical backtest + data paths that later consolidation must preserve. Addresses P8 (no CI/pytest config) *before* refactoring begins.

##### Tasks:

**E0.T1 — Add pytest + project config**
- Goal: One-command test run; central config for pytest, markers, and tool settings.
- Input: existing `tests/**`, repo root (no `pyproject.toml`/`pytest.ini` today)
- Output: `pyproject.toml` (pytest config, markers `unit`/`integration`/`e2e`/`contract`), `tests/conftest.py`
- Dependencies: none
- Risk: low
- Validation: `pytest --collect-only` discovers all existing tests with no import errors.

**E0.T2 — Make existing tests green & quarantine the flaky/broken**
- Goal: Establish a known-green baseline; mark data-dependent/integration scripts so unit runs are fast.
- Input: `tests/final_requirements_verification.py`, `tests/core_component_tests.py`, `tests/wfo_*_tests.py`, `tests/{domain,application,infrastructure,optimization}/**`
- Output: same files annotated with `@pytest.mark.integration`/`@pytest.mark.skip(reason=...)` where they need missing data
- Dependencies: E0.T1
- Risk: low
- Validation: `pytest -m "not integration"` is green; skipped tests have explicit reasons.

**E0.T3 — Add CI workflow**
- Goal: Run unit tests on every push/PR.
- Input: `pyproject.toml`
- Output: `.github/workflows/ci.yml`
- Dependencies: E0.T1, E0.T2
- Risk: low
- Validation: CI runs and passes on the baseline commit.

**E0.T4 — Characterization (golden) tests for canonical paths**
- Goal: Pin current behavior of the backtester + a data-sync path that will become canonical, so later deletions are provably output-preserving.
- Input: `infrastructure/backtest/realistic_backtester.py`, `runner_backtest.py`, `infrastructure/data/configurable_historical_data_provider.py`
- Output: `tests/e2e/test_backtest_golden.py`, `tests/fixtures/golden/*.json` (captured outputs on a fixed seed + tiny dataset)
- Dependencies: E0.T1
- Risk: medium (must isolate nondeterminism: timestamps, RNG seeds, network)
- Validation: golden test passes twice consecutively (deterministic); diff-on-change fails loudly.

---

## EPIC E1 — Settings & Breaking the `Configs` Cycle

**Description:** Replace the `Configs` global singleton (imported across all layers, the root cause of the bidirectional `application ↔ infrastructure` cycle) with typed, frozen, injected settings. This is the single highest-value epic. Addresses P1, P2.

##### Tasks:

**E1.T1 — Define typed settings schema**
- Goal: Immutable, validated settings dataclasses mirroring today's config domains.
- Input: `application/configs/configs.py`, `application/configs/enhanced_config_loader.py`, `application/configs/schemas/**`, `application/configs/profiles/{dev,staging,live}.py`
- Output: `bootstrap/settings/schema.py`, `bootstrap/settings/profiles/`
- Dependencies: E0.T1
- Risk: low (additive; nothing wired yet)
- Validation: unit test builds each profile's settings object and asserts field types/defaults.

**E1.T2 — Single settings loader (replace EnhancedConfigLoader)**
- Goal: One loader producing the schema objects from env + profile.
- Input: `application/configs/enhanced_config_loader.py`, `application/configs/env_loader.py`
- Output: `bootstrap/settings/loaders.py`
- Dependencies: E1.T1
- Risk: low
- Validation: unit test loads dev/staging/live and matches values currently returned by `Configs`.

**E1.T3 — Shim `Configs` onto new settings (compatibility bridge)**
- Goal: Make the existing `Configs` singleton read from the new loader so nothing breaks while callers migrate.
- Input: `application/configs/configs.py`
- Output: `application/configs/configs.py` (delegates internally to `bootstrap/settings`)
- Dependencies: E1.T2
- Risk: medium (touches the most-imported symbol in the codebase)
- Validation: full unit suite green; spot-check a runner produces identical config values.

**E1.T4 — Convert infrastructure files to injected settings (batched)**
- Goal: Remove `from application.configs import Configs` from the ~33 infrastructure files; pass settings via constructor instead. Do in small batches (e.g. data/, then brokers/, then fusion/logging/orchestrators, then watchers).
- Input: `infrastructure/data/*.py`, `infrastructure/brokers/multi_broker_service.py`, `infrastructure/fusion/fusion_service.py`, `infrastructure/logging/forensic_logger.py`, `infrastructure/orchestrators/auto_detection_orchestrator.py`, `infrastructure/portfolio/comprehensive_portfolio_backtester.py`, `infrastructure/services/*.py`, `infrastructure/watchers/**`, `infrastructure/data_sync/*.py`
- Output: same files, settings injected (no `application.configs` import)
- Dependencies: E1.T3, E2.T1 (container must be able to pass settings in)
- Risk: medium (many files; do per-batch with tests between)
- Validation: after each batch, `grep -rn "from application" infrastructure/` count strictly decreases; unit/golden tests stay green.

**E1.T5 — Convert remaining application/shared callers**
- Goal: Remove `Configs` imports from application services and `shared/event_system.py:12` (the shared→application back-edge).
- Input: `shared/event_system.py`, `application/services/**`, `application/walk_forward/**`
- Output: same files, settings injected
- Dependencies: E1.T4
- Risk: medium
- Validation: `grep -rn "import Configs\|configs import Configs" application shared infrastructure` returns 0 hits outside `bootstrap/`/`application/configs/`.

**E1.T6 — Delete the legacy/dead config code**
- Goal: Remove the 841-LOC dead `loader.py` and retire the `Configs` shim once no caller imports it.
- Input: `application/configs/loader.py` (dead), `application/configs/configs.py` (shim), `application/configs/hexagonal_settings.py`
- Output: deleted files; `bootstrap/settings` is sole source
- Dependencies: E1.T5
- Risk: low (verified-unused before deletion)
- Validation: `grep` confirms zero importers; full suite green; app still boots.

---

## EPIC E2 — Composition Root (`bootstrap/`)

**Description:** Create the single wiring location and migrate all 13 runners to use it instead of hand-wiring. Replace global singletons with container-scoped instances. Addresses P3, P4.

##### Tasks:

**E2.T1 — Build the container/composition root**
- Goal: One place that constructs adapters, injects settings, and exposes wired use cases/facade.
- Input: `main_hexagonal_container.py`, `application/containers/container.py`, `application/factories/trading_factories.py`
- Output: `bootstrap/container.py`, `bootstrap/lifecycle.py`
- Dependencies: E1.T2
- Risk: medium
- Validation: a smoke test builds the container and resolves every port without error.

**E2.T2 — Pilot: migrate one runner to the container**
- Goal: Prove the pattern end-to-end on the most-exercised runner.
- Input: `runner_backtest.py`
- Output: `interface/cli/backtest.py` (thin) + `application/use_cases/run_backtest.py`
- Dependencies: E2.T1, E0.T4
- Risk: medium
- Validation: golden backtest test (E0.T4) produces byte-identical results via the new path.

**E2.T3 — Migrate data/sync runners**
- Goal: Move sync/download/resync runners onto the container.
- Input: `runner_historical_data_sync.py`, `runner_history_download.py`, `runner_multitimeframe_update.py`, `runner_resync.py`, `runner_sync_approved_symbols.py`
- Output: `interface/cli/*.py` + `application/use_cases/sync_market_data.py`
- Dependencies: E2.T2
- Risk: medium
- Validation: each runner produces same files/gap-repair results on a fixture dataset.

**E2.T4 — Migrate validation/optimization runners**
- Goal: Move backtest/validation/WFO/retune runners onto the container.
- Input: `runner_comprehensive_portfolio_backtest.py`, `runner_comprehensive_validation.py`, `runner_extended_horizon_validation.py`, `runner_walkforward.py`, `runner_retune.py`
- Output: `interface/cli/*.py` + `application/use_cases/{run_walkforward,optimize_strategy}.py`
- Dependencies: E2.T2
- Risk: medium
- Validation: WFO/optimization outputs match a pinned fixture run within tolerance.

**E2.T5 — Migrate live + shadow runners**
- Goal: Move the live orchestrator and shadow deployment onto the container with proper lifecycle/shutdown.
- Input: `run_trading_system.py`, `runner_shadow_deployment.py`
- Output: `interface/cli/{live,shadow}.py` + `application/use_cases/{run_live_trading,run_shadow_deployment}.py`
- Dependencies: E2.T2, E2.T3
- Risk: high (live trading path; threading/shutdown)
- Validation: shadow/paper run completes a full cycle in a sandbox; graceful shutdown closes broker registry + pending-orders tracker (no leaked threads).

**E2.T6 — Retire global singletons → container-scoped**
- Goal: Convert `strategy_manager`, `broker_registry`, `PendingOrdersTracker`, `RateLimiter`, `engine_service`, `fusion_service`, `regime_detector` to instances owned by the container.
- Input: `infrastructure/strategies/strategy_manager.py`, `infrastructure/services/broker_registry.py`, `infrastructure/shared/pending_orders_tracker.py`, `shared/rate_limiter.py`, `infrastructure/engines/engine_service.py`, `infrastructure/fusion/fusion_service.py`, `infrastructure/market_regime/regime_detector.py`
- Output: same files with no module-level global; instances created in `bootstrap/container.py`
- Dependencies: E2.T1, and the runner migrations that consume them
- Risk: high (shared state; subtle behavior coupling)
- Validation: two containers built in one test run have independent state (proves test isolation); full suite green.

---

## EPIC E3 — Consolidate Duplicates Behind Single Ports

**Description:** Collapse each duplicated capability to one port + one canonical adapter; variant behavior becomes config/pluggable strategy. Each deletion is guarded by golden tests. Addresses P5.

##### Tasks:

**E3.T1 — One backtest engine**
- Goal: Choose `realistic_backtester` as canonical behind `BacktestEnginePort`; route portfolio/comprehensive variants through it as modes.
- Input: `infrastructure/backtest/{realistic_backtester.py,real_backtest_engine.py,realistic_backtest_engine.py}`, `infrastructure/portfolio/comprehensive_portfolio_backtester.py`, `infrastructure/validation/comprehensive_backtest_validator.py`
- Output: one `infrastructure/backtest/` engine; others deleted or reduced to thin config wrappers
- Dependencies: E0.T4, E2.T2
- Risk: high (largest file 2232 LOC; results must not drift)
- Validation: golden backtest test byte-identical; portfolio mode matches a pinned multi-symbol fixture.

**E3.T2 — One data provider + one cache**
- Goal: Single data adapter behind `DataProviderPort`; one cache; fold `data_sync/` into `data/` + `persistence/`.
- Input: `infrastructure/data/{enhanced_data_provider.py,configurable_historical_data_provider.py,csv_history_loader.py,hybrid_data_provider.py,market_data_loader.py,coin_history_service.py,data_cache.py,improved_data_cache.py}`, `infrastructure/data_sync/**`
- Output: one provider + one cache adapter; `infrastructure/persistence/`
- Dependencies: E0.T4, E2.T3
- Risk: high
- Validation: data-sync golden test (E0.T4) identical; cache hit/miss behavior unit-tested.

**E3.T3 — One position-sizing adapter (algorithms pluggable)**
- Goal: Collapse 4 sizing locations to one adapter behind `PositionSizingPort` with algorithms as strategies.
- Input: `application/position_sizing/enterprise_position_sizing.py`, `application/services/position_sizing_service.py`, `infrastructure/position_sizing/{probabilistic_position_sizer.py,advanced_position_sizing.py}`
- Output: one `infrastructure/position_sizing/` adapter + algorithm strategy set
- Dependencies: E2.T1
- Risk: medium
- Validation: per-algorithm unit tests reproduce current size outputs for fixed inputs.

**E3.T4 — One risk module**
- Goal: Merge parallel `risk/` + `risk_management/`; separate SL/TP (execution-side) from portfolio risk.
- Input: `infrastructure/risk/**`, `infrastructure/risk_management/portfolio_risk_manager.py`, `application/risk_management/enterprise_risk_manager.py`
- Output: consolidated `infrastructure/risk/` behind `RiskManagementPort`/`RiskGovernorPort`
- Dependencies: E2.T1
- Risk: high (risk controls; correctness-critical)
- Validation: kill-switch/drawdown/exposure unit tests reproduce prior decisions on fixed scenarios.

**E3.T5 — One tracking system**
- Goal: Unify `tracking/` + `results_tracking/` + `monitoring/` behind `TrackingPort`.
- Input: `infrastructure/tracking/trade_tracker.py`, `infrastructure/results_tracking/results_tracker.py`, `infrastructure/monitoring/shadow_kpi_monitor.py`
- Output: one `infrastructure/tracking/` adapter (+ `monitoring/` for logging/metrics only)
- Dependencies: E2.T1
- Risk: medium
- Validation: tracked metrics for a fixture run match prior tracker output.

**E3.T6 — One logger + one event bus**
- Goal: Single logging adapter behind `LoggingPort`; single messaging adapter behind `MessagingPort`.
- Input: `shared/logger.py`, `utils/logger.py`, `shared/event_system.py`, `shared/event_bus.py`, `shared/hexagonal_utils.py`
- Output: `infrastructure/monitoring/` logging adapter + `infrastructure/messaging/` bus adapter; duplicates deleted
- Dependencies: E1.T5 (event_system de-coupled from Configs first)
- Risk: medium
- Validation: log output format unchanged; bus delivers events in a pub/sub unit test; no callback-swallowed exceptions (errors surface).

---

## EPIC E4 — Unify the Domain Model

**Description:** Merge the two competing entity sets, delete the shadow model, enforce value objects, remove pandas from domain contracts. Addresses P6 (and the domain-purity part of the audit).

##### Tasks:

**E4.T1 — Merge entity sets into one canonical model**
- Goal: Single `domain/entities` (signal-flow + order/position/portfolio); resolve duplicates between the two files.
- Input: `domain/entities/trading_entities.py`, `domain/entities/signal_entities.py`, `domain/entities/__init__.py`
- Output: canonical `domain/entities/{signal,order,position,market_data,account}.py`
- Dependencies: none (can run parallel to E2/E3, but coordinate import updates)
- Risk: medium
- Validation: unit tests for each entity's invariants; mechanical import update compiles; suite green.

**E4.T2 — Delete the shadow model & dedupe enums**
- Goal: Remove `shared/types.py`; single home for `SignalType`/`OrderSide`/`PositionSide`.
- Input: `shared/types.py`, `domain/enums/**`
- Output: deleted shadow types; all callers point to `domain`
- Dependencies: E4.T1
- Risk: medium (many import sites)
- Validation: `grep -rn "shared.types\|from shared import types"` returns 0; suite green.

**E4.T3 — Remove pandas from domain contracts**
- Goal: Move pandas-typed signatures out of `domain`; domain speaks in entities/VOs.
- Input: `domain/engines/engine_interface.py:8`, `domain/ports/optimization_ports.py:5`
- Output: pandas confined to infrastructure/application DTOs; domain imports only stdlib + shared
- Dependencies: E4.T1
- Risk: medium
- Validation: `grep -rn "import pandas" domain/` returns 0; mypy-strict passes on `domain/`.

**E4.T4 — Enforce value objects at boundaries**
- Goal: Construct `Symbol`/`Money`/`Percentage` at adapter boundaries so raw `str`/`float` never leaks inward.
- Input: data/broker/execution adapters, use-case DTOs
- Output: VO construction at edges; typed interiors
- Dependencies: E4.T1, E4.T2
- Risk: medium
- Validation: mypy-strict on `domain/` + `application/`; a boundary unit test rejects invalid raw inputs.

---

## EPIC E5 — Interface Layer & Splitting God Modules

**Description:** Carve out the `interface/` (presentation/entry) layer, move reporting/plotting out of application, and split the 17 god modules along pipeline seams. Addresses P7, P9.

##### Tasks:

**E5.T1 — Move visualization/reporting to interface**
- Goal: Get matplotlib/plotting out of the application layer.
- Input: `application/walk_forward/visualizer.py` (528 LOC)
- Output: `interface/reporting/walkforward_report.py`
- Dependencies: E2.T4
- Risk: low
- Validation: a report renders from a fixture WFO result; no plotting import remains under `application/`.

**E5.T2 — Split `realistic_backtester` (2232 LOC)**
- Goal: Separate execution-simulation, fee/slippage, position-management, and result-tracking concerns; push pure math into `domain/services`.
- Input: canonical backtest engine (from E3.T1)
- Output: cohesive sub-modules under `infrastructure/backtest/` + `domain/services/`
- Dependencies: E3.T1
- Risk: high
- Validation: golden backtest test unchanged after each extraction.

**E5.T3 — Split `market_opportunity_watcher` (1778 LOC)**
- Goal: Separate orchestration / symbol-discovery / opportunity-detection / event-routing / init.
- Input: `infrastructure/watchers/market_opportunity_watcher.py`
- Output: focused watcher modules + orchestration moved to `application/pipelines/`
- Dependencies: E1.T4 (watchers de-Configs'd first), E2.T1
- Risk: high
- Validation: watcher emits same opportunities for a recorded market fixture.

**E5.T4 — Split `auto_detection_orchestrator` (1289 LOC)**
- Goal: Move cross-component coordination into `application/pipelines/`; orchestrator depends on ports, not concrete infra.
- Input: `infrastructure/orchestrators/auto_detection_orchestrator.py`
- Output: `application/pipelines/detection_pipeline.py` + thinned infra pieces
- Dependencies: E5.T3, E2.T6
- Risk: high
- Validation: pipeline produces same execution intents for a fixture observation stream.

**E5.T5 — Split remaining god modules (batched)**
- Goal: Bring each >700-LOC file to single-responsibility size.
- Input: `risk/advanced_sltp_manager.py`, `logging/forensic_logger.py`, `statistical_validation/decision_defensibility_validator.py`, `data/enhanced_data_provider.py`, `strategies/strategy_manager.py`, `brokers/multi_broker_service.py`, `services/broker_execution_service.py`, `fusion/fusion_service.py`, `market_regime/regime_detector.py`
- Output: focused modules; pure logic in `domain/services` where applicable
- Dependencies: relevant E3 consolidation tasks
- Risk: medium (do one file per PR)
- Validation: per-module unit tests + relevant golden test green after each split.

**E5.T6 — Thin the CLI runners**
- Goal: Ensure every `interface/cli/*.py` only parses input → calls bootstrap → invokes use case → renders.
- Input: all `interface/cli/*.py` from E2
- Output: thin CLI shells; no business logic
- Dependencies: E2.T2–E2.T5
- Risk: low
- Validation: each CLI module is small and contains no domain/infra logic (review + import-contract).

---

## EPIC E6 — Enforce Rules & Build the Test Pyramid

**Description:** Make the architecture self-defending and durably tested. Addresses P8 (durably) and locks in P1–P7.

##### Tasks:

**E6.T1 — Import-linter contracts (layering)**
- Goal: Encode dependency rules R1–R6 so violations fail CI.
- Input: final folder structure, `pyproject.toml`
- Output: import-linter config (contracts: domain pure; application→domain only; infra→domain only; nothing imports bootstrap except interface)
- Dependencies: E2–E5 substantially complete
- Risk: low
- Validation: `lint-imports` passes; deliberately adding a bad import fails it.

**E6.T2 — Layering contract test**
- Goal: Local fast feedback mirroring the CI contract.
- Input: import-linter config
- Output: `tests/contract/test_layering.py`
- Dependencies: E6.T1
- Risk: low
- Validation: test passes on clean tree, fails on an injected violation.

**E6.T3 — Adapter↔port conformance tests**
- Goal: Prove each adapter satisfies its port.
- Input: `domain/ports/**`, infrastructure adapters
- Output: `tests/contract/test_<port>_adapters.py`
- Dependencies: E3 (ports stabilized)
- Risk: low
- Validation: each canonical adapter passes the shared port test suite.

**E6.T4 — mypy-strict on domain + application**
- Goal: Keep inner layers typed and pure.
- Input: `domain/**`, `application/**`, `pyproject.toml`
- Output: mypy config + CI step
- Dependencies: E4
- Risk: low
- Validation: `mypy` clean on `domain/` and `application/`.

**E6.T5 — Backfill the unit pyramid**
- Goal: Add fast unit tests for the ~60% of infra previously untested (engines, fusion, risk, sizing, watchers, execution, shared).
- Input: consolidated adapters from E3/E5
- Output: `tests/unit/**`, `tests/integration/**`
- Dependencies: E3, E5
- Risk: low
- Validation: coverage on `domain/`+`application/` ≥ agreed threshold; CI enforces it.

---

## EPIC E7 — Scale-Readiness (Optional, enabled by E1–E6)

**Description:** With ports in place, introduce scaling seams without touching domain/application. Optional; do only when needed.

##### Tasks:

**E7.T1 — DB-backed persistence adapter**
- Goal: Swap CSV storage for a time-series DB behind the persistence port.
- Input: `infrastructure/persistence/` (file adapter)
- Output: DB adapter implementing same port
- Dependencies: E3.T2, E6.T3
- Risk: medium
- Validation: contract test passes for both file + DB adapters; golden data path unchanged.

**E7.T2 — Distributed event bus adapter**
- Goal: Replace in-process bus with Redis/Kafka behind `MessagingPort`.
- Input: `infrastructure/messaging/` (in-proc bus)
- Output: Redis/Kafka adapter
- Dependencies: E3.T6, E6.T3
- Risk: medium
- Validation: pub/sub contract test passes against the broker; e2e pipeline unaffected.

**E7.T3 — Optional REST API surface**
- Goal: Expose use cases over FastAPI (already a dependency) for remote control/monitoring.
- Input: `application/use_cases/**`, `bootstrap/container.py`
- Output: `interface/api/` routers → use cases
- Dependencies: E2, E6
- Risk: medium
- Validation: API integration tests call use cases and return expected DTOs; no business logic in routers.

**E7.T4 — Worker decomposition for watchers/engines**
- Goal: Run watchers/engines as separate processes/workers.
- Input: `application/pipelines/**`, messaging adapter
- Output: worker entry points under `interface/`
- Dependencies: E5.T3, E5.T4, E7.T2
- Risk: high
- Validation: pipeline produces identical intents whether in-proc or distributed (fixture replay).

---

## EPIC E8 — Continuous Cleanup & Decommission

**Description:** Remove dead code and old structures as they are superseded. Runs alongside other epics; finalizes last.

##### Tasks:

**E8.T1 — Delete superseded modules as replacements land**
- Goal: No parallel old/new implementations linger.
- Input: files marked superseded by E1/E2/E3/E4
- Output: deletions (only after `grep` proves zero importers)
- Dependencies: the task that supersedes each file
- Risk: low (verified-unused; reversible via VCS)
- Validation: `grep` shows zero importers before each delete; suite green after.

**E8.T2 — Fold `utils/` into the new structure**
- Goal: Distribute `utils/` contents to `infrastructure`/`shared`; drop the duplicate logger and the `profitability_enhancer` god object into proper homes.
- Input: `utils/**`
- Output: relocated modules; `utils/` removed
- Dependencies: E3.T6, E4
- Risk: low
- Validation: imports updated; suite green; `utils/` no longer referenced.

**E8.T3 — Docs & onboarding refresh**
- Goal: Update README/architecture docs to reflect the new structure.
- Input: `README.md`, `docs/**`, this plan
- Output: refreshed docs + an architecture diagram
- Dependencies: E6
- Risk: low
- Validation: a new contributor can run tests + a backtest following only the README.

---

## Sequencing & Risk Summary

| Epic | Addresses | Net risk | Why this order |
|------|-----------|----------|----------------|
| E0 Safety net | P8 | low | Must detect regressions before changing anything |
| E1 Settings/cycle | P1, P2 | medium | Highest architectural value; unblocks one-way deps |
| E2 Composition root | P3, P4 | medium–high | Centralizes control; required before consolidation |
| E3 Consolidate dupes | P5 | high (per-capability) | Big surface reduction; golden-test-guarded |
| E4 Domain model | P6 | medium | Clean core; enables mypy-strict |
| E5 Interface + god modules | P7, P9 | high | Largest files; needs ports + golden tests first |
| E6 Enforce + test | P8 | low | Locks in everything; prevents regression |
| E7 Scale-readiness | — | medium–high | Optional; pure upside once ports exist |
| E8 Cleanup | P5, P6, P10 | low | Continuous; finalizes the migration |

**Always-green guarantee:** every task lists a validation that must pass before merge; consolidation/deletion tasks are gated by the E0 golden tests so behavior cannot silently drift.

*(Planning only, per task scope — no implementation code written.)*
