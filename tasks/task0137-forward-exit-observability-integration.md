# TASK-0137 — Forward Exit Observability Integration

**Status:** READY — REPOSITORY-ONLY, RUNTIME DISABLED

## Objective

Connect TASK-0134's validated exit-event ledger to ActivePositionManager through an injectable
observer so future authorized VST runs can produce causal profit-lock evidence without changing any
exit decision or enabling collection in the current runtime.

## Sealed Implementation Boundary

1. Add an optional observer dependency to ActivePositionManager. Its default is disabled and must
   preserve current behavior byte-for-byte apart from internal no-op calls.
2. Emit deterministic payloads for `POSITION_OBSERVED` and `MANAGER_EVALUATED`, including explicit
   `NO_ACTION`, authoritative per-position leverage, thresholds, state before/after, and a stable
   evaluation/position key.
3. Wrap each existing stop synchronization attempt with `STOP_REPLACE_REQUESTED` and
   `STOP_REPLACE_RESPONDED` observations. Do not add a request, retry, visibility query, or state
   mutation.
4. Do not claim `STOP_VISIBILITY_VERIFIED` or `STATE_COMMITTED` until the existing broker path
   supplies genuine visibility evidence. Missing coverage remains explicit.
5. Observer/ledger failure must be logged and counted but cannot delay, reject, repeat, or alter a
   protective stop action.
6. Do not create a prospective boundary, import historical records, instantiate a production
   ledger, or enable the observer in any composition root. Runtime enablement is a separate gate.

## Required Tests

- Disabled observer preserves current action count, stop prices, and broker call count.
- Enabled fake observer receives one position and one manager-evaluation event per eligible
  evaluation, including `NO_ACTION`.
- Missing/malformed authoritative leverage produces an observation/error and no stop mutation.
- Every existing stop-sync attempt produces exactly one request and one response event without an
  extra broker call.
- Observer exceptions do not change the stop result or generate a retry.
- No production ledger file exists after the focused and full suites.

## Non-Goals

- No threshold, distance, leverage, sizing, symbol, entry, exit, retry, or broker behavior change.
- No runtime start/reload, deployment, order, authenticated endpoint, or historical backfill.
- No profit-lock candidate, counterfactual outcome, or profitability claim is opened by this task.
