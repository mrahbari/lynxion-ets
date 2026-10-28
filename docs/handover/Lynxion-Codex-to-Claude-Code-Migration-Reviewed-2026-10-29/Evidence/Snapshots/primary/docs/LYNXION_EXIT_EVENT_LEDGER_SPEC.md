# Lynxion Exit-Management Event Ledger Specification

## Purpose

Create forward-only evidence that can distinguish manager decisions, broker submissions, exchange
visibility, restart recovery, and eventual fills. The ledger is observational: it must not change a
threshold, stop price, order decision, retry, leverage, or execution path.

## Storage Contract

- Append-only UTF-8 JSON Lines under `data/research/exit_observability/`.
- One UTC date per file; atomic process-local append with flush and `fsync` after each event.
- Schema version, stable event ID, run ID, evaluation ID, position key, and UTC event timestamp are
  mandatory. Duplicate event IDs are invalid; ordering is preserved but timestamps remain explicit.
- Never record API keys, signatures, request headers, account identifiers, or unrelated balances.
- Collection is prospective only. No reconstruction of historical manager decisions is permitted.

## Common Fields

`schema_version`, `event_id`, `event_type`, `event_time_utc`, `run_id`, `evaluation_id`,
`position_key`, `symbol`, `side`, `quantity`, `entry_price`, `current_price`, `price_source`,
`configured_leverage`, `requested_leverage`, `exchange_leverage`, `roe_pct`, `peak_price`,
`peak_roe_pct`, `manager_state_before`, `manager_state_after`, and `error`.

Unknown authoritative values must be `null`, never guessed or replaced with defaults.

## Event Types

1. `POSITION_OBSERVED`: authoritative position snapshot and leverage readback.
2. `MANAGER_EVALUATED`: inputs, thresholds, elapsed time, and explicit decision including `NO_ACTION`.
3. `STOP_REPLACE_REQUESTED`: prior visible stop, requested stop, trigger basis, close/position side,
   quantity, and attempt number.
4. `STOP_REPLACE_RESPONDED`: broker/exchange acceptance, rejection code, order ID, and latency.
5. `STOP_VISIBILITY_VERIFIED` or `STOP_VISIBILITY_FAILED`: exchange-visible stop details, trigger
   price/basis, verification attempts, and mismatch reason.
6. `STATE_COMMITTED`: local state mutation only after verified broker visibility.
7. `POSITION_HYDRATED`: restart timestamp, recovered stop, leverage, and authoritative source.
8. `EXIT_FILL_OBSERVED`: fill time/price/quantity/fees, exit order type, trigger price/basis, and
   realized PnL when authoritative.

## Invariants

- A successful `STATE_COMMITTED` stop mutation must reference a preceding verified visibility event.
- Every broker request receives a response or explicit timeout/failure event.
- Manager evaluations record `NO_ACTION`; otherwise missing events could be mistaken for inactivity.
- Leverage mismatch or absence remains explicit and cannot be hidden by the current 10x default.
- Restart hydration cannot synthesize a manager decision that occurred before the forward boundary.
- Exit-policy comparisons may begin only after the writer, schema validation, and coverage checks are
  committed and a new prospective boundary is frozen.

## Minimum Data Gate for a Future Profit-Lock Preregistration

- At least 100 completed forward positions and at least 30 per compared side.
- At least 95% of expected manager evaluations represented, with all gaps explicit.
- Every stop mutation linked through request, response, visibility, state commit, and eventual exit.
- Zero schema, duplicate-ID, timestamp-order, impossible-side, or post-hoc-import violations.
- Authoritative leverage available for every included position.

The eventual +10/+12 trigger and +4/+5 lock comparison remains unselected until a separate
preregistration. This specification does not authorize those thresholds or any runtime change.
