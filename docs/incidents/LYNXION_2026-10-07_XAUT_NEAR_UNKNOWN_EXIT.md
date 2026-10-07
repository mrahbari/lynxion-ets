# XAUTUSDT / NEARUSDT unknown-exit alerts — evidence checkpoint

Status: **UNRESOLVED; safety cooldown retained**. This is a read-only forensic checkpoint, not a change to trading behavior. Starting HEAD: `c117dec`.

## Facts

- The operator received `EXCHANGE POSITION CLOSED` alerts for XAUTUSDT and NEARUSDT with `UNKNOWN — closing order not identified`, `N/A` realized PnL, and a safety cooldown. The local active-symbol journal no longer lists either symbol at inspection. This establishes a reported closed-position transition, not the exit order type, fill price, or realized result.
- `BrokerReconciliationService._process_position_closures` requests the last 20 orders and accepts only a `FILLED` order whose update time is between the preceding active-position observation and the closure observation, and whose type is `STOP_MARKET`, `TAKE_PROFIT_MARKET`, `LIQUIDATION`, or is marked reduce-only. If no order passes, it records an unverified-exit cooldown and sends this alert (`infrastructure/execution/broker_reconciliation.py`).
- The BingX `get_order_history` implementation returns `[]` on a nonzero API code, unexpected payload, or exception without preserving the failure reason for reconciliation (`infrastructure/brokers/adapters/bingx_adapter.py`). Thus an empty result is not proof that no closing order exists.
- The active runtime has no per-request history-query evidence for these two closures in the inspected local artifacts. No authenticated account query was performed during this investigation.

## Inference / hypotheses / unknowns

- **Inference:** At least one matching criterion failed or the history request yielded no usable orders. The alert cannot distinguish these cases.
- **Hypotheses, unproven:** delayed/missing history response; order older than the 20 returned; exchange order type/field mismatch; closing-order timestamp outside the narrow observation window; position-side/netting ambiguity; API error hidden as `[]`.
- **Unknown:** exact closing order IDs, exit mechanism, realized PnL, whether either exit was profitable, and which hypothesis applies to each symbol. Do not infer TP or SL from the alert or a chart.

## Minimum next work

1. In an isolated hardening worktree, add networkless evidence tests for empty/error/malformed history, accepted exit types, time-boundary behavior, and repeated position transitions.
2. Add status-bearing order-history diagnostics without changing order submission or cooldown policy; preserve API code/type and query/response timing without secrets. Independently review any diff touching reconciliation or execution behavior.
3. Compare the resulting local evidence with an operator-approved, read-only account/order-history query if needed. No such query is authorized by the current monitoring scope. Only verified terminal evidence may clear or reclassify an existing safety cooldown.
4. Do not deploy a reconciliation or cooldown change to the active runner until its trading-behavior impact and Pilot-2 isolation are reviewed and authorized.

## Related work and boundaries

- Pilot-2 public microstructure collection is independent and untouched. Its boundary remains 2026-10-06 00:00 to 2026-10-13 00:00 UTC.
- The separate journal-only candidate at isolated hardening commit `478acdc` addresses stale SL/TP journal provenance, not proof of these closing-order outcomes; it is not deployed.
- Entry-latency timing instrumentation is isolated in hardening commits `3515233`, `83e37b7`, and `48e250d`; it is not deployed and does not resolve unknown exits.
