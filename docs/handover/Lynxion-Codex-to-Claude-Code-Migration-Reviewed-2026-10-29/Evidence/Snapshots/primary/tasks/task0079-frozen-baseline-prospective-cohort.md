# TASK0079 — Frozen Baseline Prospective Cohort

**Status:** PENDING

## Scope

Collect a new, fully attributable cohort after TASK0077 deployment. Generate
read-only edge reports at 30, 60, and 100 completed trades.

## Acceptance Criteria

- Explicit deployment timestamp defines the cohort boundary.
- No incomplete attribution row is used to claim edge.
- Reports include net expectancy, PF, median trade, side/regime cells, and concentration.
- No strategy/risk configuration is altered during collection.
