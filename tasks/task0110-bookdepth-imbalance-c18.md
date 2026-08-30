# TASK-0110 — Book-Depth Imbalance C-18

**Status:** IN PROGRESS — C-18 PREREGISTERED, OUTCOMES UNOPENED

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
