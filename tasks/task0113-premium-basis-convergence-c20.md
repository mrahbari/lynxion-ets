# TASK-0113 — Symmetric Premium-Basis Convergence C-20

**Status:** COMPLETE — C-20 REJECTED

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

## Result

- Primary: 1,264 trades, -0.2721% funding-inclusive expectancy and PF 0.8125.
- The day-cluster 95% CI was [-0.5595%, +0.0075%], crossing zero with a negative point estimate.
- All four folds, both sides, and all six symbols were negative.
- Price-only expectancy was -0.2940%; funding improved results by +0.0219% but did not create edge.
- Temporal reverse was positive (+0.2649%, PF 1.2297, N=490), demonstrating temporal instability
  rather than validating the negative primary sample.
- At 0.50% cost, primary expectancy was -0.4721%.
- Frozen verdict: **REJECT**. No one-sided, threshold, horizon, or subgroup promotion was admitted.
