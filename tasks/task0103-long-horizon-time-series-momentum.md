# TASK-0103 — Long-Horizon Time-Series Momentum C-14

**Status:** IN PROGRESS — PROTOCOL FROZEN

## Objective

Evaluate a low-turnover 180-day directional signal with a fixed 28-day holding period on the
six-symbol native futures panel.

## Acceptance Criteria

- Commit the protocol before evaluating C-14 outcomes.
- Prove daily aggregation, shifted entry, holding period, and overlap behavior with tests.
- Keep primary and reverse-time samples separate.
- Apply realistic costs and a month-cluster confidence interval.
- Apply the frozen conjunctive gate without post-result tuning.
- Do not modify production, risk controls, symbol eligibility, or order handling.
