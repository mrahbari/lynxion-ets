# TASK-0141 — Restart Hydration Observability

**Status:** COMPLETE — REPOSITORY-ONLY, RUNTIME DISABLED

## Objective

Emit genuine restart-hydration evidence from ActivePositionManager's existing pending-stop read
without changing stop selection, manager state, broker calls, or runtime composition.

## Sealed Implementation Boundary

1. When the existing Stage 0 pending-order read selects a stop with a positive price, emit one
   `POSITION_HYDRATED` event containing the selected exchange order ID, recovered stop price,
   authoritative position leverage, and `hydration_source="BINGX_PENDING_ORDERS"`.
2. Record whether the existing logic classified the recovered stop as a breakeven/profit lock and
   include manager state only after the existing hydration mutations.
3. Do not change which stop is selected, add a query/retry, reorder Stage 0, or synthesize a prior
   manager decision, request, visibility event, or state commit.
4. Observer failure remains isolated and cannot change hydration, later stop evaluation, or broker
   call count.
5. Keep every composition root disabled; create no ledger, prospective boundary, or historical
   observation.

## Required Tests

- Existing stop hydration emits one event with exact order ID/price/source and post-hydration state.
- Non-positive or absent stops emit no hydration event and preserve current fallback behavior.
- Observer exception does not alter hydrated state or broker calls.
- Existing restart, observer, and full regression suites pass without creating a production ledger.

## Non-Goals

- No exit-fill integration, cross-component identity redesign, runtime wiring, threshold change,
  broker behavior change, or profitability conclusion.

## Result

- Existing positive stop hydration emits one `POSITION_HYDRATED` event with the exact selected
  order identity, recovered price, authoritative leverage, source, existing profit-lock
  classification, and post-hydration manager state.
- Absent/non-positive stops emit no hydration event. Observer exceptions remain isolated and do
  not change state or broker-call counts.
- Thirty-three focused regressions and the full 801-test suite pass with one optional import-linter
  skip. No production ledger file was created and runtime remains disabled.
