# TASK-0110 — Book-Depth Imbalance C-18

**Status:** COMPLETE — C-18 REJECTED

## Objective

Evaluate exactly one causal order-book-depth imbalance hypothesis on the kept TASK-0109 panel.

## Acceptance Criteria

- Commit the complete C-18 protocol before opening condition-aligned price outcomes.
- Use only the latest complete snapshot strictly before each decision, with bounded staleness.
- Apply causal thresholds that exclude the current observation.
- Use next-open execution, actual funding, explicit fees/slippage, overlap rejection, temporal
  folds, day-cluster bootstrap, and concentration reporting.
- Apply the frozen conjunctive gate once without post-result slicing or parameter changes.
- No production, broker, risk, symbol-admission, trailing, or order behavior changes.

## Deliverables

- A tested standalone evaluator.
- A machine-readable C-18 holdout report.
- A KEEP/REJECT decision recorded without changing the frozen protocol.

## Result

- Primary: 2,154 trades, -0.3568% funding-inclusive expectancy, PF 0.7685, and day-cluster
  bootstrap 95% CI [-0.5689%, -0.1456%].
- All four folds, both sides, and all six symbols were negative at the primary cost.
- Price-only expectancy was -0.3456%; mean funding contribution was -0.0111%.
- Temporal reverse: 726 trades, -0.2313% expectancy, PF 0.8230.
- At 0.50% cost, primary expectancy fell to -0.5568%.
- Frozen verdict: **REJECT**. No post-result slice or threshold change was admitted.

No production, broker, order, trailing, symbol-admission, or risk behavior changed.
