# TASK-0147 — Reconciliation Terminal Observer Integration

**Status:** READY — REPOSITORY-ONLY, RUNTIME DISABLED

## Objective

Connect TASK-0143/0146 identity and terminal evidence to BrokerReconciliationService through
optional dependencies without changing its existing closure selection, operational side effects,
broker calls, or runtime composition.

## Sealed Implementation Boundary

1. Add optional identity-store and terminal-observer dependencies; both default to `None` in every
   current constructor/composition root.
2. Retain the exact existing terminal-order history query, sort, selection, idempotency, cooldown,
   strategy notification, journal update, and alert behavior.
3. Only after the existing selector chooses a known terminal order with explicit symbol and
   `positionSide`, resolve exactly one `OPEN` identity and pass the unmodified order/identity to
   TASK-0146's extractor.
4. On eligible evidence, emit one `EXIT_FILL_OBSERVED` payload with observation UTC time and all
   missing terminal economics explicitly null. Do not infer side, fill time, price, quantity, fees,
   trigger basis, leverage, or PnL.
5. Advance the identity to `TERMINAL_EVIDENCE_COMPLETE` only when the extractor marks it complete;
   otherwise advance it to `CLOSURE_OBSERVED`. Preserve the terminal order ID and monotonic time.
6. Missing/ambiguous/corrupt identity, extraction exclusion, observer failure, or identity-store
   failure must be counted/logged but cannot change operational reconciliation or generate a retry.
7. Do not enable either dependency, instantiate a production file, add a broker query, import
   history, freeze a prospective boundary, or modify trading behavior.

## Required Tests

- Disabled integration preserves exact history, strategy, cooldown, journal, and alert call counts.
- Complete terminal evidence emits once and advances identity to terminal-complete.
- Incomplete evidence emits with nulls and advances only to closure-observed.
- Unknown side/order/symbol, mismatched or ambiguous identity, corrupt store, and observer exception
  remain fail-closed observationally while operational reconciliation is unchanged.
- Repeated closure processing emits no duplicate terminal observation.
- Focused and full suites create no production snapshot or exit ledger.

## Non-Goals

- No runtime wiring/deployment, broker API expansion, fee reconstruction, historical backfill,
  threshold/strategy change, prospective cohort, or profitability conclusion.
