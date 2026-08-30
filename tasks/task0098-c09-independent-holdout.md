# TASK-0098 — C-09 Independent Pre-2023 Holdout

**Status:** IN PROGRESS — HYPOTHESIS AND DATA BOUNDARY FROZEN

## Objective

Acquire an untouched futures panel and test the C-08-derived long/BTC-positive hypothesis
without reusing its discovery folds.

## Acceptance Criteria

- Register v8 and data dates are committed before acquisition/evaluation.
- Dataset is isolated, checksummed, exactly aligned, and integrity-checked.
- Features, threshold, next-open entry, holding horizon, costs, and folds are causal/tested.
- Fold/symbol/context/spread/cost metrics and bootstrap CI remain separable.
- Explicit KEEP FOR PROSPECTIVE VST or REJECT; never direct production promotion.
