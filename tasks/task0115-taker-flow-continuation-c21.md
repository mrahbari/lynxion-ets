# TASK-0115 — Aggressive Taker-Flow Continuation C-21

**Status:** IN PROGRESS — C-21 PREREGISTERED, OUTCOMES UNOPENED

## Objective

Evaluate exactly one causal continuation hypothesis based on completed four-hour aggressive taker
buy/sell quote flow.

## Acceptance Criteria

- Commit the complete protocol before opening condition-aligned outcomes.
- Require all 16 native 15-minute bars strictly before each decision; no fill.
- Use a causal threshold excluding the current observation.
- Preserve next-open/24h execution, funding, costs, overlap, folds, bootstrap, and concentration.
- Evaluate once without reversal, alternate horizons, thresholds, or subgroup promotion.
- No production, broker, risk, trailing, symbol-admission, or order behavior changes.
