# TASK-0092 — Controlled Edge Research C-01/C-02/C-03

**Status:** IN PROGRESS — PROTOCOL FROZEN

## Objective

Evaluate preregistered trend-continuation and volatility-breakout candidates with realistic,
path-dependent execution and four chronological OOS folds, without production mutation.

## Acceptance Criteria

- Protocol commit precedes evaluation output.
- Closed-bar, shifted MTF alignment is tested against future-data mutation.
- Entry occurs no earlier than the next bar.
- SL/TP use candle high/low with SL priority when both are touched.
- Costs are included in every decision metric.
- Symbols, sides, and folds remain separable.
- Results and limitations are documented with an explicit KEEP/REJECT verdict.
