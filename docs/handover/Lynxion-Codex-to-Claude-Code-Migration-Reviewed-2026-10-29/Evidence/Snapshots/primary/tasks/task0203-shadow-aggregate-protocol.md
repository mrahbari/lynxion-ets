# TASK-0203 — Frozen shadow aggregate protocol

## Scope

Freeze the aggregate evaluation interface behind TASK-0202 without calculating or
exposing any metric.

## Result

- Position-clustered bootstrap is frozen at 10,000 resamples, seed 20260907, and 95% CI.
- Four folds are contiguous equal-count blocks ordered by terminal UTC.
- PF threshold is 1.10; expected shortfall is the worst 5%, with at most 10% relative
  worsening; drawdown uses equal-weight cumulative net return peak-to-trough.
- Top-symbol exclusion is selected by total paired primary contribution.
- The exact per-position primary/stress schema is admitted only after every coverage
  gate passes. Protocol drift, count mismatch, duplicate identity, or schema drift fails.
- Successful admission explicitly exposes no metric.

## Boundary

No prospective record was read and no aggregate result, fold, bootstrap, or verdict was
calculated. Tests use synthetic interfaces only.

## Next

TASK-0204 implements the deterministic aggregate evaluator against synthetic fixtures,
with a hard coverage-gate check before reading economic fields.
