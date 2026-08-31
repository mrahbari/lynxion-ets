# TASK-0113 — Symmetric Premium-Basis Convergence C-20

**Status:** IN PROGRESS — C-20 PREREGISTERED, OUTCOMES UNOPENED

## Objective

Evaluate exactly one symmetric convergence hypothesis using the retained official premium-index
panel.

## Acceptance Criteria

- Commit the complete protocol before opening condition-aligned price outcomes.
- Use only a completed premium candle strictly before each decision.
- Apply causal thresholds excluding the current observation.
- Use next-open execution, actual funding, costs, overlap rejection, folds, bootstrap, and
  concentration gates.
- Evaluate once without alternate thresholds, horizons, one-sided variants, or subgroup filters.
- No production, broker, risk, trailing, symbol-admission, or order behavior changes.
