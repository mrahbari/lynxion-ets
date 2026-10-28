# Lynxion ETS — Canonical Project Context & Engineering Handover

## ROLE

Act as the **Principal Software Architect, Quant Researcher, Algorithmic Trading Engineer, Production Reliability Engineer, and Forensic Auditor** responsible for creating the canonical engineering handover for the Lynxion ETS project.

You are NOT being asked to redesign, optimize, refactor, or modify the production system in this task.

Your sole objective in this phase is:

> **Understand the entire existing Lynxion system, reconstruct its current technical and research state, independently verify important historical claims, and create a canonical Project Context document that another senior AI coding agent can use to continue development without repeatedly asking the operator to explain the project.**

This is a **READ / ANALYZE / VERIFY / DOCUMENT ONLY** task.

---

# ABSOLUTE RULES

1. DO NOT modify production source code.
2. DO NOT modify strategy parameters.
3. DO NOT modify configuration.
4. DO NOT modify historical datasets.
5. DO NOT modify `data/trade_journal.csv`.
6. DO NOT modify `data/trade_features.csv`.
7. DO NOT modify the prospective validation boundary.
8. DO NOT create or force trades.
9. DO NOT optimize strategy parameters.
10. DO NOT alter risk controls.
11. DO NOT "fix" anything during this task.
12. DO NOT rewrite architecture.
13. DO NOT delete or rename existing project files.
14. Do not assume that a previous agent's statement that something is "fixed" means it is actually fixed.
15. Every important claim must be classified as:
    - PROVEN
    - VERIFIED
    - PARTIALLY VERIFIED
    - UNVERIFIED
    - INFERRED
    - HYPOTHESIS
    - UNKNOWN
16. Preserve the distinction between historical data and prospective validation data.
17. The prospective validation boundary MUST remain immutable.
18. Minimize token usage by using targeted searches, summaries, Git history, and focused file inspection rather than dumping entire files into context.

---

# PRIMARY DELIVERABLE

Create:

`./docs/LYNXION_PROJECT_CONTEXT.md`

This document becomes the **canonical engineering and research context** for the project.

If and only if genuinely necessary, create a small number of additional focused documents under:

`./docs/`

Do NOT create documentation for the sake of creating documentation.

The primary context file must contain enough information for a new senior AI coding agent to understand the project without requiring the operator to repeatedly explain its history.

---

# PHASE 1 — REPOSITORY DISCOVERY

Before writing the context document, inspect:

- README files
- existing documentation
- project structure
- source tree
- configuration
- environment/configuration references
- tests
- scripts
- data schemas
- strategy implementations
- broker implementations
- execution code
- risk modules
- reconciliation
- persistence
- logging
- WFO/backtesting infrastructure
- research tooling
- deployment/runtime scripts

Identify the actual architecture from source code.

Do NOT trust README descriptions when source code contradicts them.

Source code is authoritative.

---

# PHASE 2 — ARCHITECTURE RECONSTRUCTION

Reconstruct and document the actual end-to-end pipeline.

At minimum investigate:

Market Data
→ Watcher
→ Engine
→ Fusion
→ Strategy
→ ExecutionIntent
→ Risk Enforcement
→ Live Execution Guard
→ Broker
→ Exchange
→ Reconciliation
→ Persistence
→ Trade Journal

Identify:

- actual classes
- actual modules
- actual entry points
- actual call paths
- actual interfaces
- important state stores
- persistence mechanisms
- failure boundaries
- retry mechanisms
- concurrency/event-loop behavior
- broker abstraction
- exchange-specific behavior

Document where the architecture differs from intended design.

---

# PHASE 3 — TRADING SYSTEM CAPABILITIES

Document the capabilities that already exist.

Include, where applicable:

- multi-symbol processing
- symbol discovery/universe
- historical OHLCV ingestion
- live market data
- WebSocket
- REST fallback
- timeframe generation
- candle storage
- 1m / 5m / 15m / 30m / 1h or other supported timeframes
- market structure
- volume profile
- ATR
- fusion
- strategy adapters
- confidence engine
- risk management
- position sizing
- cooldown
- SL/TP
- OCO
- broker execution
- reconciliation
- active-position persistence
- trade journal
- backtesting
- WFO
- optimization
- paper/VST mode
- monitoring
- logging
- audit infrastructure

For each capability record:

- where it lives
- how it works
- current status
- verification status
- known limitations

---

# PHASE 4 — GIT / CHANGE HISTORY

Inspect Git history selectively.

Focus on:

- recent commits
- SEV-1 fixes
- P1 position sizing work
- P2 cooldown work
- exit management investigations
- reconciliation fixes
- confidence calibration work
- execution safety work
- heartbeat remediation
- prospective validation work
- recent tasks

For each major change determine:

1. What problem was identified?
2. What was changed?
3. Why was it changed?
4. Which files changed?
5. How was it tested?
6. What evidence proves the fix?
7. Is the fix actually verified?
8. What remains uncertain?

Do not merely copy commit messages.

Reconstruct the engineering story.

---

# PHASE 5 — HISTORICAL TRADING FORENSICS

Inspect the relevant historical trading data, especially:

- `data/trade_journal.csv`
- `data/trade_features.csv`
- active position journals
- relevant execution/reconciliation logs
- broker/order records where available

The current historical boundary is:

> **Trade #694**

The prospective cohort begins at:

> **Trade #695**

Treat this boundary as immutable.

Analyze the historical cohort without modifying it.

Extract and summarize:

- total trades
- completed trades
- net PnL
- gross profit
- gross loss
- win rate
- profit factor
- expectancy
- average win
- average loss
- long/short performance
- symbol concentration
- trade duration
- position sizing
- exposure
- cooldown behavior
- SL/TP integrity
- suspicious trades
- rejected orders
- execution failures
- abnormal outcomes
- major loss clusters
- known anomalies

Do NOT dump thousands of rows into the context file.

Produce a concise forensic summary.

---

# PHASE 6 — VERIFY PREVIOUSLY CLAIMED FIXES

Create a section called:

`## Verified Historical Claims`

For every important previous fix, independently inspect source code, tests, logs, and data where possible.

At minimum investigate:

### P1 — Position Sizing

Expected invariant:

`MAX_POSITION_EXPOSURE <= $1,000 VST`

Determine:

- actual enforcement point
- fallback/default configuration
- bypass possibilities
- historical violations
- post-remediation violations
- evidence

### P2 — Symbol Cooldown

Expected invariant:

60-minute cooldown after applicable losing trade.

Determine:

- actual enforcement point
- ordering in pipeline
- persistence
- restart behavior
- historical violations
- post-remediation behavior

### Position Persistence

Inspect:

`data/active_positions_journal.json`

Verify:

- atomicity
- fsync behavior
- startup restoration
- closure behavior
- stale-state prevention

### Protective Orders

Verify:

- mandatory SL
- mandatory TP
- exchange-side OCO/conditional orders
- wrong-side protection
- missing protection rejection
- failure behavior

### Execution Path Integrity

Verify:

- all production order paths
- LiveExecutionGuard
- RiskEnforcement
- broker entry points
- possible bypasses

### Confidence Engine

Verify:

- whether confidence is genuinely dynamic
- absence of previous hardcoded confidence
- actual strategy adapter behavior
- calibration if evidence exists

### Reconciliation

Verify the previously identified reconciliation bug and remediation.

### Heartbeat Guard

Verify the previously identified heartbeat defect and remediation.

Specifically inspect:

- `_last_market_data_times`
- live WebSocket ingestion
- REST ingestion
- `SignalProcessor`
- `MonitoringAnalysisService`
- `AutoDetectionOrchestrator`
- `MarketDataWatcher`
- receipt timestamp semantics
- stale-data veto behavior
- fail-closed behavior

Do not classify a fix as PROVEN solely because a previous agent reported it.

---

# PHASE 7 — PROSPECTIVE VALIDATION STATE

Document the exact current state of the prospective experiment.

Record:

- baseline commit
- historical boundary
- prospective start
- target sample size
- acceptance criteria
- frozen parameters
- frozen controls
- current completed prospective trades
- current runtime state if observable
- whether the cohort has been contaminated
- whether any trades were excluded
- whether any parameters changed
- whether production code changed

Current known baseline information:

- Baseline commit:
  `75246a1f7364d12790fb1d40ad231bb0222b3d22`

- Historical boundary:
  `Trade #694`

- Prospective cohort:
  `Trade #695 onwards`

- Target:
  `N >= 100 completed prospective trades`

- Prospective net PnL:
  `> $0.00 VST`

- Prospective expectancy:
  `> +$0.25/trade`

- Position sizing violations:
  `ZERO`

- Cooldown violations:
  `ZERO`

- Production code modification during frozen validation:
  `ZERO`

Clearly separate:

### HISTORICAL EVIDENCE

from

### PROSPECTIVE EVIDENCE

Never mix them.

---

# PHASE 8 — STRATEGY INVENTORY

Inspect every strategy currently present.

For each strategy document:

- name
- location
- timeframe
- entry logic
- exit logic
- features used
- market regime assumptions
- long/short behavior
- confidence generation
- dependencies
- known issues
- historical performance if available
- whether it is active/retired/salvageable
- evidence supporting its current status

Include previous strategic findings such as:

- retired strategies
- salvageable strategies
- short-side problems
- synthetic/high-wick token anomalies
- residual baseline performance
- sizing/cooldown contamination

Do not invent conclusions.

---

# PHASE 9 — RESEARCH INFRASTRUCTURE AUDIT

Document the current research capabilities.

Inspect:

- historical data downloader
- candle builders
- feature generation
- backtest runner
- WFO
- hyperparameter optimization
- datasets
- train/test split
- OOS methodology
- cost assumptions
- slippage assumptions
- funding assumptions
- execution simulation
- look-ahead protection
- data leakage protection

Identify gaps.

Especially determine whether:

`backtest execution path == live execution path`

and whether any divergence still exists.

---

# PHASE 10 — OPEN PROBLEMS

Create:

`## Open Problems / Known Risks`

Classify each problem:

### P0 — Production critical
### P1 — High
### P2 — Medium
### P3 — Research enhancement

For each:

- description
- evidence
- affected modules
- risk
- current mitigation
- recommended next action
- whether coding is required
- whether operator approval is required

---

# PHASE 11 — FUTURE DEVELOPMENT ROADMAP

Do NOT implement this roadmap.

Create a proposed roadmap based on evidence.

The roadmap should prioritize:

1. Preserve production safety.
2. Preserve current architecture unless evidence proves it inadequate.
3. Improve research capability.
4. Improve edge discovery.
5. Improve symbol/universe selection.
6. Improve feature engineering.
7. Improve regime awareness.
8. Improve strategy evaluation.
9. Improve statistical validation.
10. Introduce ML only where justified by evidence.
11. Improve opportunity ranking.
12. Improve WFO/OOS robustness.
13. Improve production observability.

Explicitly avoid:

- unnecessary rewrites
- indicator accumulation
- uncontrolled strategy proliferation
- blind hyperparameter optimization
- AI-driven trade decisions without statistical validation
- production changes without evidence

---

# PHASE 12 — AUTONOMOUS DEVELOPMENT MODEL

The future coding agent should be able to operate from this document using a goal-oriented task system.

Document the recommended workflow:

```text
GOAL
  ↓
TASK BACKLOG
  ↓
SELECT HIGHEST-PRIORITY TASK
  ↓
INVESTIGATE
  ↓
IMPLEMENT MINIMAL CHANGE
  ↓
TEST
  ↓
FORENSIC VERIFY
  ↓
DOCUMENT
  ↓
COMMIT
  ↓
SELECT NEXT TASK
```

The future agent should NOT require operator approval for routine engineering work.

Operator approval should only be required for:

- changing core trading philosophy
- changing risk limits
- changing historical/prospective boundaries
- deploying capital-impacting changes
- deleting historical data
- irreversible architectural decisions
- fundamentally conflicting strategic objectives

Routine debugging, testing, documentation, telemetry, research scripts, proven bug fixes, and incremental improvements should be autonomous.

---

# PHASE 13 — CLAIM / EVIDENCE REGISTRY

Create a compact table:

| Claim | Evidence | Status | Confidence |
|---|---|---|---|

Use only evidence actually inspected.

Never mark something PROVEN without evidence.

---

# PHASE 14 — FINAL CONTEXT DOCUMENT STRUCTURE

The final:

`docs/LYNXION_PROJECT_CONTEXT.md`

should contain approximately:

1. Executive Summary
2. Project Mission
3. Current System Status
4. Architecture
5. End-to-End Execution Flow
6. Data Architecture
7. Strategy Architecture
8. Risk Architecture
9. Broker / Execution Architecture
10. Persistence / Reconciliation
11. Backtesting / WFO
12. Historical Trading Forensics
13. SEV-1 / Major Incident History
14. Verified Fixes
15. Prospective Validation State
16. Strategy Inventory
17. Research Infrastructure
18. Known Problems
19. Research Gaps
20. Future Roadmap
21. Claim / Evidence Registry
22. Important Files / Entry Points
23. Git Baseline / Important Commits
24. Rules for Future AI Agents

---

# TOKEN EFFICIENCY REQUIREMENT

This is important.

Do NOT read every file in full.

Use:

- repository tree
- targeted search
- symbol/class/function search
- Git history
- focused file ranges
- test names
- logs around relevant events
- statistical summaries

Only open complete files when necessary.

Do not duplicate information.

The final context should be comprehensive but compact.

The goal is:

> **Maximum engineering knowledge per token.**

---

# COMPLETION CRITERIA

This task is complete only when:

- repository structure is understood
- architecture is reconstructed
- important historical changes are understood
- historical trading data has been summarized
- previous fixes have been independently checked
- prospective validation state is documented
- strategies are inventoried
- research infrastructure is documented
- open problems are classified
- future roadmap is proposed
- claims are linked to evidence
- no production code has been modified
- no parameters have been changed
- no historical/prospective data has been modified
- `docs/LYNXION_PROJECT_CONTEXT.md` exists and is complete

At the end, report:

1. Files inspected
2. Documents created
3. Production files modified: MUST BE ZERO
4. Configuration modified: MUST BE ZERO
5. Historical data modified: MUST BE ZERO
6. Prospective validation modified: MUST BE ZERO
7. Claims independently verified
8. Claims still unverified
9. Top 10 open engineering/research problems
10. Recommended first task for the future autonomous coding agent

DO NOT ask the operator for permission to perform any of the above analysis.

DO NOT modify production code.

This is a documentation and forensic handover phase only.