# Phase 2 — Target Architecture & Clean System Design

**Repository:** Lynxion ETS (Enterprise Trading System)
**Scope:** Design only. No implementation code. Builds directly on `phase1-codebase-audit-report.md`.
**Goal:** A clean, modular, scalable hexagonal architecture that eliminates the duplication and the bidirectional `application ↔ infrastructure` coupling found in Phase 1.

> Design principles applied throughout: **Dependencies point inward** (Clean/Hexagonal), **one source of truth per concept**, **composition at the edge** (wiring lives only in the entry layer), **inject config — never import a global singleton**.

---

## 0. What Phase 1 Told Us (the problems this design must solve)

| # | Phase 1 finding | Target-architecture remedy |
|---|---|---|
| P1 | Bidirectional `application ↔ infrastructure` cycle (62 cross-imports) | One-way dependency rule, enforced in CI by an import-linter contract (§4, §6) |
| P2 | `Configs` global singleton imported by every layer (incl. domain-adjacent + shared) | Typed, immutable **settings objects injected** from the composition root; no module ever imports a global config (§3, §4) |
| P3 | Composition root (`main_hexagonal_container.py`) exists but is bypassed; 13 runners hand-wire | A single **`bootstrap/` composition root**; runners/CLI/API call it and nothing else wires services (§2, §3) |
| P4 | 10+ mutable global singletons; broken test isolation | Singletons replaced by **container-scoped instances**; lifecycle owned by bootstrap (§3, §5) |
| P5 | 4–5 backtesters, 5–6 data providers, position sizing in 4 places | **One port + one canonical adapter** per capability; variants become strategies behind that port (§1, §2) |
| P6 | Duplicate entities/enums + `shared/types.py` shadow model | Single canonical domain model; `shared/types` deleted; value objects enforced (§3) |
| P7 | 17 god modules >700 LOC mixing concerns | Split along the **engine → fusion → strategy → risk → execution** seams; each module one responsibility (§3) |
| P8 | Broad-but-shallow tests, no CI/pytest config | **Test pyramid per layer** + pytest config + import-contract test + CI gate (§3, §5) |
| P9 | Matplotlib/visualization & "API"-style logic mixed into application | New **`interface/` (presentation/entry) layer**; reporting/plotting lives there, not in use cases (§2, §3) |

---

## 1. Target Architecture Overview

The system stays **hexagonal (Ports & Adapters)**, but the rules become *enforced* rather than aspirational. Four concentric rings, plus a thin outer entry layer:

```
                 ┌──────────────────────────────────────────────────────┐
                 │                  interface/ (entry)                    │
                 │   CLI runners · REST API · schedulers · dashboards     │
                 └───────────────▲──────────────────────▲────────────────┘
                                 │ calls                 │ builds graph
                 ┌───────────────┴───────┐   ┌───────────┴───────────────┐
                 │     bootstrap/         │   │      application/          │
                 │  (composition root,    │──▶│  use cases · orchestration │
                 │   DI wiring, settings) │   │  (depends on PORTS only)   │
                 └───────────────┬────────┘   └───────────┬────────────────┘
                                 │ instantiates           │ depends on
                                 ▼                         ▼
                 ┌───────────────────────┐   ┌─────────────────────────────┐
                 │   infrastructure/      │   │          domain/            │
                 │  adapters implement    │──▶│  entities · value objects · │
                 │  domain PORTS          │   │  PORTS · domain services    │
                 └───────────────────────┘   └─────────────────────────────┘
                       (depends inward on domain ports only)

   Dependency arrows ALL point inward → domain.  Nothing points outward from domain.
```

**Key shifts from today:**

1. **The composition root becomes the only place wiring happens.** `bootstrap/` reads settings, constructs adapters, injects them into application services, and hands a ready-to-use facade to whatever entry point asked for it (CLI runner, REST endpoint, scheduled job). This kills the 13-runners-each-wire-themselves problem (P3).

2. **`Configs` becomes injected settings, not an imported god.** A `settings/` module produces frozen, validated dataclasses. The composition root reads them once and passes them down. No infrastructure or application module imports settings directly — which removes the single biggest cause of the infra→app cycle (P1/P2).

3. **One capability = one port = one canonical adapter.** The 4–5 backtesters collapse to a `BacktestEnginePort` with one canonical engine; the "realistic/portfolio/comprehensive" variations become *configurable behaviors or strategies behind that port*. Same for data providers, position sizing, tracking, logging, and the event bus (P5/P6).

4. **The trading pipeline gets explicit module seams.** `watcher → engine → fusion → strategy → risk → position-sizing → execution → broker` each becomes a bounded module with its own port. God modules are split along these seams (P7).

5. **A new `interface/` layer** holds everything user/operator-facing: CLI runners, an optional REST API (FastAPI is already a dependency), schedulers, dashboards, and reporting/plotting. **Business logic is removed from here** — runners become thin (parse args → call bootstrap → call a use case → render result) (P9).

6. **Scaling is designed in, not bolted on.** Because adapters sit behind ports, you can later swap CSV storage for a time-series DB, the in-process event bus for Redis/Kafka, or run watchers/engines as separate workers — without touching domain or application code.

---

## 2. Proposed Folder Structure

```
lynxion/
├── pyproject.toml                  # packaging, pytest config, import-linter contracts, ruff/mypy
├── README.md
│
├── domain/                         # PURE. No I/O, no pandas-as-contract, no settings, no logging impl.
│   ├── entities/                   # ONE canonical model
│   │   ├── signal.py               # MarketObservation → InterpretedSignal → FusedSignal → ExecutionIntent
│   │   ├── order.py                # Order, Fill
│   │   ├── position.py             # Position, Portfolio
│   │   ├── market_data.py          # Candle / MarketData (typed)
│   │   └── account.py              # Balance, TradingAccount
│   ├── value_objects/              # Symbol, Money, Price, Percentage, Volume, RiskValue, Correlation
│   ├── enums/                      # SignalType, OrderSide, PositionSide, BrokerType, StrategyType, RegimeType
│   ├── events/                     # DomainEvent + concrete events (definitions only)
│   ├── services/                   # PURE domain logic (e.g. fusion math, sizing formulas, pnl, risk rules)
│   └── ports/                      # ALL interfaces (Protocols), grouped by capability
│       ├── data.py  broker.py  execution.py  backtest.py
│       ├── engine.py  fusion.py  strategy.py  watcher.py
│       ├── risk.py  portfolio.py  optimization.py  tracking.py
│       └── messaging.py  clock.py  config.py  logging.py
│
├── application/                    # Use cases & orchestration. Depends ONLY on domain (entities, VOs, ports).
│   ├── use_cases/                  # One class/function per user intent, no infra imports
│   │   ├── run_backtest.py
│   │   ├── run_walkforward.py
│   │   ├── optimize_strategy.py
│   │   ├── sync_market_data.py
│   │   ├── run_live_trading.py
│   │   └── run_shadow_deployment.py
│   ├── pipelines/                  # Orchestration of the watcher→engine→fusion→strategy→exec flow
│   ├── services/                   # Thin coordinators (NOT god services); each one capability
│   └── dto/                        # Request/response DTOs for use cases (decouple from entities at edges)
│
├── infrastructure/                 # Adapters. Implement domain ports. Depend on domain ports + 3rd-party libs.
│   ├── data/                       # ONE canonical historical/market data adapter (+ cache adapter)
│   ├── brokers/                    # binance/ bingx/ mexc/ phemex behind one BrokerPort + a router
│   ├── backtest/                   # ONE canonical backtest engine adapter
│   ├── engines/                    # signal engine adapters (trend, volatility, orderflow, ml, ...)
│   ├── fusion/                     # fusion adapters
│   ├── strategies/                 # strategy adapters (one file per strategy)
│   ├── risk/                       # risk + sl/tp + portfolio risk adapters (consolidated)
│   ├── position_sizing/            # ONE sizing adapter (algorithms = pluggable strategies)
│   ├── execution/                  # execution algorithms (twap/vwap/smart) behind ExecutionPort
│   ├── optimization/               # hyperopt/optuna adapters
│   ├── tracking/                   # ONE results/trade/kpi tracking adapter
│   ├── persistence/                # file/CSV + (future) DB repositories
│   ├── messaging/                  # event bus adapter (in-proc now; Redis/Kafka later)
│   └── monitoring/                 # forensic logging adapter, metrics exporter
│
├── interface/                      # Entry/presentation layer. Thin. No business logic.
│   ├── cli/                        # one thin module per former runner_*.py
│   │   ├── backtest.py  walkforward.py  retune.py  sync.py  live.py  shadow.py ...
│   ├── api/                        # optional FastAPI app (routers → use cases) for future scaling
│   ├── scheduler/                  # cron/scheduled jobs → use cases
│   └── reporting/                  # matplotlib/plotting/report rendering (moved out of application)
│
├── bootstrap/                      # COMPOSITION ROOT — the only place wiring happens
│   ├── container.py                # builds adapters, injects into services, returns app facade
│   ├── settings/                   # typed, frozen, validated settings (replaces Configs singleton)
│   │   ├── schema.py   loaders.py   profiles/  (dev/staging/live)
│   └── lifecycle.py                # startup/shutdown, graceful teardown of resources
│
├── shared/                         # TRULY cross-cutting, dependency-free helpers ONLY
│   ├── result.py                   # Result/Either, error types
│   ├── exceptions.py               # exception hierarchy
│   └── (small pure utils)          # NO config, NO domain types, NO event system, NO duplicate logger
│
└── tests/
    ├── unit/                       # domain + application (fast, no I/O, fakes for ports)
    │   ├── domain/  application/
    ├── integration/                # infrastructure adapters against real files/sandbox brokers
    ├── contract/                   # each adapter conforms to its port; import-linter contract test
    ├── e2e/                        # full pipelines via bootstrap (former wfo_*/verification scripts)
    ├── fixtures/                   # shared data fixtures
    └── conftest.py
```

**What disappears / merges vs. today:**

| Today | Target |
|---|---|
| `domain/` + `shared/` + `utils/` all holding domain-ish types | `domain/` is the single model; `shared/` shrinks to dependency-free helpers; `utils/` folded into `infrastructure/` or `shared/` |
| `infrastructure/risk/` **and** `infrastructure/risk_management/` | one `infrastructure/risk/` |
| `infrastructure/data/` **and** `infrastructure/data_sync/` | one `infrastructure/data/` + `infrastructure/persistence/` |
| `tracking/` + `results_tracking/` + `monitoring/` | one `infrastructure/tracking/` (+ `monitoring/` for logging/metrics only) |
| 4–5 backtesters | one `infrastructure/backtest/` engine |
| position sizing in 4 places | one `infrastructure/position_sizing/` (algorithms pluggable) |
| `application/configs/` (2 loaders + dead code) | `bootstrap/settings/` (one loader, typed, injected) |
| `main_hexagonal_container.py` + per-runner wiring | `bootstrap/container.py` only |
| `shared/types.py` shadow model | deleted |
| `shared/logger.py` + `utils/logger.py` | one logging adapter behind `LoggingPort` |
| `shared/event_system.py` + `event_bus.py` + `hexagonal_utils` bus | one messaging adapter behind `MessagingPort` |

---

## 3. Layer Responsibilities

### `domain/` — the core model and rules
**Belongs here:** entities, value objects, enums, domain events, **pure domain services** (fusion math, sizing formulas, pnl, risk-rule evaluation), and **ports (interfaces)**. Everything is deterministic and in-memory.
**Must NOT be here:** pandas/ccxt/redis/requests imports as part of contracts; any settings/`Configs` access; logging implementations; file/network/db I/O; framework code. (Phase 1 found `import pandas` in `domain/engines` and `domain/ports/optimization_ports` — those signatures move to application/infrastructure DTOs.)

### `application/` — use cases & orchestration
**Belongs here:** use-case classes (one per user intent), the trading **pipeline orchestration**, thin coordinating services, and request/response **DTOs**. Depends **only** on `domain` (entities, value objects, ports).
**Must NOT be here:** imports from `infrastructure`; concrete adapters; matplotlib/plotting; HTTP/CLI parsing; direct file/network access; global singletons. (Today's 29 application→infrastructure imports and the matplotlib visualizer all leave this layer.)

### `infrastructure/` — adapters & implementations
**Belongs here:** classes that **implement domain ports** — brokers, data providers, backtest engine, signal engines, fusion, strategies, risk, sizing, execution, optimization, tracking, persistence, messaging, logging, monitoring. May use any third-party library.
**Must NOT be here:** imports from `application` or `interface` (Phase 1's 33 infra→application imports, mostly `Configs`, are eliminated — adapters receive their settings via constructor injection); business orchestration; cross-adapter god objects.

### `interface/` — entry / presentation
**Belongs here:** CLI runners (thin), optional FastAPI routers, schedulers, dashboards, and **all reporting/plotting**. Each entry point: parse input → ask `bootstrap` for the wired facade/use case → invoke it → render output.
**Must NOT be here:** business logic, wiring/DI (delegated to `bootstrap`), or direct adapter construction.

### `bootstrap/` — composition root
**Belongs here:** the DI container/builder, **typed settings** (the `Configs` replacement), and lifecycle (startup/shutdown, resource teardown). This is the **only** place that knows which adapter implements which port and reads configuration.
**Must NOT be here:** business logic or algorithms; it only assembles and hands back ready objects.

### `shared/` — cross-cutting, dependency-free
**Belongs here:** `Result`/error types, the exception hierarchy, and tiny pure helpers used everywhere.
**Must NOT be here:** domain types (no shadow model), config, logging implementations, event systems, or anything that imports another layer.

### `tests/`
Unit (domain/application with port fakes) · integration (adapters) · **contract** (adapter ↔ port conformance + the import-linter contract) · e2e (full pipelines via bootstrap). Pytest config + CI gate live in `pyproject.toml`.

---

## 4. Dependency Rules

**The one rule:** *dependencies point inward.* Concretely, allowed import directions:

```
interface  ──▶  bootstrap  ──▶  application  ──▶  domain
    │                │                              ▲
    └────────────────┴────────▶ infrastructure ─────┘   (infrastructure ──▶ domain.ports only)
```

| Rule | Allowed | Forbidden |
|------|---------|-----------|
| R1 | `interface → bootstrap`, `interface → application` (use cases), `interface → domain` (DTOs/types) | `interface → infrastructure` (no direct adapter use) |
| R2 | `application → domain` (entities, VOs, **ports**) | `application → infrastructure`, `application → interface`, `application → bootstrap` |
| R3 | `infrastructure → domain` (**ports + entities/VOs only**) | `infrastructure → application`, `infrastructure → interface`, `infrastructure → bootstrap` |
| R4 | `bootstrap → everything` (it is the composition root) | nothing imports `bootstrap` except `interface` |
| R5 | `domain → (nothing but stdlib + shared)` | `domain → application/infrastructure/interface`, `domain → pandas/ccxt/redis` in contracts, `domain → settings` |
| R6 | everyone may use `shared` | `shared →` any other layer |

**Concrete corollaries that fix Phase 1:**
- **Domain must not depend on infrastructure** (R5). pandas-typed signatures move out of `domain`.
- **Configuration is injected, never imported** (R2/R3). No module does `from application.configs import Configs`. Settings are constructed in `bootstrap` and passed into adapters/services via constructors. This single rule removes the infra→app cycle.
- **No global singletons** — instances are created once by the container and shared by reference, giving the same single-instance benefit *with* test isolation (each test builds its own container).
- **One port per capability**; multiple implementations are fine but must all satisfy the same port and be selected in `bootstrap`.

**Enforcement (not just convention):**
- Add **import-linter** contracts in `pyproject.toml` encoding R1–R6; run in CI so a violating import fails the build.
- A `tests/contract/test_layering.py` asserts the same, so violations surface locally too.
- `mypy` in strict mode on `domain/` and `application/` to keep them pure and typed.

---

## 5. Migration Strategy

Incremental and **always-green** — the system keeps running at every step. No big-bang rewrite. Suggested sequence (each step is independently shippable):

**Step 0 — Safety net first.**
- Add `pyproject.toml` with pytest config; make the existing `tests/` runnable under `pytest` (no behavior change). Add CI to run them. Pin current behavior of the *one* backtester and *one* data path you intend to keep as canonical with characterization tests (capture current outputs as golden files). This protects the later consolidation (addresses P8 before refactoring).

**Step 1 — Introduce `bootstrap/settings/` and break the `Configs` cycle (highest leverage).**
- Create typed, frozen settings objects. Have the existing `Configs` *read from* them temporarily (adapter shim) so nothing breaks.
- Then, file-by-file, replace `from application.configs import Configs` with **constructor-injected settings**, starting with the ~33 infrastructure files. Each conversion removes one infra→app edge. When the last one is gone, delete the back-edge. This alone resolves P1/P2 and is the single most valuable move.

**Step 2 — Stand up the composition root.**
- Build `bootstrap/container.py` that wires the *current* adapters/services. Point **one** runner at it (e.g. `runner_backtest`) as a pilot. Validate identical results via the golden files. Then migrate the other 12 runners one at a time to call `bootstrap` instead of hand-wiring (fixes P3/P4).

**Step 3 — Consolidate duplicates behind single ports (one capability at a time).**
- For each duplicated capability (backtesters → data providers → position sizing → tracking → logger → event bus): define/confirm the port, choose the canonical implementation, route everything through it, then delete the losers. Variant behavior (realistic/portfolio/comprehensive) becomes config or pluggable strategy. Golden tests guard each deletion (fixes P5).

**Step 4 — Unify the domain model.**
- Merge `trading_entities` + `signal_entities` into one canonical `domain/entities` set; delete `shared/types.py`; enforce value objects. Update imports mechanically. Add mypy-strict to lock it (fixes P6).

**Step 5 — Carve out `interface/` and split god modules.**
- Move CLI runners into `interface/cli/` as thin shells; move the matplotlib visualizer and any reporting into `interface/reporting/`.
- Split the 17 god modules along the pipeline seams (watcher/engine/fusion/strategy/risk/execution), extracting pure logic down into `domain/services` and orchestration up into `application/pipelines`. Do the largest/most-changed first (`realistic_backtester`, `market_opportunity_watcher`, `auto_detection_orchestrator`) (fixes P7/P9).

**Step 6 — Enforce the rules permanently.**
- Turn on import-linter contracts (R1–R6) and the layering contract test in CI. From here, the architecture cannot silently regress. Backfill unit tests per layer to climb the test pyramid (fixes P8 durably).

**Step 7 — Scale-readiness (optional, enabled by the above).**
- With ports in place: swap CSV persistence for a time-series DB behind the persistence port; swap the in-proc event bus for Redis/Kafka behind `MessagingPort`; run watchers/engines as separate processes/workers — all without touching `domain` or `application`.

**Sequencing rationale:** settings/cycle first (unblocks everything and stops the bleeding), then composition root (centralizes control), then de-duplication (shrinks the surface), then model + structure (cleanliness), then enforcement (prevents regression). Each step is reversible and leaves the system shippable.

---

## Summary

The target is the **same hexagonal architecture the project already aspires to — but enforced**: one inward-pointing dependency direction, configuration injected from a single composition root instead of a global singleton, one port + one canonical adapter per capability, a thin entry/presentation layer separated from business logic, and CI-enforced import contracts so the structure cannot rot again. The migration is incremental and test-guarded, beginning with the settings/`Configs` cycle break that yields the most architectural value for the least risk.

*(Design only, per task scope — no implementation code written.)*
