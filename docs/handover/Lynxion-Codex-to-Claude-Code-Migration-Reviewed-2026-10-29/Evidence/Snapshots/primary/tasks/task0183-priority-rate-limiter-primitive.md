# TASK-0183 — Bounded FIFO priority rate-limiter primitive

## Scope

Implement the TASK-0179 admission primitive in the existing single token bucket.
Do not wire priority into BingX calls, change capacity, or alter runtime behavior.

## Result

- Existing ordinary callers retain blocking admission by default.
- Priority callers queue FIFO ahead of ordinary waiters while consuming the same
  aggregate tokens.
- Optional monotonic timeout returns explicit success/failure; timed-out priority
  waiters are removed without blocking the queue.
- No second limiter or reserved capacity can exceed the configured exchange budget.

## Next

TASK-0184: wire bounded priority only to stop-order mutation admission and expose queue
timing, with adapter and manager failure-injection tests. Remain repository-only.
