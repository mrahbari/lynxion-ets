# TASK-0146 — Terminal Evidence Extractor

**Status:** READY — DISCONNECTED IMPLEMENTATION

## Objective

Implement a pure, broker-agnostic extractor that joins one already-selected terminal order to one
exact identity record under TASK-0145's frozen admission rules.

## Sealed Boundary

1. Accept plain order/identity dictionaries and return a validated evidence object or an explicit
   exclusion reason.
2. Never query a broker, read/write a production file, import reconciliation/manager components, or
   mutate either input.
3. Require known order ID, explicit terminal position side, exact normalized symbol/side agreement,
   and identity lifecycle `OPEN`.
4. Preserve missing optional economics as null and mark completeness false; never convert absent or
   malformed values to zero.
5. Mark terminal completeness true only with authoritative fill price, quantity, realized PnL,
   fees, and exchange event time.
6. Cover malformed, ambiguous-side, mismatched, incomplete, complete, and input-immutability cases.

## Non-Goals

- No reconciliation integration, identity lifecycle write, exit-ledger event, broker call, runtime
  wiring, historical import, prospective boundary, strategy change, or profitability conclusion.
