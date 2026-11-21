# TASK-0200 — Paired per-position outcome economics

## Scope

Implement pure cost-adjusted economics for one already linked baseline/candidate pair.
Do not aggregate positions, inspect cohort results, bootstrap, or issue a verdict.

## Result

- LONG/SHORT price return, entry fee, authoritative realized baseline exit commission,
  candidate expected exit fee, side-signed funding, and frozen primary/stress slippage
  are applied at authoritative 10x leverage.
- A candidate that does not exit early inherits the authoritative terminal price and fee;
  an earlier shadow exit uses its causal executable mark and preregistered fee schedule.
- Primary and stress paired deltas are emitted per position only.
- Non-finite economics, negative costs, invalid prices, or non-10x leverage fail closed.

## Boundary

Only synthetic test fixtures were evaluated. Aggregate prospective outcomes remain
unopened until the TASK-0189 minimum coverage gate is satisfied.

## Next

TASK-0201 binds candidate state-machine fills to funding windows and this per-position
calculator without exposing aggregate results.
