# E6 — Canonical Environment Specification, Validation, Resume & Allowlist Retirement

> Design artifact (uncommitted-by-default, per the docs/reports convention). Produced
> 2026-06-09 after the team accepted **Option 1: adopt the actual running environment
> as canonical**. Supersedes the stale `requirements.txt` pins (numpy 1.24.3 / pandas
> 1.5.3 / pydantic v1 / TA-Lib), which describe an environment that never existed and
> cannot run the code (`bootstrap/settings/schema.py` uses pydantic-v2 `ConfigDict`).

---

## 0. Roadmap state — FROZEN

Branch `e3-consolidation-behind-ports`. Completed & committed: E0–E2; E3 (consolidation);
E4 (closed at ingestion boundary); E5-A (T1/T9/T10/T3/T4 + T6 acceptance); E5.T5 SAFE batch
(7 god-module splits); E6.T1/T2/T3 (import-linter contracts + layering test + adapter-port
conformance); E8.T1a/T1b/T1c/T2; **E6 graph-coverage `617a70e`** (39 `__init__.py`; grimp
142→412 modules; allowlist 9→92).

Deferred/blocked before this turn: E1.T4/T5, E5-B, E6.T4, E6.T5, E8 allowlist-retirement.

---

## A. Canonical Environment Specification

**Interpreter:** CPython **3.12** (observed 3.12.3). CI pins `python-version: "3.12"`.
**Platform:** Windows (primary dev) and Linux/WSL (CI + local). cp312 wheels.

### A.1 Runtime dependencies (authoritative versions — exact, ==)

| Package | Version | Package | Version |
|---|---|---|---|
| numpy | 1.26.4 | aiohttp | 3.14.0 |
| pandas | 3.0.3 | aiodns | 4.0.4 |
| scipy | 1.17.1 | websockets | 16.0 |
| scikit-learn | 1.9.0 | matplotlib | 3.10.9 |
| pydantic | 2.13.4 | flask | 3.1.3 |
| pydantic_core | 2.46.4 | fastapi | 0.136.3 |
| hyperopt | 0.2.7 | uvicorn | 0.48.0 |
| ccxt | 4.5.56 | starlette | 1.2.1 |
| yfinance | 1.4.1 | redis | 8.0.0 |
| requests | 2.34.2 | python-dotenv | 1.2.2 |
| schedule | 1.2.2 | | |

> pydantic is **v2** and REQUIRED at v2 — `bootstrap/settings/schema.py` uses
> `model_config = ConfigDict(...)`; the 16 v1-style schemas (`@validator`/`class Config`)
> run via v2's back-compat shim. Do not pin pydantic <2.

### A.2 Dev / CI tooling

| Tool | Version | Use |
|---|---|---|
| pytest | 9.0.3 | test runner |
| pytest-asyncio | 1.4.0 | async tests |
| pytest-cov | 7.1.0 | coverage (E6.T5) |
| import-linter | 2.11 | layering gate (R1–R6) |
| grimp | 3.14 | import-graph builder |
| mypy | 2.1.0 | typing (E6.T4) |

### A.3 Explicitly EXCLUDED

- **TA-Lib** — declared in `requirements.txt` but imported by **zero** source files; absent
  from the working venv. Not a runtime dependency. → remove from `requirements.txt` (debt).

### A.4 Installation order (wheels-only; order defensive, not strictly required)

1. Create venv on Python 3.12; upgrade `pip`, `setuptools`, `wheel`.
2. `numpy==1.26.4` (foundation for the numeric stack).
3. `pandas==3.0.3 scipy==1.17.1 scikit-learn==1.9.0`.
4. `pydantic==2.13.4`.
5. Exchange/IO: `ccxt==4.5.56 aiohttp==3.14.0 aiodns==4.0.4 yfinance==1.4.1`.
6. Viz/web/store/util: `matplotlib==3.10.9 flask==3.1.3 fastapi==0.136.3 uvicorn==0.48.0 redis==8.0.0 requests==2.34.2 python-dotenv==1.2.2 schedule==1.2.2 hyperopt==0.2.7`.
7. Tooling: `pytest==9.0.3 pytest-asyncio==1.4.0 pytest-cov==7.1.0 import-linter==2.11 mypy==2.1.0`.

### A.5 Technical-debt items to correct SEPARATELY (not roadmap tasks)

- `requirements.txt`: replace stale pins with §A.1; drop TA-Lib; add pydantic==2.13.4.
- CI (`.github/workflows/ci.yml`) installs no numeric deps — only adds import-linter/pytest;
  fine for the layering gate, but the test job needs the full canonical set to run pytest.
- The broken Windows-venv `Scripts/python.exe` artifact (WSL interop) is cosmetic.

---

## B. Validation Procedure

Run from repo root with the canonical interpreter (`.venv/bin/python` on WSL, or the
Windows venv). Each step lists the expected output.

| # | Command | Expected |
|---|---|---|
| B1 | `python --version` | `Python 3.12.x` |
| B2 | `python -c "import numpy,pandas,pydantic;print(numpy.__version__,pandas.__version__,pydantic.VERSION)"` | `1.26.4 3.0.3 2.13.4` (numpy 2.4.x tolerated for non-golden work) |
| B3 | `python -c "from bootstrap.settings.loaders import load_settings; print(type(load_settings()).__name__)"` | `Settings` (pydantic-v2 settings gate) |
| B4 | `lint-imports` | `Analyzed 412 files … Contracts: 2 kept, 0 broken` |
| B5 | `python -m pytest tests/e2e/test_backtest_golden.py -q` | `2 passed` |
| B6 | `python -m pytest -q` | full-suite baseline (record count; this is the per-batch gate for E1.T4) |

**Prerequisite fix applied this turn:** `_extract_fusion_config_data` was missing its
`return` (stranded as dead code in `enhanced_config_loader.py:118` during E5.T5 split
`312c5ee`), so `load_settings()` raised `TypeError` and **all** infra imports / golden
tests were non-functional. Fixed (added the return; removed the orphan). B3/B5 now pass.

---

## C. Roadmap Resume Plan

Per-task gate template: **entry** → **what** → **validation** → **retires (allowlist)** →
**risk** → **exit**. Order is the accepted execution priority.

### C.1 E1.T4 — Inject settings into infrastructure (batched)
- **Entry:** B3+B5 green; container can pass settings in (verify E2.T1 wiring).
- **What:** remove `from bootstrap.settings.loaders import load_settings` from infra; receive
  settings via constructor injection. Batches: (a) data/ (b) brokers/ (c) fusion+logging+
  orchestrators+portfolio (d) services/ (e) watchers/ (f) data_sync/.
- **Validation (per batch):** `grep -rn "bootstrap.settings.loaders" infrastructure/` count
  strictly decreases; `pytest` suite stays at the B6 baseline; `lint-imports` green; remove
  the matching `-> bootstrap.settings.loaders` allowlist entries as each batch lands.
- **Retires:** the 29 `infrastructure.* -> bootstrap.settings.loaders` allowlist entries.
- **Risk:** MEDIUM (constructor signatures + container wiring; behavior must not change).
- **Exit:** zero infra→bootstrap.settings edges; suite green; those allowlist entries gone.

### C.2 E1.T5 — Convert remaining application/shared callers
- **Entry:** E1.T4 complete.
- **What:** remove remaining settings-loader imports from application/ + shared/ (incl. the
  shared→bootstrap back-edge in `event_system.py`).
- **Validation:** `grep` returns 0 outside bootstrap/ + application/configs/; suite green.
- **Retires:** the 15 `application.* -> bootstrap.settings.loaders` entries + the
  `shared.event_system -> bootstrap.settings.loaders` entry.
- **Risk:** MEDIUM (preserve event-routing behavior).
- **Exit:** settings-injection bucket fully retired (46 → 0 of the E1.T4/T5 block).

### C.3 E8 — event_system relocation
- **Entry:** E1.T5 complete.
- **What:** relocate/invert `shared/event_system.py` so it no longer reaches up into
  domain/infrastructure (it currently imports domain entities/VOs + infra forensic_logger,
  advanced_risk_management, architecture_orchestrator).
- **Validation:** event-bus characterization tests (`test_logging_messaging_characterization`)
  unchanged; suite green; lint green.
- **Retires:** the 5 remaining `shared.event_system -> {domain.*, infrastructure.*}` entries.
- **Risk:** MEDIUM (bus is behavior-sensitive; callback-exception surfacing must hold).
- **Exit:** shared/ imports nothing above it (R6 clean for event_system).

### C.4 E8 — optimization_service port split
- **Entry:** independent of C.1–C.3 (can run after E1.T5).
- **What:** put a domain port between `shared.optimization_service` and
  `infrastructure.optimization.hyperopt_space`; likewise for the 3
  `application.services.unified_optimization_service -> infrastructure.optimization.*` edges.
- **Validation:** optimization path smoke + suite green; lint green.
- **Retires:** `shared.optimization_service -> hyperopt_space` + the 3 unified_optimization edges.
- **Risk:** MEDIUM.
- **Exit:** optimization wiring behind a port; those 4 entries gone.

### C.5 E5-B sequence (golden-gated, per-file approval)
- **Entry:** C.1–C.4 done; golden + characterization tests green; per-module go-ahead.
- **What:** broker adapters split (before VO-wiring) → multi_broker_service/broker_execution_service
  → advanced_sltp_manager/risk → realistic/comprehensive_portfolio backtester → the 4
  trading-deferred modules (strategy_manager, fusion_service, strategy_provider,
  probabilistic_position_sizer) → carried E4 broker VO-wiring (needs contract items D1/D2).
- **Validation:** golden backtest byte-stable; per-adapter parity (adapter == canonical);
  suite green; retire E5-B + E4-deferred + E5 data-sync + reporting-inversion allowlist blocks
  as each lands.
- **Retires:** E5-B risk/exec (7), backtest/WFO/opt (10), E4-deferred ingestion/DTO (9),
  E5 data-sync/workflow (8), E5-A reporting inversion (2) — 36 entries.
- **Risk:** HIGH (Order/Money/ExecutionIntent; broker execution).
- **Exit:** infra↔application trading edges retired or behind ports.

### C.6 E6.T5 — coverage gate
- **Entry:** B6 suite green; a DEFINED numeric coverage threshold (decision required).
- **What:** `pytest --cov` gate at the agreed threshold; extend the 5 port-fake unit tests.
- **Validation:** coverage ≥ threshold in CI.
- **Retires:** none (test-only).
- **Risk:** LOW–MEDIUM.
- **Exit:** coverage gate enforced in CI.

### C.7 E6.T4 — typing remediation (separate follow-up epic)
- Blocked by the E4 freeze (domain 115 / application 2249 strict errors in frozen code).
  Not scheduled here; pull in only if a later task requires it. Needs an explicit unfreeze + scope.

---

## D. Allowlist Retirement Plan

92 entries today (89 layered + 3 R1). Each block retires wholesale with its owning task.

| Order | Block | Entries | Retired by | Post-state |
|---|---|---|---|---|
| 1 | `infrastructure.* -> bootstrap.settings.loaders` | 29 | E1.T4 | 92 → 63 |
| 2 | `application.* -> bootstrap.settings.loaders` + event_system→bootstrap | 16 | E1.T5 | 63 → 47 |
| 3 | `shared.event_system -> {domain.*, infrastructure.*}` (remaining 5) | 5 | E8 event_system relocation | 47 → 42 |
| 4 | `shared.optimization_service` + `unified_optimization_service` → infra.optimization | 4 | E8 optimization port split | 42 → 38 |
| 5 | E5-B risk/exec/position-sizing | 7 | E5-B | 38 → 31 |
| 6 | E5-B backtest/WFO/optimization | 10 | E5-B | 31 → 21 |
| 7 | E4-deferred ingestion/DTO (`infra.data -> application`) | 9 | E5-B (E4 VO-wiring) | 21 → 12 |
| 8 | E5 data-sync/watcher-retune/workflow (`application -> infra`) | 8 | E5-B | 12 → 4 |
| 9 | E5-A reporting inversion (main_wfo→report, prod_orch→dashboard) | 2 | E5-B dependency inversion | 4 → 2 |
| 10 | R1 CLI → comprehensive_portfolio_backtester | 3 | E5.T6 CLI fat-wiring | 2 → 0* |

\* Target end-state = empty allowlist (full layering compliance). Counts are exact at the
time of writing; re-verify with `lint-imports` after each block lands. Note the
optimization-service edge appears once under block 4 (it was listed in the E5-B optimization
comment group in pyproject but is owned by the E8 optimization split).

---

## E. Blocker re-evaluation under the canonical environment

| Previously blocked | Now | Why |
|---|---|---|
| E1.T4 / E1.T5 | **UNBLOCKED** | settings load (B3) + golden (B5) + suite (B6) run here after the fusion-return fix |
| E8 event_system relocation | **UNBLOCKED** | char tests runnable |
| E8 optimization_service split | **UNBLOCKED** | runnable |
| E5-B sequence | **UNBLOCKED for validation** | golden/char runnable; still gated by per-file approval (process, not env) |
| E6.T5 coverage gate | **PARTIALLY** | runnable; still needs a defined numeric threshold (decision) |
| E6.T4 typing | **STILL BLOCKED** | E4 freeze (architectural decision), independent of env |

**New blocker found & resolved this turn:** `load_settings()` `TypeError` from the missing
`_extract_fusion_config_data` return (regression from E5.T5 `312c5ee`). Fixed as a prerequisite.
