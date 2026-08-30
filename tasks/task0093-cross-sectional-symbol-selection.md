# TASK-0093 — Cross-Sectional Symbol Selection C-05

**Status:** IN PROGRESS — PROTOCOL FROZEN

## Objective

Test whether dynamic relative-strength/weakness selection improves cost-adjusted conditional
returns across Lynxion's stored universe, without production mutation.

## Acceptance Criteria

- Register v4 is committed before evaluation output exists.
- Features, liquidity eligibility, ranks, and broad-market context use decision-time data only.
- Entry is next-bar open; fixed-horizon exit and costs are explicit.
- Four chronological folds, LONG/SHORT separation, confidence interval, cost sensitivity, and
  symbol concentration are reported.
- Portfolio/single-symbol limits and fold boundaries are respected.
- Leakage and execution semantics have focused regression tests.
- Decision is KEEP FOR FURTHER VALIDATION or REJECT; production remains unchanged.
