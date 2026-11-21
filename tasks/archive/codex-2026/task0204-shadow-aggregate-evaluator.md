# TASK-0204 — Deterministic shadow aggregate evaluator

## Scope

Implement the frozen aggregate evaluator against synthetic fixtures, with coverage
admission before any economic field access. Do not read prospective records.

## Result

- Computes paired mean/position-bootstrap lower bound, aggregate and four-fold
  expectancy/PF, stress improvement, both-side improvement, top-symbol exclusion,
  equal-weight drawdown, and worst-5% expected shortfall.
- Coverage failure returns `COLLECTING` with no metrics and does not touch economics.
- Once coverage is open, every frozen gate passing returns
  `KEEP_FOR_SEPARATE_DEPLOYMENT_REVIEW`; any failure returns `REJECT` without retuning.
- Bootstrap uses the frozen seed and 10,000 position resamples.

## Boundary

Only synthetic records were evaluated. No active/prospective cohort result was opened.

## Next

TASK-0205 performs an independent implementation review and full regression suite before
the evaluator hash is considered frozen for future prospective use.
