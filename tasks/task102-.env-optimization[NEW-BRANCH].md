# Professional .env Refactor & Governance Prompt (Hedge-Fund Grade)

## ROLE

You are a **Senior Systems Architect & Quantitative Risk Infrastructure Engineer** responsible for auditing, refactoring, and governing a production-grade trading system configuration layer (`.env`).

Your objective is to transform the `.env` file into a **clean, deterministic, auditable, production-safe configuration system** suitable for hedge-fund-grade infrastructure.

This task is NOT about optimization.
This task is about **safety, correctness, determinism, and governance**.

---

## INPUT

You are given:

1. Full `.env` file, alternatively backup is .env.example
2. Full codebase (all modules, services, watchers, engines, strategies, risk managers, executors, pipelines)

---

## GLOBAL OBJECTIVES

### 1. Configuration Integrity

Ensure:

* Single source of truth for each domain
* No duplicated responsibility
* No conflicting parameters
* Deterministic runtime behavior

---

## TASKS

### 🔍 PHASE 1 — USAGE ANALYSIS

For every `.env` variable:

Classify into:

* `ACTIVE_USED` → Referenced in runtime code
* `PASSIVE_USED` → Referenced only in config/metadata
* `DECLARED_UNUSED` → Never referenced
* `LEGACY_UNUSED` → Referenced in deprecated code
* `SHADOWED` → Defined but overridden elsewhere
* `DUPLICATED_AUTHORITY` → Multiple vars control same logic

---

### 🧠 PHASE 2 — DOMAIN OWNERSHIP MAPPING

Map each variable to exactly ONE domain:

Domains:

* `Risk`
* `Execution`
* `Strategy`
* `PositionSizing`
* `Portfolio`
* `Data`
* `Optimization`
* `WFO`
* `Backtest`
* `Watcher`
* `Fusion`
* `Confidence`
* `Correlation`
* `Safety`
* `Monitoring`
* `Infrastructure`
* `Broker`
* `Sync`
* `Security`

If a variable belongs to multiple domains → FLAG AS ARCHITECTURAL ERROR.

---

### 🧹 PHASE 3 — UNUSED VARIABLE ELIMINATION

For each:

* `DECLARED_UNUSED`
* `LEGACY_UNUSED`

Actions:

* Mark for permanent deletion
* Provide deletion safety level:

  * SAFE_DELETE
  * REVIEW_DELETE

---

### ⚠️ PHASE 4 — CONFLICT & DUPLICATION RESOLUTION

Detect and resolve:

* Multiple risk limits (e.g. MAX_DRAWDOWN, RISK_MAX_DRAWDOWN, MAX_DRAWDOWN_THRESHOLD)
* Multiple confidence thresholds
* Multiple RR definitions
* Multiple volatility models
* Multiple position sizing authorities (Kelly + Martingale + Fixed Fractional)

Rules:

* Only ONE authority per domain
* Others must be deprecated or removed

---

### 🏗️ PHASE 5 — CONFIG GOVERNANCE DESIGN

reformat `.env` file and specific section for each type of configs into:

```
.env
  ├── core
  ├── risk
  ├── execution
  ├── strategy
  ├── sizing
  ├── confidence
  ├── data
  ├── optimization
  ├── monitoring
  ├── safety
  └── infrastructure
```

---

## OUTPUT (PRODUCTION READY)

### 1️⃣ Classification Table

For each variable:

* Name
* Status (ACTIVE_USED / UNUSED / DUPLICATED / SHADOWED / LEGACY)
* Domain
* Authority Level
* Action (KEEP / MOVE / DELETE / MERGE)

---

### 2️⃣ Deletion List

Permanent removal list:

* Variable name
* Reason
* Risk level

---

### 3️⃣ Authority Map

```
Domain → Authority Variable
Risk → RISK_ENGINE_CONFIG
PositionSizing → POSITION_SIZING_ENGINE
Confidence → CONFIDENCE_ENGINE
Execution → EXECUTION_ENGINE
```

---

### 4️⃣ Clean Config Structure

Provide:

* Refactored env structure
* Modular env layout
* New naming conventions
* Dependency order

---

### 5️⃣ Safety Guarantees

Ensure:

* No runtime ambiguity
* No double authority
* No shadow configs
* Deterministic behavior
* Predictable risk exposure

---

## NON-NEGOTIABLE RULES

* No optimization logic
* No strategy tuning
* No capital changes
* No performance tuning
* No behavioral assumptions

This is a **governance, safety, and architecture task only**.

---

## FINAL PRINCIPLE

> A hedge-fund system must never depend on configuration ambiguity.
> Every variable must have:
>
> * One owner
> * One meaning
> * One authority
> * One execution path

---

**Goal:**
Transform `.env` into a **clean, auditable, deterministic, production-grade configuration layer**
suitable for institutional-grade trading infrastructure.
