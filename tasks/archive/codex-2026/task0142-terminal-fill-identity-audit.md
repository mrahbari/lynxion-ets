# TASK-0142 — Terminal Fill Identity Audit

**Status:** COMPLETE — IDENTITY GAP VERIFIED

## Objective

Determine whether the existing broker-reconciliation payload can emit a valid `EXIT_FILL_OBSERVED`
event and join it to TASK-0137 through TASK-0141 without new broker calls or guessed values.

## Findings

1. Reconciliation persists only a set of active symbols. After a position disappears it no longer
   has the entry price, position side, quantity, leverage, or manager `position_key` required by the
   exit-event contract.
2. The selected terminal order can provide order ID/type/status and sometimes `realizedProfit`.
   Fill price, executed quantity, fees, trigger price/basis, and fill time are not required by the
   current selection path and may be absent. Missing fields cannot be inferred.
3. Symbol plus latest terminal order is not a stable join key: re-entry, hedge-mode sides, multiple
   terminal orders, and restart timing can make the newest order belong to a different position.
4. Adding an observer directly to reconciliation now would either emit schema-invalid events or
   guess identity/economics, invalidating a cost-adjusted profit-lock comparison.
5. No authenticated broker call or runtime path was exercised during this audit.

## Verdict

`EXIT_FILL_OBSERVED` integration is BLOCKED until the position identity that exists while the
position is open survives closure and restart. The minimal safe route is a versioned, atomic local
identity snapshot populated only from already-fetched authoritative position data and consumed by
reconciliation; missing terminal economics must remain null or explicitly exclude the outcome.

## Next Boundary

TASK-0143 may specify and test the disconnected identity snapshot contract. It must not wire the
runtime, query the broker, emit fills, change reconciliation decisions, or create a prospective
boundary.
