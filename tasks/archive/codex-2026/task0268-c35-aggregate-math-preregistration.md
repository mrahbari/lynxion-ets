# TASK-0268 — C-35 aggregate-math preregistration

## Scope

Implement deterministic statistical primitives before any C-35 outcome exists, without opening
live aggregate economics.

## Frozen implementation details

- Arithmetic mean over completed position returns.
- Profit factor is positive-return sum divided by absolute negative-return sum; positive-only is
  infinity and all-zero is undefined.
- Drawdown compounds returns from unit equity in chronological order.
- Daily-cluster bootstrap resamples UTC exit-date clusters with replacement, retains every trade
  in each selected cluster, uses 10,000 samples, seed `350035`, and a linearly interpolated 2.5th
  percentile.
- Four folds are contiguous groups of ordered represented UTC ISO weeks; entry and exit must map
  to the same fold or evaluation fails closed.

## Evidence

Focused tests freeze the metric, drawdown, clustered bootstrap, and fold semantics. No live outcome
or aggregate result was opened.

## Verdict

`KEEP — AGGREGATE MATH FROZEN BEFORE FIRST OUTCOME`.
