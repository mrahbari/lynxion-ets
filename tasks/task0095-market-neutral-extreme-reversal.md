# TASK-0095 — Market-Neutral Extreme Reversal C-06

**Status:** IN PROGRESS — PROTOCOL FROZEN

## Objective

Evaluate C-06 on the integrity-checked aligned futures panel without production mutation.

## Acceptance Criteria

- Register v5 is committed before evaluation output.
- Feature, rolling-threshold, ranking, and fill semantics are point-in-time and tested against
  future mutation.
- Both legs enter next-open, exit after four bars, and include frozen costs.
- Pair/leg metrics, four folds, sides, symbols, confidence interval, dispersion buckets, and
  cost sensitivity remain separable.
- Decision is KEEP FOR FURTHER VALIDATION or REJECT under the frozen gate.
