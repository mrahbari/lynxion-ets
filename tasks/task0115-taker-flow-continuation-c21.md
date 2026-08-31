# TASK-0115 — Aggressive Taker-Flow Continuation C-21

**Status:** COMPLETE — C-21 REJECTED

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

## Result

- Primary: 2,326 trades, -0.2086% funding-inclusive expectancy, PF 0.8384, and day-cluster 95% CI
  [-0.3855%, -0.0229%].
- All four folds were negative; only LONG and ETH were narrowly positive diagnostic cells.
- Five of six symbols and SHORT were negative; those opened cells are not promotable.
- Temporal reverse: 831 trades, -0.3853% expectancy, PF 0.6827.
- At 0.50% cost, primary expectancy was -0.4086%.
- Frozen verdict: **REJECT** with no reversal, threshold, horizon, or subgroup change.
