# TASK-0145 — Reconciliation Terminal-Field Admission

**Status:** COMPLETE — FIELD CONTRACT FROZEN

## Objective

Freeze which values from the existing terminal-order history and identity snapshot may enter
forward exit evidence without adding broker calls or inferring missing economics.

## Findings and Admission Rules

- A terminal order is eligible only when the existing reconciliation selector already chooses it,
  its `orderId` is known, and `positionSide` is explicitly `LONG` or `SHORT`.
- Identity resolution must use normalized symbol plus explicit position side and return exactly one
  `OPEN` record. Missing, conflicting, corrupt, or ambiguous identity excludes observation but must
  not alter operational reconciliation.
- Admit fill price only from positive finite `avgPrice` or `avgFillPrice`; quantity only from
  positive finite `executedQty` or `cumQty`; realized PnL only from finite `realizedProfit` or
  `profit`; fees only from finite `commission`, `fee`, or `tradingFee`.
- Admit event time only from a valid positive `updateTime` or `time` exchange epoch; otherwise use
  null evidence, not local reconciliation time, for fill timing.
- Admit trigger price only from positive finite `stopPrice` or `triggerPrice`, and trigger basis only
  from an explicit `workingType`.
- An observation may record missing fields as null, but identity lifecycle reaches
  `TERMINAL_EVIDENCE_COMPLETE` only when fill price, quantity, realized PnL, fees, and exchange event
  time are all authoritative. Otherwise it advances only to `CLOSURE_OBSERVED` and is excluded from
  cost-adjusted outcome gates.

## Verdict

The current mocked reconciliation fixtures contain only order ID/type/status/PnL, so they are
insufficient for cost-adjusted outcomes. TASK-0146 may add optional, failure-isolated identity
consumption and terminal evidence extraction from the already-fetched order only; no extra query or
runtime wiring is allowed.
