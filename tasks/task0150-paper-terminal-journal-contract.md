# TASK-0150 — Paper Terminal Journal Contract

**Status:** READY — REPOSITORY-ONLY

## Objective

Resolve the remaining verified `record_result` contract mismatch in the multi-broker simulated-fill
path so paper/test evidence cannot remain falsely in-flight after an admitted simulated terminal
result.

## Sealed Boundary

1. Characterize the existing paper authorization result and journal lifecycle call counts.
2. Replace only the unavailable terminal method with the journal's existing compatible transition.
3. Preserve authorization, simulation, fill identity, pending-order behavior, return value, and all
   real-send branches exactly.
4. Journal absence or write failure remains unable to affect execution-path behavior.
5. Add focused regression and failure-injection tests, then run the full suite.

## Non-Goals

No paper or real order may be placed. No runtime, broker/API, account, strategy, risk, leverage,
trailing, symbol, prospective evidence, or profitability setting may change.
