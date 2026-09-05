# TASK-0148 — Disconnected Exit-Evidence Chain Verification

**Status:** READY — TEST-ONLY, RUNTIME DISABLED

## Objective

Verify the complete TASK-0134/0143/0144/0147 evidence chain with real temporary snapshot and
ledger implementations before any runtime-wiring or prospective-data decision is considered.

## Frozen Boundary

1. Use only temporary test paths; no production snapshot or event ledger may be created.
2. Exercise the existing reconciliation closure selector with the existing history call and one
   exact `OPEN` identity captured through the existing identity contract.
3. Prove one complete terminal order creates exactly one valid `EXIT_FILL_OBSERVED` record and
   advances the matching identity to `TERMINAL_EVIDENCE_COMPLETE`.
4. Prove incomplete economics remain null, validate in the ledger, and advance only to
   `CLOSURE_OBSERVED`.
5. Prove replayed closure, process reconstruction, ambiguous identity, corrupt snapshot, duplicate
   event, ledger failure, and snapshot-write failure cannot create conflicting evidence or alter
   reconciliation's strategy, cooldown, journal, alert, history-query, or halt behavior.
6. Record explicit coverage counts for eligible, excluded, and failed observations.
7. Do not change runtime composition, broker calls, retry cadence, strategy, risk, trailing,
   leverage, symbols, thresholds, or account settings.

## Acceptance Criteria

- Real `PositionIdentitySnapshot` and `ExitEventLedger` are used together under `tmp_path`.
- The emitted file validates with deterministic identity/order linkage and no sensitive fields.
- Idempotency survives service reconstruction using persisted lifecycle state and deterministic
  event identity.
- Failure-injection tests demonstrate operational reconciliation remains unchanged.
- Focused and full suites pass and leave no production evidence artifacts.

## Progress

- Real temporary snapshot and ledger components now prove complete evidence persistence,
  null-preserving incomplete evidence, lifecycle-based restart idempotency, ambiguity rejection,
  corrupt-snapshot rejection, and ledger validation.
- Seventeen focused TASK-0143/0146/0147/0148 tests pass.
- The remaining sealed unit is reconciliation-selector failure injection and full-suite validation.

## Decision After Completion

TASK-0148 may establish repository readiness only. Enabling forward collection remains a separate
runtime/deployment approval gate, and no profit-lock policy candidate may be selected until a
prospective boundary and data-completeness gate are frozen before outcomes are observed.
