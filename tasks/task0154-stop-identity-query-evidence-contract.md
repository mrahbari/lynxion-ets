# TASK-0154 — Stop Identity and Query-Evidence Contract

**Status:** IN PROGRESS — STRUCTURED QUERY EVIDENCE COMPLETE

## Objective

Correct the confirmed local observability defects from TASK-0153 without changing stop thresholds,
order intent, retry cadence, symbol admission, account settings, or runtime activation.

## Minimal Repository Scope

1. Preserve the placement response's exchange order ID in `STOP_REPLACE_RESPONDED`; absence remains
   explicit and must not be fabricated.
2. Add a structured pending-order query result that distinguishes success-empty, exchange rejection,
   transport/parser failure, and valid returned orders while preserving the existing public list
   method for unrelated callers.
3. When placement provides an order ID, require visibility to match that exact ID before committing
   manager state. Attribute-only matching is allowed only when placement identity is genuinely
   unavailable and must be labelled as fallback evidence.
4. Emit query status, match mode, returned order identity, and a non-sensitive failure reason in the
   existing visibility event. Never expose request headers, account identifiers, keys, or signatures.

## Mandatory Failure-Injection Tests

- `code=0` with missing order ID remains explicit and never invents identity.
- Nonzero API response, exception, malformed payload, and success-empty are distinguishable.
- Wrong order ID with otherwise matching type/side/price is not exact visibility.
- Exact ID with wrong symbol/side/position side/type/price is rejected.
- Exact ID plus all frozen attributes emits verified evidence and permits one state commit.
- Observer/query-evidence failure cannot add broker calls, retries, state commits, or successful
  action reports.
- Disabled/default composition preserves existing behavior and produces no evidence files.

## Boundary

Repository implementation and disconnected tests only. Do not reload the runner, call a broker,
place/cancel/replace orders, change policy, or activate the correction. Any runtime deployment is a
separate approval gate after focused and full suites pass.

## Implementation Evidence

- The first unit adds a structured pending-order result with distinct `OK`, `API_ERROR`,
  `MALFORMED`, and `EXCEPTION` states. Error evidence contains only exchange code or exception type;
  response/exception text is not retained.
- The legacy list-returning method delegates to the structured method and preserves its existing
  empty-list failure behavior for unrelated callers.
- Twelve focused TASK-0139/0153/0154 tests pass. No runtime was reloaded and no broker was called.
