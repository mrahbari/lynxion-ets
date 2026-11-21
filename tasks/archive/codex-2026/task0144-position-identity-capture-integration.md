# TASK-0144 — Position Identity Capture Integration

**Status:** COMPLETE — REPOSITORY-ONLY, RUNTIME DISABLED

## Objective

Connect TASK-0143's identity snapshot to eligible ActivePositionManager observations through an
optional dependency so the exact open-position identity can survive closure and restart, without
enabling runtime persistence or changing trading behavior.

## Sealed Implementation Boundary

1. Add an optional identity-store dependency to ActivePositionManager; default `None` in the
   canonical singleton and every composition root.
2. After symbol, side, entry, quantity, current price, and authoritative leverage are validated,
   upsert one `OPEN` identity using the manager's existing `position_key` and observer run ID.
3. Reuse an exact existing record only when symbol, side, position key, entry, and run identity
   agree. Ambiguous or conflicting identity fails observationally and cannot block or alter manager
   evaluation.
4. Update only quantity, last-observed UTC time, and genuinely present exchange identifiers. Never
   guess leverage, identifiers, timestamps, or a prior lifecycle transition.
5. Add no broker call, query, retry, delay, order, state mutation, or production file. Identity-store
   exceptions are logged/counted separately from exit-observer failures and cannot change actions.
6. Do not connect reconciliation, emit an exit fill, freeze a prospective boundary, or enable a
   store in runtime.

## Required Tests

- Disabled identity capture preserves action and broker-call counts and creates no file.
- Enabled temporary store creates one deterministic `OPEN` identity from authoritative inputs.
- Repeated evaluation advances last-observed time without duplicating identity.
- Conflict, ambiguity, corruption, and store-write failure do not change manager decisions or
  generate broker retries.
- Existing observer, identity, restart, and full suites pass without a production snapshot.

## Non-Goals

- No reconciliation integration, terminal-fill event, runtime wiring/deployment, threshold or
  strategy change, authenticated broker call, historical backfill, or profitability conclusion.

## Result

- ActivePositionManager accepts an optional identity store and records validated open-position
  identity after authoritative inputs are available. Repeated observations update quantity/time
  without duplicating the deterministic record.
- Disabled, corrupt, conflicting, ambiguous, and write-failure paths remain observational only;
  they do not change actions or broker-call counts. The canonical singleton remains disabled.
- Eleven focused identity/capture tests and the full 812-test suite pass with one optional
  import-linter skip. No production identity snapshot or exit ledger was created.
