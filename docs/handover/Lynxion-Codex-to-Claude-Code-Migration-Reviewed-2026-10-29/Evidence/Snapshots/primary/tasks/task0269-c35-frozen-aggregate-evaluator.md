# TASK-0269 — C-35 frozen aggregate evaluator

## Scope

Connect the preregistered aggregate math to every frozen economic gate while preserving complete
sealing until source-bound minimum coverage passes.

## Contract

- Return coverage-only `COLLECTING/SEALED` output before the minimum gate.
- After unsealing, compute primary/stress expectancy, PF, clustered bootstrap, both sides, symbol
  breadth, concentration, compounded drawdown, and four chronological folds exactly once.
- Any failed completed gate is `REJECT`; a full pass is only
  `KEEP_FOR_SEPARATE_VST_REVIEW`, never deployment authorization.
- Require source-bound event integrity before any economics open.

## Evidence

Focused tests cover live empty sealing, a full synthetic pass, and deterministic rejection when a
completed side gate fails. The live cohort remains sealed with zero outcomes.

## Verdict

`KEEP — FROZEN AGGREGATE EVALUATOR READY; LIVE ECONOMICS SEALED`.
