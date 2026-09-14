# Lynxion ETS — Complete Single-File AI Handoff

**Audience:** AI engineering agents, quantitative researchers, technical reviewers, and investors'
technical advisers

**Prepared:** 2026-09-14

**Repository:** `lynxion-ets`

**Branch at preparation:** `task-00-ground-truth-audit`

**Source checkpoint:** `0340e3d` (this document is committed after that checkpoint)

**Technical-release verdict:** `INVESTOR_REVIEW_READY — TECHNICAL VST/SHADOW ONLY`

**Economic verdict:** `COLLECTING — PROFITABILITY NOT PROVEN`

**Economic admission policy:** `NO_TRADE_DEFAULT`

---

## 1. How to use this document

This is a self-contained project handoff. A receiving AI can understand the project, its current
evidence, its roadmap, and the required research discipline from this file alone. Access to the
repository is still required to verify mutable facts and make changes.

Evidence must be trusted in this order:

1. current source code and tests;
2. frozen research manifests and preregistrations;
3. hash-bound datasets and reproducible artifacts;
4. append-only progress and task records;
5. dated runtime or exchange observations;
6. prose summaries and previous-agent statements.

Any changing fact—Git HEAD, worktree status, process ownership, exchange positions, stop coverage,
test count, candidate count, runtime configuration, or market-data coverage—must be refreshed from
its primary source before being represented as current.

Classify material conclusions as:

- `FACT`: directly reproduced from current evidence;
- `INFERENCE`: logically derived from facts, with assumptions disclosed;
- `HYPOTHESIS`: testable explanation not yet established;
- `UNKNOWN`: evidence is missing, stale, ambiguous, or inaccessible.

Never convert a historical claim into current fact merely because it appears in documentation.

---

## 2. Project purpose

Lynxion ETS is a Python-based, event-driven cryptocurrency perpetual-futures trading and research
system. BingX VST is the preferred broker integration and validation target. The system contains
market-data ingestion, signal generation, strategy adapters, centralized risk admission, broker
execution, exchange-side protection, reconciliation, persistence, monitoring, backtesting, and
prospective research tooling.

The primary mission is not to maximize trade count, win rate, leverage, or presentation quality.
It is:

> Determine whether Lynxion possesses a durable, statistically defensible, risk-controlled trading
> edge with positive net expectancy after realistic execution costs and robust out-of-sample and
> prospective validation. If the current information and strategy families fail, evaluate bounded
> causal alternatives and explicitly decide whether new data, a new strategy family, or a justified
> architecture change is required.

Infrastructure quality is necessary but does not prove economic edge.

---

## 3. Current high-level truth

The project now has two deliberately separate tracks.

### Track A — Investor technical delivery

The bounded technical package is frozen as:

`INVESTOR_REVIEW_READY — TECHNICAL VST/SHADOW ONLY`

The frozen evidence boundary is commit `1f07520`, recorded by TASK-0234.

This verdict supports only the following category of claims:

- the project contains a deterministic broker-free demonstration;
- the guarded BingX VST path has dated evidence of capped isolated execution and protection;
- investor-demo activity is separated from research evidence;
- central risk, protection, routing, leverage/margin admission, journaling, and reconciliation have
  focused source/test evidence;
- the package contains architecture, evidence, limitations, and reviewer material.

It does **not** mean:

- profitable or break-even;
- `PILOT_REVIEW_READY`;
- permanently healthy runtime or exchange state;
- approved for real funds;
- safe to scale capital;
- any strategy is admitted economically.

Later branch commits do not silently expand the frozen release claim. A new release freeze would
need its own clean verification and evidence boundary.

### Track B — Economic edge validation

This track remains active. No strategy currently clears all frozen promotion gates. Therefore:

`NO_TRADE_DEFAULT` remains the only admissible economic-release policy.

Individual positive trades are encouraging observations, not proof of edge.

---

## 4. Why the project changed direction

The historical trade journal showed that the deployed mixture was economically negative. The
frozen investor baseline used 1,913 source rows and 1,257 final deduplicated trade IDs:

| Metric | Frozen value |
|---|---:|
| Duplicate state rows resolved | 656 |
| Recorded PnL | -14,935.7042 USDT |
| Signed fees | -559.710655 USDT |
| Cost-adjusted PnL | -15,495.414855 USDT |
| Expectancy | -12.32729901 USDT/trade |
| Profit factor | 0.15008542 |
| Max drawdown | 15,557.062582 USDT |

This baseline mixes materially different code, configuration, sizing, and risk eras. It lacks
complete MFE, MAE, measured slippage, funding, regime, initial protection, confidence, and
configuration provenance. It is valid as negative descriptive ground truth, but it is not one clean
experiment from which arbitrary strategies can be optimized.

Some historical slices looked positive—especially small-notional, MeanReversion, and small
OIFootprint samples—but they were post-hoc, under-sampled, or missing OOS/prospective gates. They
were retained as hypothesis leads, not promoted as edge.

The project therefore stopped treating implementation progress or post-hoc slices as profitability
proof and adopted preregistered, cost-adjusted, prospective validation.

---

## 5. Edge discovery method

The 2026-09-14 acceleration directive adds a strict decision-before-build and engineering-budget
gate: at most three independent new mechanisms, zero allowed, while carry/basis and broad L2 builds
are currently rejected by existing evidence. C-33 liveness repair is the highest-ranked minimal
task; C-35 continues to its 168-decision rate checkpoint and C-11 is background-only because its
observed completion rate projects roughly two years to the frozen minimum.

The required research loop is:

```text
reconstruct and deduplicate evidence
    -> attribute losses and gains
    -> identify a causal mechanism
    -> preregister all rules before outcomes are opened
    -> validate data integrity and provenance
    -> run historical/OOS tests only where scientifically admissible
    -> collect genuinely forward prospective observations
    -> keep aggregate economics sealed until frozen gates are met
    -> issue KEEP / REJECT / INSUFFICIENT verdict
    -> propose a minimal production change only after promotion
```

Every candidate must freeze, before outcome inspection:

- hypothesis and causal mechanism;
- asset universe and venue;
- timeframe and decision timestamp;
- feature availability and shifts;
- side and regime rules;
- entry and exit definitions;
- stop-loss and take-profit path semantics;
- fees, funding, spread, slippage, and stress costs;
- sample-size floor;
- chronological train/OOS or walk-forward folds;
- bootstrap or other uncertainty method;
- temporal, symbol, and side breadth;
- concentration and drawdown limits;
- acceptance and rejection conditions;
- prospective activation boundary.

After outcomes are visible, thresholds and gates may not be weakened. Parameter variants on an
already-opened dataset are not independent hypotheses.

When a candidate fails, preserve the negative result and advance to another preregistered causal
mechanism. If the bounded hypothesis cycle fails, explicitly test the hypothesis that the current
information set is insufficient. Only then consider a new data source, strategy family, or material
architecture direction. Do not endlessly optimize the same opened panel.

---

## 6. Mandatory trading-validation standards

Any edge or backtest claim must satisfy all applicable items:

1. no lookahead bias;
2. no lag or timestamp misalignment;
3. indicators shifted so only available information is used;
4. no data-snooping promotion;
5. no survivorship-biased universe construction;
6. correct multi-timeframe downsample, forward-fill, shift, and alignment;
7. SL/TP evaluated with candle high/low rather than close alone;
8. conservative stop-first handling when long SL and TP are both touched in one candle;
9. realistic execution prices;
10. fees included in PnL;
11. slippage included in PnL;
12. funding included where applicable;
13. partial fills and exchange acknowledgements handled correctly;
14. equity drawdown measured peak-to-trough;
15. portfolio exposure limits enforced;
16. duplicate entries prohibited unless explicitly allowed;
17. walk-forward validation genuinely out of sample;
18. reproducible reports bound to code and inputs;
19. positive net expectancy and profit factor above 1;
20. adequate sample, time, symbol, and side breadth;
21. acceptable concentration and stress-cost performance;
22. unopened prospective confirmation before production promotion.

A violation affecting validation correctness is P0. Win rate and leverage never substitute for
these gates.

---

## 7. Current research state

The following is a dated snapshot at source checkpoint `0340e3d`. Refresh it from repository data
before reporting it as current.

### C-35 — Compression release

- Status: `COLLECTING`
- Decision hours: 88
- Completed signals/outcomes: 2
- Outcomes: individually positive after frozen primary and stress costs
- Direction breadth: both SHORT
- Symbol breadth: XRPUSDT and ADAUSDT
- Represented UTC weeks: 1
- Data integrity: zero known gaps, duplicates, or boundary-role errors at the checkpoint
- Aggregate economics: `SEALED`
- First frozen signal-rate checkpoint: 168 decisions

The first two results are encouraging but far too small and concentrated to establish edge. The
governing protocol is `tasks/research/edge-candidate-register-v34.md`.

A real orchestration defect was discovered when the first signal appeared: the hourly pipeline
attempted to evaluate the next signal before resolving the prior outcome, causing a deadlock/failure.
Commit `fda57ea` reordered outcome resolution before signal evaluation and added explicit unresolved
signal handling plus regressions. This repair enabled correct measurement; it did not generate the
market opportunity or create profitability.

### C-11 — Severe funding

- Status: `COLLECTING`
- Frozen boundary epoch: `1788082349`
- Completed outcomes: 2
- Pending outcomes: 1 ETHUSDT candidate at the checkpoint
- Only funding settlements strictly after the boundary may be counted
- Historical observations may never be imported into this cohort

One completed record was approximately flat/slightly negative and one ETHUSDT outcome was strongly
positive. N=2 is not statistically meaningful. The governing protocol is
`tasks/research/edge-candidate-register-v10.md`.

### C-33 — Liquidation exhaustion

- Status: `COLLECTING`
- Latest verified eligible buckets: 740
- Next frozen checkpoint: 1,000
- Public append-only prospective collection only
- Interrupted or liveness-incomplete buckets remain ineligible

The Binance forced-liquidation feed is treated as censored latest-event snapshots, not complete
liquidation volume. Do not reinterpret it as a complete tape.

### Prospective +12% activation / +5% net-floor exit shadow

- Research/preregistration work exists.
- An official public BingX perpetual fee snapshot and an empty post-fee cohort were prepared.
- Static readiness checking was corrected.
- Activation remains blocked by exactly the required fresh, read-only single-runner proof that no
  position is missing stop protection, plus any applicable runtime/authenticated approval.
- It must not be tuned from already-inspected winners or activated merely because the alternative
  looks intuitively better.

---

## 8. Investor technical package

The investor track was separated from the economic track so a technically reviewable version could
be delivered without waiting months for edge evidence and without fabricating profitability.

Key completed units:

| Task | Result |
|---|---|
| TASK-0223 | Investor release scope, claims, and boundaries frozen |
| TASK-0224 | Two demo-scope P0 gaps identified |
| TASK-0225 | Persistent cooldown contamination removed from deterministic demo; P0-IR1 closed |
| TASK-0226 | Dedicated fail-closed broker-free investor launcher; P0-IR2 closed |
| TASK-0227 | Dated capped isolated BingX VST order with SL/TP evidence |
| TASK-0228 | Negative cost-adjusted economic baseline frozen; no-trade retained |
| TASK-0229 | Investor and technical reviewer narratives created |
| TASK-0230 | Demo order identities excluded from edge research |
| TASK-0231 | Forward VST activation evidence and cohort boundary work |
| TASK-0232 | Launcher-scoped isolated 10x configuration and ROE-boundary regression |
| TASK-0233 | Execution stablecoin-guard liveness defect repaired |
| TASK-0234 | Evidence index and technical-only investor verdict frozen |

The deterministic broker-free demo previously reproduced 87 PAPER decisions, 174 verified records,
and zero exchange sends. This is dated evidence and should be rerun at a new release freeze.

The controlled BingX VST proof is also dated. It demonstrated a bounded isolated position with
exchange-side stop and take-profit coverage at its checkpoint. It does not prove that current
exchange state is still healthy.

Current limits documented for the investor scope:

- maximum order notional: 21 USDT VST;
- maximum portfolio notional: 1,000 USDT VST;
- `./lynxion` new entries request isolated 10x under its launcher-scoped contract;
- leverage changes margin, liquidation headroom, and ROE trigger timing; it does not create edge.

---

## 9. System architecture

The intended high-level flow is:

```text
market data
    -> watchers and feature engines
    -> fusion and strategy adapters
    -> execution intent
    -> centralized risk enforcement
    -> live execution guard
    -> broker routing / BingX adapter
    -> exchange acknowledgement and conditional protection
    -> active position management
    -> reconciliation and persistent journals
    -> trade and research evidence
```

Important areas:

| Area | Primary location or entry point |
|---|---|
| Main CLI/runtime | `run_trading_system.py`, `./lynxion` |
| Configuration/profiles | `application/configs/` |
| Application orchestration | `application/`, `infrastructure/orchestrators/` |
| Domain entities and ports | `domain/entities/`, `domain/ports/` |
| Watchers and market data | `infrastructure/watchers/`, `infrastructure/data/` |
| Engines/fusion | `infrastructure/engines/`, `infrastructure/fusion/` |
| Strategies | `infrastructure/strategies/` |
| Central risk | `infrastructure/risk/risk_enforcement.py` |
| Position protection/trailing | `infrastructure/risk/active_position_manager.py` |
| Execution guard | `shared/` and execution wiring |
| BingX broker boundary | `infrastructure/brokers/adapters/bingx_adapter.py` |
| Reconciliation/persistence | broker, execution, tracking, and journal modules under `infrastructure/` and `data/` |
| Backtesting/research | `application/backtesting/`, `application/walk_forward/`, `infrastructure/research/`, `scripts/` |
| Tests | `tests/` |

This diagram is orientation, not proof of the actual runtime call graph. Before changing behavior,
trace constructors, dependency injection, event subscriptions, guard calls, adapter selection, and
error paths in current source.

---

## 10. Execution and risk principles

The system has been hardened around the general risk-bypass class rather than treating symbol
blacklisting as the solution. A symbol-specific exclusion such as XMR may contain an incident but
cannot substitute for centralized controls.

Critical behavior to preserve and verify includes:

- one serialized admission path before broker submission;
- finite, side-correct mandatory stop loss;
- bounded per-order and aggregate portfolio notional;
- duplicate-symbol and cooldown rejection;
- enabled-broker and account-type routing;
- isolated margin and leverage establishment/readback before entry admission;
- exchange acknowledgement and client-order identity;
- conditional SL/TP visibility or guaranteed unwind;
- kill-switch escalation if protection and unwind fail;
- restart hydration and reconciliation;
- monotonic stop movement—never loosen an existing protective stop;
- consistent ROE math using leverage and side correctly;
- spot adapters excluded from futures-position/trailing management;
- disabled brokers unable to activate solely because credentials exist;
- stale, incomplete, malformed, or provenance-invalid market data rejected fail-closed.

Local unit tests prove tested code paths, not current deployment or mutable exchange state. A source
fix does not affect a running process until the applicable controlled reload occurs.

---

## 11. Historical incidents and lessons

Important incident classes discovered during the roadmap include:

- symbol/context leakage and repeated unintended XMR trading;
- risk admission capable of being bypassed or evaluated inconsistently;
- missing exchange-side protection and the need for guaranteed unwind;
- stale/incorrect position source caused by Spot adapters being queried for futures positions;
- disabled Phemex configuration being bypassed by connection assumptions;
- incorrect or stale leverage/isolated/ROE assumptions;
- trailing/breakeven mutation, restart hydration, and monotonicity risks;
- order-journal in-flight state surviving incorrectly across startup;
- market-data staleness and incomplete/gapped historical panels;
- strategy-to-broker telemetry failure capable of stopping intents before submission;
- forward-cohort activation manifests invalidated by later HEAD changes;
- prospective orchestration ordering deadlock after the first C-35 signal;
- stale readiness/checkpoint defaults that reported already-resolved blockers.

The correct lesson is not that every runtime problem is permanently solved. It is that each verified
defect requires a minimal root-cause fix, focused regression, dated evidence, and explicit distinction
between repository correctness and deployed runtime state.

---

## 12. Data and evidence organization

Important categories include:

- `data/trade_journal.csv`: historical trade outcome journal; mixed eras and incomplete provenance;
- `data/research/investor_release/`: frozen investor baseline and release artifacts;
- `data/research/c11/`: C-11 prospective funding ledger;
- `data/research/c33/`: C-33 prospective public liquidation/candle evidence;
- `data/research/c35/`: C-35 candles, funding, decisions, signals, outcomes, and coverage receipts;
- `tasks/research/`: candidate registers and frozen protocols;
- `docs/LYNXION_PROGRESS_LEDGER.md`: chronological task/evidence record.

Research ledgers are append-only unless a frozen task explicitly defines another safe operation.
Never import historical observations into a prospective cohort or silently repair evidence after
outcomes are visible.

---

## 13. Current roadmap

### Immediate / short term

1. Preserve the frozen technical-only investor package and honest limitations.
2. Continue evidence-supported correctness repairs that make configured behavior execute correctly.
3. Continue C-35 hourly prospective collection without opening aggregate economics early.
4. Refresh C-11 only on its authorized cadence and preserve its strict boundary.
5. Maintain C-33 toward its frozen checkpoints with liveness-complete evidence only.
6. Keep the exit shadow inactive until its final evidence and approval prerequisites pass.
7. Avoid broad refactoring and presentation-driven cleanup.

### Medium term

1. Obtain adequate prospective sample and breadth for active candidates.
2. Evaluate net expectancy, PF, costs, drawdown, concentration, folds, bootstrap, and stress cases.
3. Reject candidates that fail frozen gates without retuning the opened outcomes.
4. Promote only a candidate with independently reproducible and prospective evidence.
5. Prepare a bounded pilot proposal only after both economic and operational gates pass.

### Long term

1. Replicate any qualifying edge across time, regimes, symbols, and sides.
2. Improve measured execution telemetry and causal attribution.
3. If the bounded cycle fails, reassess information sources, strategy family, or architecture as new
   preregistered hypotheses.
4. Treat real-money deployment as a separate capital, security, operational, monitoring, legal, and
   approval decision.

---

## 14. Task execution policy

Every task is a sealed boundary. Do not refactor, clean up, redesign, or fix unrelated findings
inside another task. Record out-of-scope discoveries and continue the current unit.

For authorized repository work:

1. identify the first unfinished roadmap item;
2. state explicit inputs, outputs, and acceptance criteria;
3. inspect current code and evidence;
4. make the minimum necessary change;
5. add focused regression coverage for behavior changes;
6. run proportionate tests and integrity checks;
7. update the progress record;
8. commit one understandable unit;
9. continue automatically to the next safe unit.

Routine engineering does not require repeated operator confirmation. Stop only for a genuine
blocker or an approval gate.

Separate approval is required for:

- real funds or live-account exposure;
- starting or reloading the trading runtime;
- authenticated broker calls;
- orders, positions, leverage, margin, or account mutation;
- production secrets;
- destructive/data-loss actions;
- security-boundary changes;
- external paid services;
- legal/compliance decisions;
- merges;
- materially different architectural choices.

General authorization to continue does not silently grant these actions.

---

## 15. Commands for a receiving AI

Start with read-only discovery:

```bash
git status --short
git log -1 --oneline
git branch --show-current
find . -name AGENTS.md -print
sed -n '1,240p' AGENTS.md
sed -n '1,240p' tasks/00-right-path.md
sed -n '1,240p' docs/ROADMAP_INDEX.md
sed -n '1,120p' docs/LYNXION_PROGRESS_LEDGER.md
tail -240 docs/LYNXION_PROGRESS_LEDGER.md
```

Current local research verification entry points:

```bash
python scripts/verify_c35_candle_ledger.py
python scripts/verify_c35_funding_ledger.py
python scripts/verify_c35_signal_ledger.py
python scripts/check_c35_signal_throughput.py
python scripts/evaluate_c35_aggregate.py
python scripts/check_c33_checkpoint.py
```

Do not run `./lynxion`, `run_trading_system.py`, authenticated broker tools, or order demos solely
because they appear in this handoff. Determine the task authority and approval boundary first.

---

## 16. Questions a reviewer must answer

1. Are Git, data, test, runtime, and exchange claims current or explicitly dated?
2. Can each material claim be reproduced from a commit, input artifact, and command?
3. Are investor technical capability and economic profitability kept separate?
4. Can any signal bypass centralized risk and broker-backed admission?
5. Does every accepted position obtain visible valid protection or guaranteed unwind?
6. Is leverage/margin/account state authoritative and side-aware?
7. Are Spot and Futures position-management paths separated?
8. Are prospective boundaries genuinely unopened and immutable?
9. Are costs, temporal folds, uncertainty, breadth, concentration, and drawdown complete?
10. Is `NO_TRADE_DEFAULT` preserved when evidence is negative or insufficient?
11. Are failures preserved instead of tuned away?
12. Is any cleanup proven safe against dynamic/config/plugin discovery?

---

## 17. Correct current conclusion

The project is following a defensible direction because it now distinguishes technical capability
from economic proof, preserves negative evidence, uses preregistered forward cohorts, and keeps a
no-trade admission default while evidence is insufficient.

There are encouraging observations—particularly two positive C-35 outcomes and one strong completed
C-11 ETH outcome—but they are too few and concentrated to demonstrate durable edge. Engineering
integrity has improved materially, but current profitability, pilot readiness, production readiness,
and real-money suitability remain unproven.

The next correct action is not to declare success or tune the visible winners. It is to continue the
frozen prospective process, fix only verified correctness defects, reject failed candidates honestly,
and change information or strategy direction only at a documented evidence gate.

---

## 18. Copy-paste instruction for the receiving AI

```text
You are the senior AI engineer and quantitative reviewer continuing the Lynxion ETS project. Treat
this single-file handoff as orientation, not immutable live truth. Verify the current repository,
data, tests, processes, and any exchange state before making current claims. Read the repository's
AGENTS.md and tasks/00-right-path.md before taking action. Preserve strict task boundaries, minimal
changes, frozen candidate protocols, prospective boundaries, and NO_TRADE_DEFAULT. Separate the
technical investor-release verdict from the economic edge verdict. Do not claim profitability,
pilot readiness, runtime health, or broker protection from small samples or dated evidence. Do not
weaken gates after outcomes are visible. Do not start/reload runtime, call authenticated broker
paths, place orders, mutate accounts/positions, expose secrets, delete data, introduce paid services,
change security boundaries, merge, or make materially different architectural choices without the
applicable explicit approval. Identify the first unfinished bounded roadmap unit, verify its inputs
and acceptance criteria, complete it with proportionate tests and reproducible evidence, document
the result, and continue to the next safe unit unless a genuine blocker or approval gate is reached.
```

---

## 19. Repository references for deeper verification

This file is self-contained for orientation. When repository access exists, the following remain the
primary detailed records:

- `AGENTS.md`
- `tasks/00-right-path.md`
- `docs/ROADMAP_INDEX.md`
- `docs/LYNXION_PROGRESS_LEDGER.md`
- `docs/INVESTOR_RELEASE_EVIDENCE_INDEX.md`
- `docs/README_INVESTOR_RELEASE.md`
- `docs/README_AGENT_TECHNICAL_REVIEW.md`
- `tasks/research/edge-candidate-register-v10.md`
- `tasks/research/edge-candidate-register-v34.md`
- the latest task file and current Git history

When any summary conflicts with a frozen candidate preregistration, the preregistration governs that
candidate. When prose conflicts with reproducible current source/evidence, current source/evidence
governs.
