# TASK-0134 — Exit Event Ledger Writer

**Status:** PLANNED — DISCONNECTED IMPLEMENTATION ONLY

## Objective

Implement and test the append-only schema writer and validator from TASK-0133 without connecting it
to ActivePositionManager, a broker, or any execution path.

## Acceptance Criteria

- Validate required common and event-specific fields, UTC timestamps, finite numerics, sides, unique
  event IDs, and causal references.
- Append atomically to daily JSONL with flush/fsync and process-local locking.
- Reject secrets and account-identifying fields.
- Test corruption, duplicates, invalid references, concurrent append, and deterministic validation.
- Do not import historical events or alter production risk, trailing, admission, leverage, or orders.
