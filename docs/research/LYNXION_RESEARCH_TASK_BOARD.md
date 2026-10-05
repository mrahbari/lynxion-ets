# Lynxion research task board

Operational queue over [the canonical research backlog](LYNXION_RESEARCH_BACKLOG.md), not a new scientific protocol. No future outcomes or trading activity are authorized by this board. Statuses and evidence below were verified on **2026-10-05 10:16 UTC** at starting HEAD `8b3ab1e`.

| Dashboard | Current state |
|---|---|
| Current active task | TASK-01 Pilot-2 pre-start integrity; TASK-07 liquidation/OI/OBI reconciliation |
| Current Pilot-2 status | PRE-START SUPERVISION; frozen 2026-10-06 00:00 to 2026-10-13 00:00 UTC; LaunchAgent and child PID 38441 running; 0 formal sessions; ~50 GiB available |
| Next ready task | TASK-08 frozen/collecting studies status audit |
| Done / remaining / parked or blocked queue tasks | 5 / 6 / 0 (the scientific R25 lead remains PARKED; V3 requires operator decision) |

Status vocabulary: `TODO`, `READY`, `IN_PROGRESS`, `WAITING_EXTERNAL`, `DONE`, `PARKED`, `BLOCKED_BY_SCIENTIFIC_DECISION`, `BLOCKED_BY_DATA`, `CLOSED`. Pilot-2 always preempts backlog work. `Latest commit` is `NONE` until that task's own deliverable is committed. Existing C-11/C-35 working-tree writes belong to independent collectors and must not be staged or altered here.

| ID / priority / family | Task and status | Dependency | Authorized scope / explicitly forbidden | Start / latest commit | Evidence or deliverable; next action; blocker; operator decision? |
|---|---|---|---|---|---|
| TASK-01 / P0 / observed microstructure | Monitor frozen Pilot-2; `IN_PROGRESS` | Frozen contract and activation | Local integrity/liveness and contract recovery only / no outcomes, backfill, boundary/source change, account or orders | `8b3ab1e` / `NONE` | [Contract](../MICROSTRUCTURE_DATA_PILOT2_CONTRACT.md), [activation](../MICROSTRUCTURE_DATA_PILOT2_ACTIVATION.json); check at start and during window, final report at stop; time boundary; NO unless semantics change |
| TASK-02 / P1 / research governance | Reconcile R01–R26 and operational board; `DONE` | Existing reports and exact verdicts | Documentation/status verification / no study rerun or verdict reinterpretation | `8b3ab1e` / `17c511b` + this reconciliation commit | [Backlog](LYNXION_RESEARCH_BACKLOG.md) and this board; exact verdicts retained, stale R18 successor corrected; none; NO |
| TASK-03 / P2 / extreme-mover selection | Point-in-time public data feasibility; `DONE` | R22 and source provenance | Universe/listings/rank/volume/liquidity/sample feasibility / no returns, thresholds or new study | `8b3ab1e` / this feasibility commit | [Feasibility](CROSS_SECTIONAL_EXTREME_MOVER_FEASIBILITY.md): `EXTREME_MOVER_DATA_PARTIAL`; preserve unqualified historical universe; none; NO |
| TASK-04 / P2 / extreme-mover selection | Outcome-blind information contract; `DONE` | TASK-03 partial feasibility | Classify fields and time-T availability / no rule thresholds or outcomes | `8b3ab1e` / this contract commit | [Information contract](CROSS_SECTIONAL_EXTREME_MOVER_INFORMATION_CONTRACT.md); no capture activated; no blocker; YES for hypothesis/activation |
| TASK-05 / P3 / external methodology | Bounded Qullamaggie review; `DONE` | Public original sources | Method taxonomy and research discipline / no stock thresholds or profit transfer | `8b3ab1e` / this review commit | [Review](QULLAMAGGIE_METHOD_RESEARCH_REVIEW.md); transfer only method discipline; no blocker; NO |
| TASK-06 / P3 / prospective annotation | Design inactive all-candidate protocol; `DONE` | R24 draft | Pre-outcome schema, immutable evidence, separate labels / no collection or outcome labels | `8b3ab1e` / this protocol commit | [Protocol](MANUAL_PROSPECTIVE_ANNOTATION_PROTOCOL.md); no collection activated; inclusion rule not frozen; YES for activation |
| TASK-07 / P4 / liquidation-OI-OBI | Reconcile prior information only; `IN_PROGRESS` | R08, R09, R12, R25, C-33 | Evidence/provenance map / no experiment or unpark | `8b3ab1e` / `NONE` | `LIQUIDATION_OI_OBI_RECONCILIATION.md`; preserve PARKED status; no blocker; YES to unpark |
| TASK-08 / P4 / frozen studies | Status-only audit; `READY` | Frozen protocols | Read existing status/gates / no collector repair, outcome opening or definition change | `8b3ab1e` / `NONE` | `FROZEN_STUDIES_STATUS.md`; audit C-11/C-33/C-35/F4; no blocker; NO |
| TASK-09 / P4 / sibling selection | Source-vs-inference evidence map; `READY` | R01–R03 and R20 | Read existing forensic work / no new profitability study | `8b3ab1e` / `NONE` | `SIBLING_RESEARCH_EVIDENCE_MAP.md`; reconcile provenance; no blocker; NO |
| TASK-10 / P4 / information sets | Consolidated coverage map; `TODO` | TASK-03, 07, 09 | Compare observed/proxy/default and tested scope / no new signal | `8b3ab1e` / `NONE` | `LYNXION_INFORMATION_SET_MAP.md`; wait for source maps; no blocker; NO |
| TASK-11 / P5 / scientific decision | Outcome-blind next-experiment package; `TODO` | Earlier backlog tasks | Compare novelty/readiness/burden only / no V3 selection or outcomes | `8b3ab1e` / `NONE` | `NEXT_EDGE_EXPERIMENT_DECISION_PACKAGE.md`; wait for prior tasks; scientific selection deferred; YES to start a new Edge study |

The queue is not a mandate to stay busy. Once authorized backlog tasks are complete, retain low-cost Pilot-2 monitoring until its frozen stop, then commit the measurement report and final handover. A negative, partial, or unavailable measurement remains evidence, not permission to rescue a cohort.
