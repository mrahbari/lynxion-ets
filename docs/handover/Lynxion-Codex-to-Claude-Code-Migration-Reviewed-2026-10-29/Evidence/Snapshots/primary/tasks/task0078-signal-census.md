# TASK0078 — Point-in-Time Signal Census

**Status:** IMPLEMENTED — runtime verification pending deployment

## Scope

Persist every strategy evaluation outcome (accepted and rejected) with its
point-in-time signal context. The census is read-only and cannot affect order
routing.

## Required Fields

- UTC decision timestamp, symbol, strategy, side, accepted/rejected decision, and reason.
- Fused confidence, regime, direction, dominant bias, price, volatility/ATR where present, and expected SL/TP/R:R.
- Source timeframe and watcher information where present.

## Acceptance Criteria

- Every early rejection path emits one durable census record.
- Every accepted intent emits one durable census record.
- Recording errors fail isolated and never change a decision.
- Unit tests prove accepted/rejected capture and no strategy behavior change.

## Implementation Evidence

- `infrastructure/execution/signal_census_journal.py` provides a thread-safe,
  append-only JSONL journal at `data/signal_census.jsonl`.
- `BaseStrategyAdapter.evaluate_fused_signal()` records disabled, discipline,
  eligibility, and accepted outcomes with fail-isolated writes.
- Unit coverage verifies accepted record contents and disabled rejection capture.
