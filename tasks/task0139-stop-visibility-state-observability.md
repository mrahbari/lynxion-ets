# TASK-0139 — Stop Visibility and State Observability

**Status:** IN PROGRESS — REPOSITORY-ONLY, RUNTIME DISABLED

## Objective

Complete the stop-replacement causal chain by preserving genuine evidence from the manager's
existing pending-order verification and linking the already-existing local state commit to that
evidence, without changing broker or exit behavior.

## Sealed Implementation Boundary

1. Replace the internal boolean-only verification result with structured evidence containing the
   matched exchange order ID, actual visible stop price, and observation time. Do not add or remove
   a poll, delay, broker call, order, cancellation, or retry.
2. Preserve `_sync_sl_to_exchange`'s public boolean result and every caller's mutation behavior.
3. When the optional observer is enabled, emit exactly one `STOP_VISIBILITY_VERIFIED` for a matched
   stop or one `STOP_VISIBILITY_FAILED` after the existing verification loop is exhausted.
4. Link visibility to the corresponding `STOP_REPLACE_RESPONDED` event. Emit `STATE_COMMITTED` only
   from the caller after its existing state mutation, linked to verified visibility evidence.
5. Observer failures must remain logged/counted and cannot change acceptance, verification,
   mutation, sleep, or retry behavior.
6. Keep the canonical singleton and every composition root observer-free. Do not instantiate a
   production ledger, set a prospective boundary, import history, or enable runtime collection.

## Required Tests

- Structured verification identifies the exact matching order and actual visible stop price.
- Verified and failed visibility events are causally linked and do not change pending-order calls.
- State-commit events occur only after successful existing mutation and reference verified evidence.
- Rejected/invisible stops never emit `STATE_COMMITTED`.
- Observer exceptions do not change stop result, retry count, or manager state.
- Focused and full suites create no production ledger file.

## Non-Goals

- No restart-hydration event, exit-fill integration, runtime wiring, threshold change, strategy
  change, order placement beyond existing mocked tests, or profitability conclusion.

## Implementation Progress

- The existing verifier now returns the matched exchange order ID, actual visible stop price, and
  UTC observation time while `_sync_sl_to_exchange` retains its boolean result.
- Accepted attempts now emit a causally linked verified/failed visibility event after the broker
  response. Focused tests preserve the existing broker request and one-poll success / three-poll
  exhaustion counts; observer failure still cannot generate a retry.
- Caller-side state-commit linkage remains.
