# TASK-0100 — C-11 Prospective Funding Shadow Cohort

**Status:** IN PROGRESS — COLLECTOR AND 8H MONITOR ACTIVE

## Objective

Collect and resolve severe negative-funding rebound observations prospectively without orders.

## Acceptance Criteria

- Boundary/register commit precedes every counted settlement.
- Collector is broker-free, idempotent, causal, and exact-bar/funding tested.
- Ledger distinguishes PENDING/COMPLETE/ERROR and never synthesizes fills.
- Recurring monitor updates the cohort independently of the engineering loop.
- Verdict remains COLLECTING until the frozen sample/stability gate is met.

## Runtime Evidence

- Boundary commit: `921a772`, before the first collector run.
- First update: 2026-08-30 09:34:24 UTC; N=0, verdict `COLLECTING`.
- Zero pre-boundary records were imported and no settlement after the boundary had yet qualified.
- Four focused causality/overlap/minimum-sample tests passed; full suite: 680 passed and 1
  optional layering test skipped.
- App heartbeat `c11-funding-shadow-monitor` is ACTIVE every eight hours. It runs only the
  public-data shadow updater and explicitly prohibits broker/order/production mutations.

This task remains open by design while engineering proceeds independently.
