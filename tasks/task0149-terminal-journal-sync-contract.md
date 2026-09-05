# TASK-0149 — Terminal Journal Synchronization Contract

**Status:** READY — REPOSITORY-ONLY

## Objective

Resolve the verified contract mismatch between reconciliation's terminal-close synchronization and
`LiveOrderJournal` without changing broker queries, trading behavior, closure classification, or
the TASK-0148 evidence observer.

## Sealed Boundary

1. Characterize the journal's existing state machine and supported terminal-write methods.
2. Prove the current `record_result` call is unavailable and therefore always enters its caught
   warning path.
3. Select the smallest compatible correction using the journal's existing terminal transition;
   do not add a parallel state machine or infer an order reference.
4. Unknown closing order IDs or unmatched journal identities remain fail-closed and observational.
5. Preserve the exact history query, selector, cooldown, strategy, alert, halt, and observer calls.
6. Add focused success, unmatched, duplicate, and failure-injection tests, then run the full suite.

## Non-Goals

No runtime wiring, broker/API call, order, strategy, risk, leverage, trailing threshold, symbol
setting, historical rewrite, or prospective outcome is permitted.

## Progress

- `LiveOrderJournal` now resolves an exact lifecycle `order_ref` from one unique exchange order ID;
  missing and ambiguous matches fail closed.
- Reconciliation uses the existing `record_terminal` transition only after exact resolution. It no
  longer calls the nonexistent `record_result` method or treats an exchange order ID as a journal
  lifecycle identity.
- Twenty-one focused journal/reconciliation/observer tests pass. Full-suite validation remains.
- A separate pre-existing `record_result` call in multi-broker order execution is outside this
  task's reconciliation boundary and remains deferred for independent characterization.
