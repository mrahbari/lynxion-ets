# TASK-0100 — C-11 Prospective Funding Shadow Cohort

**Status:** IN PROGRESS — BOUNDARY FROZEN

## Objective

Collect and resolve severe negative-funding rebound observations prospectively without orders.

## Acceptance Criteria

- Boundary/register commit precedes every counted settlement.
- Collector is broker-free, idempotent, causal, and exact-bar/funding tested.
- Ledger distinguishes PENDING/COMPLETE/ERROR and never synthesizes fills.
- Recurring monitor updates the cohort independently of the engineering loop.
- Verdict remains COLLECTING until the frozen sample/stability gate is met.
